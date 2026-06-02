from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CLIENT = "client"
    ROLE_COURIER = "courier"
    ROLE_DISPATCHER = "dispatcher"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_CLIENT, "Клиент"),
        (ROLE_COURIER, "Курьер"),
        (ROLE_DISPATCHER, "Диспетчер"),
        (ROLE_ADMIN, "Администратор"),
    ]

    full_name = models.CharField("ФИО", max_length=150)
    phone = models.CharField("Телефон", max_length=16, unique=True)
    email = models.EmailField("Email", unique=True)
    role = models.CharField("Роль", max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)

    @property
    def is_client(self):
        return self.role == self.ROLE_CLIENT

    @property
    def is_courier(self):
        return self.role == self.ROLE_COURIER

    @property
    def is_dispatcher(self):
        return self.role == self.ROLE_DISPATCHER

    @property
    def is_business_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def can_manage_orders(self):
        return self.is_dispatcher or self.is_business_admin

    @property
    def can_access_admin_panel(self):
        return self.is_superuser or self.role in {self.ROLE_DISPATCHER, self.ROLE_ADMIN}

    @property
    def can_view_all_client_pages(self):
        return self.is_superuser or self.role == self.ROLE_ADMIN

    def save(self, *args, **kwargs):
        self.is_staff = self.can_access_admin_panel
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.username
