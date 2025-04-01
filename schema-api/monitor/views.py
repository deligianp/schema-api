from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsApplicationService, IsActive
from monitor.services import ApplicationServiceMonitoringService


class ApplicationServiceMonitoringAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationService, IsActive]

    def get(self, request):
        application_service = request.user
        application_service_monitoring_service = ApplicationServiceMonitoringService(application_service)
        metrics = application_service_monitoring_service.get_metrics()
        return Response(data=metrics, status=status.HTTP_200_OK)