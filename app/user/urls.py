"""
URL mappings for the user API.
"""

from django.urls import path
from user import views


app_name = "user"

urlpatterns = [
    path("create/", views.UserCreateView.as_view(), name="create"),
    path("token/", views.AuthTokenCreateView.as_view(), name="token"),
    path("me/", views.UserRetrieveUpdateView.as_view(), name="me"),
]
