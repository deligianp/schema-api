from django.urls import path

from api_auth.views import ContextsAPIView, ContextDetailsAPIView, UsersAPIView, UserDetailsAPIView, \
    ContextParticipantsAPIView, ContextParticipantDetailsAPIView, ContextParticipationTokensAPIView, \
    ContextParticipationTokenDetailsAPIView, ContextQuotasAPIView, ContextParticipantQuotasAPIView

urlpatterns = [
    path(r'users', UsersAPIView.as_view(), name='users'),
    path(r'users/<username>', UserDetailsAPIView.as_view(), name='user-details'),
    path(r'contexts', ContextsAPIView.as_view(), name='contexts'),
    path(r'contexts/<name>', ContextDetailsAPIView.as_view(), name='context-details'),
    path(r'contexts/<name>/quotas', ContextQuotasAPIView.as_view(), name='context-quotas'),
    path(r'contexts/<name>/users', ContextParticipantsAPIView.as_view(), name='context-participants'),
    path(r'contexts/<name>/users/<username>', ContextParticipantDetailsAPIView.as_view(),
         name='context-participant-details'),
    path(r'contexts/<name>/users/<username>/quotas', ContextParticipantQuotasAPIView.as_view(),
         name='context-participant-quotas'),
    path(r'contexts/<name>/users/<username>/tokens', ContextParticipationTokensAPIView.as_view(),
         name='context-participation-tokens'),
    path(r'contexts/<name>/users/<username>/tokens/<uuid>', ContextParticipationTokenDetailsAPIView.as_view(),
         name='context-participation-token-details')
]
