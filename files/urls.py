from django.urls import path

from files.views import UploadAPIView, DownloadAPIView

urlpatterns = [
    path(r'upload/', UploadAPIView.as_view(), name='uploads'),
    path(r'download/<path:file_path>/', DownloadAPIView.as_view(), name='downloads')
]
