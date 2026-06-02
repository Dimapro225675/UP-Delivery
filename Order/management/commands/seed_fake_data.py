import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from faker import Faker

from Order.models import AuditLog, DeliveryType, Issue, Order, StatusHistory


class Command(BaseCommand):
    help = "Generate fake users, delivery types, orders, statuses, and issues for local development."

    def add_arguments(self, parser):
        parser.add_argument("--clients", type=int, default=12, help="Number of client users to create.")
        parser.add_argument("--couriers", type=int, default=6, help="Number of courier users to create.")
        parser.add_argument("--dispatchers", type=int, default=3, help="Number of dispatcher users to create.")
        parser.add_argument("--admins", type=int, default=1, help="Number of admin users to create.")
        parser.add_argument("--orders", type=int, default=30, help="Number of orders to create.")
        parser.add_argument(
            "--password",
            default="Test12345!",
            help="Password for every generated user.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously generated fake users and related seed data before creating new data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker("ru_RU")
        Faker.seed(42)
        random.seed(42)

        user_model = get_user_model()
        password = options["password"]

        if options["clear"]:
            self._clear_seed_data(user_model)

        delivery_types = self._ensure_delivery_types()
        clients = self._create_users(user_model, user_model.ROLE_CLIENT, options["clients"], password, fake)
        couriers = self._create_users(user_model, user_model.ROLE_COURIER, options["couriers"], password, fake)
        dispatchers = self._create_users(user_model, user_model.ROLE_DISPATCHER, options["dispatchers"], password, fake)
        admins = self._create_users(user_model, user_model.ROLE_ADMIN, options["admins"], password, fake)

        orders_created = self._create_orders(
            fake=fake,
            clients=clients,
            couriers=couriers,
            dispatchers=dispatchers,
            admins=admins,
            delivery_types=delivery_types,
            orders_count=options["orders"],
        )

        self.stdout.write(self.style.SUCCESS("Fake data generated successfully."))
        self.stdout.write(f"Clients: {len(clients)}")
        self.stdout.write(f"Couriers: {len(couriers)}")
        self.stdout.write(f"Dispatchers: {len(dispatchers)}")
        self.stdout.write(f"Admins: {len(admins)}")
        self.stdout.write(f"Orders: {orders_created}")
        self.stdout.write(f"Password for generated users: {password}")

    def _clear_seed_data(self, user_model):
        seed_users = user_model.objects.filter(username__startswith="seed_")
        if seed_users.exists():
            self.stdout.write("Deleting previously generated seed users and related data...")
            seed_users.delete()
        DeliveryType.objects.filter(name__startswith="Seed ").delete()

    def _ensure_delivery_types(self):
        defaults = [
            {"name": "Seed Экспресс", "description": "Быстрая доставка для тестовых данных.", "max_distance": 150, "base_price": Decimal("2000.00")},
            {"name": "Seed Стандарт", "description": "Базовый тип доставки для тестовых данных.", "max_distance": 900, "base_price": Decimal("1200.00")},
            {"name": "Seed Дальний", "description": "Междугородняя доставка для тестовых данных.", "max_distance": 2500, "base_price": Decimal("4500.00")},
        ]

        delivery_types = []
        for item in defaults:
            delivery_type, _ = DeliveryType.objects.get_or_create(name=item["name"], defaults=item)
            delivery_types.append(delivery_type)
        return delivery_types

    def _create_users(self, user_model, role, count, password, fake):
        role_prefix = {
            user_model.ROLE_CLIENT: "client",
            user_model.ROLE_COURIER: "courier",
            user_model.ROLE_DISPATCHER: "dispatcher",
            user_model.ROLE_ADMIN: "admin",
        }[role]

        users = []
        for index in range(count):
            username = f"seed_{role_prefix}_{index + 1}"
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "full_name": fake.name(),
                    "email": f"{username}@example.com",
                    "phone": self._build_phone(index, role_prefix),
                    "role": role,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            users.append(user)
        return users

    def _create_orders(self, *, fake, clients, couriers, dispatchers, admins, delivery_types, orders_count):
        city_choices = [city for city, _ in Order.CITY_CHOICES]
        creators = clients + dispatchers + couriers + admins
        statuses = [
            Order.STATUS_WAITING,
            Order.STATUS_WAITING_COURIER,
            Order.STATUS_DELIVERING,
            Order.STATUS_DELIVERED_PICKUP_POINT,
            Order.STATUS_DELIVERED_ADDRESS,
            Order.STATUS_CONFIRMED,
            Order.STATUS_RETURNED,
            Order.STATUS_CANCELLED,
        ]
        created_orders = 0

        for index in range(orders_count):
            client = random.choice(creators)
            pickup_city = random.choice(city_choices)
            delivery_city = random.choice([city for city in city_choices if city != pickup_city] or city_choices)
            delivery_to_pickup_point = random.choice([True, False])
            delivery_type = random.choice(delivery_types)
            courier = random.choice(couriers) if couriers and random.choice([True, False]) else None
            status = random.choice(statuses)

            if status in {Order.STATUS_WAITING_COURIER, Order.STATUS_DELIVERING, Order.STATUS_DELIVERED_PICKUP_POINT, Order.STATUS_DELIVERED_ADDRESS} and not courier:
                courier = random.choice(couriers) if couriers else None
            if status == Order.STATUS_WAITING and courier:
                status = Order.STATUS_WAITING_COURIER
            if status in {Order.STATUS_CONFIRMED, Order.STATUS_RETURNED, Order.STATUS_CANCELLED} and not courier and couriers:
                courier = random.choice(couriers)

            order = Order.objects.create(
                client=client,
                courier=courier,
                pickup_city=pickup_city,
                pickup_street=fake.street_name(),
                pickup_house=str(random.randint(1, 120)),
                delivery_to_pickup_point=delivery_to_pickup_point,
                delivery_city=delivery_city,
                delivery_street="" if delivery_to_pickup_point else fake.street_name(),
                delivery_house="" if delivery_to_pickup_point else str(random.randint(1, 120)),
                description=fake.sentence(nb_words=8),
                delivery_type=delivery_type,
                cargo_type=random.choice([choice for choice, _ in Order.CARGO_TYPES]),
                weight_kg=Decimal(str(round(random.uniform(0.5, 40.0), 2))),
                length_cm=Decimal(str(round(random.uniform(10.0, 100.0), 2))),
                width_cm=Decimal(str(round(random.uniform(10.0, 100.0), 2))),
                height_cm=Decimal(str(round(random.uniform(5.0, 80.0), 2))),
                status=status,
            )

            StatusHistory.objects.create(
                order=order,
                status=order.status,
                courier=courier or client,
                comment="Seed data created",
            )
            AuditLog.objects.create(
                user=client,
                order=order,
                action="seed_created",
                details="Order created by seed command",
            )

            if random.choice([True, False, False]):
                issue = Issue.objects.create(
                    order=order,
                    issue_type=random.choice([choice for choice, _ in Issue.ISSUE_TYPES]),
                    description=fake.sentence(nb_words=10),
                    created_by=courier or random.choice(dispatchers or admins or [client]),
                    resolved=random.choice([True, False]),
                )
                AuditLog.objects.create(
                    user=issue.created_by,
                    order=order,
                    action="seed_issue_created",
                    details=issue.description,
                )

            created_orders += 1

        return created_orders

    @staticmethod
    def _build_phone(index, prefix):
        prefix_digits = {
            "client": "901",
            "courier": "902",
            "dispatcher": "903",
            "admin": "904",
        }[prefix]
        suffix = f"{index + 1:07d}"
        return f"+7{prefix_digits}{suffix}"
