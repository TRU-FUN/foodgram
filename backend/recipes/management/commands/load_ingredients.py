from csv import reader
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из CSV файла'

    def handle(self, *args, **options):
        if Ingredient.objects.exists():
            self.stdout.write(self.style.WARNING('Ингредиенты уже загружены'))
            return

        with open('/app/data/ingredients.csv', encoding='utf-8') as f:
            for row in reader(f):
                name, measurement_unit = row
                Ingredient.objects.get_or_create(
                    name=name,
                    measurement_unit=measurement_unit
                )
        self.stdout.write(self.style.SUCCESS('Ингредиенты успешно загружены'))
