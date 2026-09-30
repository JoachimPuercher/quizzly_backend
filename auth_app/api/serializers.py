from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """Create a user from username, email and a confirmed password."""

    # User.email is blank=True on the model, which would make it optional here.
    email = serializers.EmailField(required=True)
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        """Reject duplicate addresses and store them lower cased."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Email already exists')
        return email

    def validate(self, values):
        """Both passwords have to match."""
        if values['password'] != values['confirmed_password']:
            raise serializers.ValidationError('Passwords do not match')
        return values

    def save(self):
        """Create the user with a hashed password and the matching profile."""
        user = User(
            username=self.validated_data['username'],
            email=self.validated_data['email'],
        )
        # set_password hashes the value, a plain assignment would store it
        # in clear text
        user.set_password(self.validated_data['password'])
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user, returned after login."""

    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = fields
