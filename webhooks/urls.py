from django.urls import path
from .views import EmailWebookView, TestView, AuthorizeView, OAuth2CallbackView, RevokeView, ClearCredentialsView


urlpatterns = [
    path('webhook/email/', EmailWebookView.as_view(), name='email_webhook'),
    path('test/', TestView.as_view(), name='test_api_request'),
    path('authorize/', AuthorizeView.as_view(), name='authorize'),
    path('oauth2callback/', OAuth2CallbackView.as_view(), name='oauth2callback'),
    path('revoke/', RevokeView.as_view(), name='revoke'),
    path('clear/', ClearCredentialsView.as_view(), name='clear_credentials'),
]
