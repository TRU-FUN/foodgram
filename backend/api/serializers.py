import base64
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from rest_framework import serializers

from recipes.models import (
    Ingredient, Tag, Recipe, RecipeIngredient,
    Favorite, ShoppingCart
)
from users.models import Subscription


User = get_user_model()


def _bulk_update_ingredients(recipe, ingredients_data):
    RecipeIngredient.objects.bulk_create([
        RecipeIngredient(
            recipe=recipe,
            ingredient_id=item['id'],
            amount=item['amount']
        )
        for item in ingredients_data
    ])


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания нового пользователя."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор смены пароля пользователя."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate(self, attrs):
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                "Новый пароль не должен совпадать с текущим."
            )
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя с полем статуса подписки."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name',
            'avatar', 'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if not user or not user.is_authenticated:
            return False
        return Subscription.objects.filter(
            follower=user, following=obj
        ).exists()


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Сериализатор списка подписок пользователя."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'avatar',
            'is_subscribed', 'recipes', 'recipes_count',
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if not user or not user.is_authenticated:
            return False
        return Subscription.objects.filter(
            follower=user, following=obj
        ).exists()

    def get_recipes(self, obj):
        from api.serializers import RecipeSerializer

        request = self.context['request']
        limit = None
        param = request.query_params.get('recipes_limit')
        try:
            if param is not None:
                limit = int(param)
        except (ValueError, TypeError):
            limit = None

        qs = obj.recipes.all()
        if limit:
            qs = qs[:limit]
        return RecipeSerializer(qs, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Tag."""
    class Meta:
        model = Tag
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор связи ингредиента с рецептом."""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(
        source='ingredient.name', read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class Base64ImageField(serializers.ImageField):
    """Поле для загрузки base64-изображений."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            header, imgstr = data.split(';base64,')
            ext = header.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор чтения рецепта с вложенными данными."""
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
            'is_in_shopping_cart', 'is_favorited',
        ]

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and obj.in_carts.filter(user=user).exists()
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and obj.favorited_by.filter(user=user).exists()
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор создания и обновления рецепта."""
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=False)
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'text',
            'ingredients', 'tags', 'cooking_time', 'author',
        )

    def validate(self, attrs):
        ingredients = attrs.get('ingredients')
        if ingredients is None:
            raise serializers.ValidationError('Ингредиенты обязательны.')
        ids = [item.get('id') for item in ingredients]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными.'
            )
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        _bulk_update_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.ingredient_links.all().delete()
            _bulk_update_ingredients(instance, ingredients_data)
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор избранного рецепта."""
    class Meta:
        model = Favorite
        fields = ('id', 'recipe')

    def create(self, validated_data):
        user = self.context['request'].user
        return Favorite.objects.create(
            user=user, recipe=validated_data['recipe']
        )


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор корзины покупок."""
    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe')

    def create(self, validated_data):
        user = self.context['request'].user
        return ShoppingCart.objects.create(
            user=user, recipe=validated_data['recipe']
        )
