from django.urls import path

from api_auth.views import ContextAPIView, ContextTokenAPIView, ContextDetailsAPIView, ContextTokenDetailsAPIView

urlpatterns = [
    path(r'contexts', ContextAPIView.as_view(), name='contexts'),
    path(r'contexts/<context_name>', ContextDetailsAPIView.as_view(), name='context_name-details'),
    path(r'contexts/<context_name>/tokens', ContextTokenAPIView.as_view(), name='context_name-tokens'),
    path(r'contexts/<context_name>/tokens/<token_uuid>', ContextTokenDetailsAPIView.as_view(),
         name='context_name-token-details')
]
