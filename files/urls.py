from django.urls import path

from files.views import UploadAPIView

urlpatterns = [
    path(r'upload/', UploadAPIView.as_view(), name='uploads'),
]
