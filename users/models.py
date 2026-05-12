from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=16, unique=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username
