from django.views.generic import DetailView
from main.models.album import Album


class AlbumDetailView(DetailView):
    model = Album
