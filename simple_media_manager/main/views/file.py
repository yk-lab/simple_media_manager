import io
import os
import re
from base64 import b64decode
from wsgiref.util import FileWrapper

import boto3
from Cryptodome.Cipher import AES
from Cryptodome.Cipher._mode_gcm import GcmMode
from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views import View

from ..models import File

range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)


class RangeFileWrapper(object):
    def __init__(self, filelike, blksize=8192, offset=0, length=None):
        self.filelike = filelike
        self.filelike.seek(offset, os.SEEK_SET)
        self.remaining = length
        self.blksize = blksize

    def close(self):
        if hasattr(self.filelike, 'close'):
            self.filelike.close()

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining is None:
            # If remaining is None, we're reading the entire file.
            data = self.filelike.read(self.blksize)
            if data:
                return data
            raise StopIteration()
        else:
            if self.remaining <= 0:
                raise StopIteration()
            data = self.filelike.read(min(self.remaining, self.blksize))
            if not data:
                raise StopIteration()
            self.remaining -= len(data)
            return data


class FileView(View):
    def get(self, request, pk):
        file = get_object_or_404(File, pk=pk)
        encrypt_opt = file.option['encrypt']
        json_k = ['nonce', 'tag']
        jv = {k: b64decode(encrypt_opt[k]) for k in json_k}
        cipher = AES.new(settings.AES_KEY.encode('utf8'),
                         AES.MODE_GCM, nonce=jv['nonce'])
        assert isinstance(cipher, GcmMode)
        s3 = boto3.resource('s3', **settings.S3)
        bucket = s3.Bucket(settings.S3_BUCKET_NAME)
        obj = bucket.Object(f'upload/{file.hash}{file.suffix}')
        response = obj.get()

        _file = cipher.decrypt_and_verify(response['Body'].read(), jv['tag'])

        range_header = request.META.get('HTTP_RANGE', '').strip()
        range_match = range_re.match(range_header)
        size = len(_file)

        if range_match:
            first_byte, last_byte = range_match.groups()
            first_byte = int(first_byte) if first_byte else 0
            last_byte = int(last_byte) if last_byte else size - 1
            if last_byte >= size:
                last_byte = size - 1
            length = last_byte - first_byte + 1
            resp = StreamingHttpResponse(
                RangeFileWrapper(
                    io.BytesIO(_file), offset=first_byte, length=length),
                status=206, content_type=file.mime)
            resp['Content-Length'] = str(length)
            resp['Content-Range'] = 'bytes %s-%s/%s' % (
                first_byte, last_byte, size)
        else:
            resp = StreamingHttpResponse(
                FileWrapper(io.BytesIO(_file)), content_type=file.mime)
            resp['Content-Length'] = str(size)
        resp['Accept-Ranges'] = 'bytes'
        return resp
