from django.conf import settings
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from monitor.views import ApplicationServiceMonitoringAPIView

urlpatterns = [
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),
    path("application-service/metrics", ApplicationServiceMonitoringAPIView.as_view(),
         name='application-service-metrics'),
]
