from django.urls import path

from workflows import views

urlpatterns = [
    path('', views.WorkflowsAPIView.as_view(), name='workflows'),
    path('/definition', views.WorkflowDefinitionAPIView.as_view(), name='workflow-definition'),
    path('/<uuid:uuid>', views.WorkflowDetailsAPIView.as_view(), name='workflow-details'),
    path('/<uuid:uuid>/cancel', views.WorkflowCancelAPIView.as_view(), name='workflow-cancel')
]