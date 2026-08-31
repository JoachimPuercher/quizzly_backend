from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """Creates a User together with its UserProfile from a single registration payload."""

    confirmed_password = serializers.CharField(max_length=100, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def save(self):
        """Create the user with a hashed password and the matching profile."""
        user = User(
            username=self.validated_data['username'],
            email=self.validated_data['email'],
        )
        # set_password hashes the value, a plain assignment would store it in clear text
        user.set_password(self.validated_data['password'])
        user.save()

        return user

    def validate_email(self, value):
        """Reject duplicate addresses and store them lower cased."""
        new_mail = value.lower()
        if User.objects.filter(email=new_mail).exists():
            raise serializers.ValidationError('Email already exists')
        else:
            return new_mail

    def validate(self, values):
        """Both password fields have to match."""
        if values['password'] != values['confirmed_password']:
            raise serializers.ValidationError('Password do not match')
        else:
            return values


class LoginSerializer(serializers.Serializer):
    """Checks the credentials and hands the matching user to the view."""

    username = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True)

    def validate(self, values):
        new_username = values['username']
        user = User.objects.filter(username=new_username).first()

        if user:
            pw_valid = user.check_password(values['password'])

            if pw_valid:
                # the view needs the instance, so it travels on in validated_data
                values['user'] = user
                return values
            else:
                # same message for both cases, otherwise it would leak existing usernames
                raise serializers.ValidationError('Invalid Credentials')
        else:
            raise serializers.ValidationError('Invalid Credentials')