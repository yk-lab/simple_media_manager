from django.db import models
from model_utils.models import UUIDModel

from .album import Album, File


class AlbumFile(UUIDModel):
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, verbose_name='アルバム')
    file = models.ForeignKey(
        File, on_delete=models.CASCADE, verbose_name='ファイル')
    filename = models.CharField(verbose_name='アルバム内ファイル名', max_length=256)
    ordering = models.IntegerField(verbose_name='表示順', default=128)
