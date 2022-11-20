from rest_framework import routers

from api.views import TaskViewSet

router = routers.SimpleRouter()
router.register(r'tasks', TaskViewSet, basename='tasks')

urlpatterns = router.urls
