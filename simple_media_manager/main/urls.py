from django.urls import path

from .views import (AlbumDetailView, FileThumbnail, FileView, TopView,
                    UploadView)

urlpatterns = [
    path('', TopView.as_view(), name='top'),
    path('album/<str:pk>/', AlbumDetailView.as_view(), name='album_detail'),
    path('file/<str:pk>/', FileView.as_view(), name='file'),
    path('file/<str:hash>/thumbnail',
         FileThumbnail.as_view(), name='file_thumbnail'),
    path('upload/', UploadView.as_view()),
]
