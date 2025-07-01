import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from .models import (
    Ingredient, Tag, Recipe, Favorite, ShoppingCart,
    RecipeIngredient
)
from users.serializers import UserSerializer


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='ingredient_links', many=True, read_only=True
    )
    is_in_shopping_cart = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'name', 'image', 'text', 'cooking_time',
            'author', 'tags', 'ingredients',
            'is_in_shopping_cart', 'is_favorited'
        ]

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        )


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                format, imgstr = data.split(';base64,')
                ext = format.split('/')[-1]
                return ContentFile(
                    base64.b64decode(imgstr), name=f'temp.{ext}')
            except Exception:
                raise serializers.ValidationError(
                    'Ошибка декодирования изображения'
                )
        return super().to_internal_value(data)


class RecipeIngredientCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'amount': getattr(instance, 'amount', 0)
        }


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = Base64ImageField(required=False)
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'text', 'ingredients', 'tags',
            'cooking_time', 'author'
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Список ингредиентов не может быть пустым.'
            )
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными.'
            )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'Список тегов не может быть пустым.'
            )
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                'Теги должны быть уникальными.'
            )
        return value

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            ) for item in ingredients
        ])
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)

        if tags is not None:
            instance.tags.set(tags)

        if ingredients is not None:
            instance.ingredient_links.all().delete()
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=item['id'],
                    amount=item['amount']
                ) for item in ingredients
            ])
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'recipe': {'read_only': True},
        }

    def validate(self, data):
        user = self.context['request'].user
        recipe = self.context['view'].kwargs.get('recipe_id')
        if Favorite.objects.filter(user=user, recipe_id=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в избранном.')
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = '__all__'
