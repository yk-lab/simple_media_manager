from django.db import models
from django.urls import reverse
from model_utils.models import UUIDModel

from .file import File


class Album(UUIDModel):
    name = models.CharField(verbose_name='アルバム名', max_length=256)
    files = models.ManyToManyField(
        File, through='AlbumFile', verbose_name='ファイル')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('album_detail', kwargs={'pk': self.id})
