import random
from django.core.management.base import BaseCommand
from django_seed import Seed
from rooms import models as room_models
from users import models as user_models
from reviews import models as review_models

NAME = "reviews"


class Command(BaseCommand):

    help = f"This command creates many {NAME}"

    def add_arguments(self, parser):
        parser.add_argument(
            "--number", default=1, type=int, help="How many users you want to create?"
        )

    def handle(self, *args, **options):
        number = options.get("number")
        seeder = Seed.seeder()
        users = user_models.User.objects.all()
        rooms = room_models.Room.objects.all()
        seeder.add_entity(
            review_models.Review,
            number,
            {
                "accuracy": lambda x: random.randint(0, 6),
                "communication": lambda x: random.randint(0, 6),
                "cleanliness": lambda x: random.randint(0, 6),
                "location": lambda x: random.randint(0, 6),
                "check_in": lambda x: random.randint(0, 6),
                "value": lambda x: random.randint(0, 6),
                "room": lambda x: random.choice(rooms),
                "user": lambda x: random.choice(users),
            },
        )
        seeder.execute()
        self.stdout.write(self.style.SUCCESS(f"{number} {NAME} created!"))

