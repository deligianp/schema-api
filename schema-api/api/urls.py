from django.urls import path
from rest_framework import routers

from api.views import TaskViewSet, UserQuotasAPIView

router = routers.SimpleRouter()
router.register(r'tasks', TaskViewSet, basename='tasks')

urlpatterns = router.urls
urlpatterns.extend([
    path(r'quotas', UserQuotasAPIView.as_view(), name='user_quotas'),
])