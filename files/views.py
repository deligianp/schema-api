from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsActive, IsUser
from files.serializers import UploadInputSerializer
from files.services import UploadService


# Create your views here.
class UploadAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive] if settings.USE_AUTH else []

    def post(self, request):
        upload_input_serializer = UploadInputSerializer(data=request.data)
        upload_input_serializer.is_valid(raise_exception=True)

        upload_service = UploadService(request.user)
        upload_info = upload_service.create_upload_request(**upload_input_serializer.validated_data)

        return Response(status=status.HTTP_201_CREATED, data={
            **upload_input_serializer.validated_data,
            'upload_info': upload_info
        })


class DownloadAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsActive] if settings.USE_AUTH else []

    def get(self, request, file_path: str):
        download_service = UploadService(request.user)
        download_info = download_service.create_download_request(file_path)

        return Response(status=status.HTTP_200_OK, data={
            'file_path': file_path,
            **download_info
        })
