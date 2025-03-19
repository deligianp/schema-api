from django.urls import path

from workflows import views

urlpatterns = [
    path('', views.WorkflowsAPIView.as_view(), name='workflows'),
    path('/specification', views.WorkflowSpecificationAPIView.as_view(), name='workflow-specification'),
    path('<uuid:uuid>', views.WorkflowDetailsAPIView.as_view(), name='workflow-details'),
    path('<uuid:uuid>/cancel', views.WorkflowDetailsAPIView.as_view(), name='workflow-cancel')
]