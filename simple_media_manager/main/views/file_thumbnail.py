import boto3
from django.conf import settings
from django.http import StreamingHttpResponse
from django.views import View


class FileThumbnail(View):
    def get(self, request, hash):
        s3 = boto3.resource('s3', **settings.S3)
        bucket = s3.Bucket(settings.S3_BUCKET_NAME)
        obj = bucket.Object(f'thumbnails/{hash}.jpg')
        response = obj.get()
        return StreamingHttpResponse(
            response['Body'],
            content_type=response['ContentType'],
        )
