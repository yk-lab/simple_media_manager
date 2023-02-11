import hashlib
import io
import mimetypes
import tempfile
import zipfile
from base64 import b64encode
from pathlib import Path
from typing import IO

import boto3
import cv2
import numpy as np
from Cryptodome.Cipher import AES
from Cryptodome.Cipher._mode_gcm import GcmMode
from Cryptodome.Random import get_random_bytes
from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import TemplateView

from ..models import Album, AlbumFile, File


class UploadView(TemplateView):
    template_name = 'upload.html'

    def generate_thumbnail(self, file: IO[bytes], mimetype: str, suffix: str):
        if mimetype.startswith('video/'):
            with tempfile.NamedTemporaryFile(suffix=suffix) as f:
                file.seek(0)
                f.write(file.read())
                f.seek(0)
                cap = cv2.VideoCapture(f.name)

                if not cap.isOpened():
                    raise Exception

                num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                # digit = len(str(num_frames))
                # frame_num = str(num_frames // 2).zfill(digit)
                frame_num = num_frames // 2
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

                success, img = cap.read()
                i = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                while not success:
                    # TODO: tqdm
                    success, img = cap.read()
                    i += 1
        elif mimetype.startswith('image/'):
            file.seek(0)
            img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), 1)
            # img = cv2.imdecode(file, cv2.IMREAD_UNCHANGED)
        else:
            raise Exception

        print(img.shape)
        thumb = cv2.imencode('.jpg', cv2.GaussianBlur(img, (51, 51), 0))[1]
        return thumb.tostring()

    def file_exec(
            self, album: Album, pos: int, filepath: Path, file: IO[bytes]):
        file.seek(0)
        hash_hexdigest = hashlib.sha3_512(file.read()).hexdigest()

        mimetype, encoding = mimetypes.guess_type(filepath.name)
        assert mimetype is not None

        file_obj, file_created = File.objects.get_or_create(
            hash=hash_hexdigest,
            defaults={
                'name': filepath.name,
                'mime': mimetype,
                'suffix': filepath.suffix,
            })
        if file_created:
            s3 = boto3.client('s3', **settings.S3)
            nonce = get_random_bytes(12)
            cipher = AES.new(
                settings.AES_KEY.encode('utf8'), AES.MODE_GCM, nonce=nonce)
            assert isinstance(cipher, GcmMode)
            file.seek(0)
            ciphertext, tag = cipher.encrypt_and_digest(file.read())
            json_k = ['nonce', 'tag']
            json_v = [
                b64encode(x).decode('utf-8') for x in [cipher.nonce, tag]]
            file_obj.option['encrypt'] = dict(zip(json_k, json_v))
            file_obj.save()

            s3.upload_fileobj(
                io.BytesIO(ciphertext),
                settings.S3_BUCKET_NAME,
                f'upload/{hash_hexdigest}{filepath.suffix}')

            s3.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=f'thumbnails/{hash_hexdigest}.jpg',
                Body=self.generate_thumbnail(file, mimetype, filepath.suffix),
                ContentType='image/jpeg',
            )

        AlbumFile.objects.create(
            album=album, file=file_obj, filename=filepath.name, ordering=pos)

    @transaction.atomic
    def post(self, request):
        file = request.FILES['file']
        mimetype, encoding = mimetypes.guess_type(file.name)

        if mimetype == 'application/zip':
            album = Album.objects.create(name=Path(file.name).stem)
            with tempfile.TemporaryFile() as f:
                for chunk in file.chunks():
                    f.write(chunk)
                with zipfile.ZipFile(f) as zip:
                    for pos, filename in enumerate(zip.namelist(), 1):
                        with zip.open(filename) as _file:
                            print(filename, _file)
                            self.file_exec(album, pos, Path(filename), _file)

        return redirect('/upload')
