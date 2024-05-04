"""
Vies for the user API.
"""
from rest_framework.generics import CreateAPIView

from user.serializers import UserSerializer


class UserCreateView(CreateAPIView):
    """Create a new user in the system."""
    serializer_class = UserSerializer
    lookup_field = 'pk'
