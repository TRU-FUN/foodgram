from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Tag

DEFAULT_TAGS = [
    {'name': 'Завтрак', 'slug': 'breakfast'},
    {'name': 'Обед', 'slug': 'lunch'},
    {'name': 'Ужин', 'slug': 'dinner'},
    {'name': 'Десерт', 'slug': 'dessert'},
]


@receiver(post_migrate)
def create_default_tags(sender, **kwargs):
    if sender.name != 'recipes':
        return
    for tag_data in DEFAULT_TAGS:
        Tag.objects.get_or_create(**tag_data)
