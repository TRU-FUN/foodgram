from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

from api.constants import (
    INGREDIENT_NAME_MAX_LENGTH,
    MEASUREMENT_UNIT_MAX_LENGTH,
    TAG_NAME_MAX_LENGTH,
    RECIPE_NAME_MAX_LENGTH
)

User = get_user_model()


class TimeStampedModel(models.Model):
    """
    Абстрактная модель, добавляющая поля создания и обновления.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Ingredient(TimeStampedModel):
    """
    Ингредиент для рецептов.
    """
    name = models.CharField(
        'Название', max_length=INGREDIENT_NAME_MAX_LENGTH, unique=True,
        help_text='Уникальное имя ингредиента'
    )
    measurement_unit = models.CharField(
        'Ед. измерения', max_length=MEASUREMENT_UNIT_MAX_LENGTH,
        help_text='Например, г, шт., мл'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Tag(TimeStampedModel):
    """
    Тег для рецептов.
    """
    name = models.CharField(
        'Название', max_length=TAG_NAME_MAX_LENGTH, unique=True,
        help_text='Уникальное имя тега'
    )
    slug = models.SlugField(
        'Slug', unique=True,
        help_text='URL-дружественный идентификатор'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(TimeStampedModel):
    """
    Рецепт блюда.
    """
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='recipes', verbose_name='Автор'
    )
    name = models.CharField(
        'Название', max_length=RECIPE_NAME_MAX_LENGTH,
        help_text='Уникальное имя рецепта'
    )
    image = models.ImageField(
        'Изображение', upload_to='recipes/', blank=True, null=True
    )
    text = models.TextField(
        'Описание', help_text='Текст рецепта с инструкциями'
    )
    cooking_time = models.PositiveIntegerField(
        'Время (мин)', validators=[MinValueValidator(1)]
    )
    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name='Теги'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    shopping_cart_entries = models.ManyToManyField(
        User,
        through='ShoppingCart',
        related_name='shopping_cart',
        verbose_name='В списках покупок'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('recipe-detail', kwargs={'pk': self.pk})


class RecipeIngredient(models.Model):
    """
    Количество ингредиента в рецепте.
    """
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='ingredient_links'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE
    )
    amount = models.PositiveIntegerField(
        'Количество', validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name}: {self.amount}'


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name='Рецепт'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.user.email} -> {self.recipe.name}'


class Favorite(UserRecipeRelation):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='favorites', verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE,
        related_name='favorited_by', verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_favorite'
            )
        ]

    def __str__(self):
        return f'{self.user.email} -> {self.recipe.name}'


class ShoppingCart(UserRecipeRelation):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='cart_items', verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE,
        related_name='in_carts', verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Покупка'
        verbose_name_plural = 'Список покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_cart_item'
            )
        ]

    def __str__(self):
        return f'{self.user.email} x {self.recipe.name}'
