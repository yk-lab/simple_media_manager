from django.db import models
from django.urls import reverse
from model_utils.models import UUIDModel


class File(UUIDModel):
    name = models.CharField(verbose_name='ファイル名', max_length=256)
    hash = models.CharField(verbose_name='ファイルハッシュ', max_length=256)
    mime = models.CharField(verbose_name='ファイル種別', max_length=256)
    suffix = models.CharField(verbose_name='ファイル拡張子', max_length=256)
    option = models.JSONField(verbose_name='オプション', default=dict)

    def __str__(self):
        return self.name

    def get_thumbnail_url(self):
        return reverse('file_thumbnail', kwargs={'hash': self.hash})

    def get_absolute_url(self):
        return reverse('file', kwargs={'pk': self.id})
