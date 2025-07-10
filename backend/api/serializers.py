import base64
import uuid

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Ingredient, Tag, Recipe, RecipeIngredient,
    Favorite, ShoppingCart
)
from users.models import Subscription


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Поле для обработки изображений в формате base64 с уникальным именем."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            header, imgstr = data.split(';base64,')
            ext = header.split('/')[-1]
            filename = f'{uuid.uuid4().hex[:10]}.{ext}'
            data = ContentFile(
                base64.b64decode(imgstr),
                name=filename
            )
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки и удаления аватара пользователя."""
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar')
        if avatar and instance.avatar:
            instance.avatar.delete(save=False)
        instance.avatar = avatar
        instance.save()
        return instance

    def delete_avatar(self, instance):
        if instance.avatar:
            instance.avatar.delete(save=True)
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователя."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name', 'password'
        )

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
    new_password = serializers.CharField(
        write_only=True, min_length=8
    )

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "Неверный текущий пароль."
            )
        return value

    def validate(self, attrs):
        if (
            attrs['current_password']
            == attrs['new_password']
        ):
            raise serializers.ValidationError(
                "Новый пароль не должен совпадать"
                " с текущим."
            )
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя с флагом подписки."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name',
            'last_name', 'avatar', 'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return bool(
            user
            and user.is_authenticated
            and Subscription.objects.filter(
                follower=user,
                following=obj
            ).exists()
        )


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Сериализатор списка подписок пользователя."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name',
            'last_name', 'avatar', 'is_subscribed',
            'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return bool(
            user
            and user.is_authenticated
            and Subscription.objects.filter(
                follower=user,
                following=obj
            ).exists()
        )

    def get_recipes(self, obj):
        from api.serializers import RecipeSerializer
        params = self.context['request'].query_params
        try:
            limit = int(params.get('recipes_limit', 0))
        except (ValueError, TypeError):
            limit = None
        qs = obj.recipes.all()
        if limit:
            qs = qs[:limit]
        return RecipeSerializer(
            qs, many=True,
            context=self.context
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиента."""
    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тега."""
    class Meta:
        model = Tag
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор связи ингредиента и рецепта."""
    id = serializers.IntegerField(
        source='ingredient.id'
    )
    name = serializers.CharField(
        source='ingredient.name', read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = (
            'id', 'name', 'measurement_unit', 'amount'
        )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Количество должно быть больше нуля.'
            )
        return value


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор рецепта (чтение)."""
    author = UserSerializer(read_only=True)
    tags = TagSerializer(
        many=True, read_only=True
    )
    ingredients = RecipeIngredientSerializer(
        source='ingredient_links', many=True, read_only=True
    )
    is_in_shopping_cart = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'name', 'image', 'text',
            'cooking_time', 'author', 'tags',
            'ingredients', 'is_in_shopping_cart',
            'is_favorited'
        ]

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return bool(
            user.is_authenticated
            and obj.in_carts.filter(user=user).exists()
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return bool(
            user.is_authenticated
            and obj.favorited_by.filter(user=user).exists()
        )


class RecipeCreateUpdateSerializer(
    serializers.ModelSerializer
):
    """Сериализатор для создания и редактирования рецепта."""
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=False)
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'text',
            'ingredients', 'tags', 'cooking_time',
            'author'
        )

    def validate(self, attrs):
        ing = attrs.get('ingredients')
        if not ing:
            raise serializers.ValidationError(
                'Ингредиенты обязательны.'
            )
        ids = [i.get('id') for i in ing]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными.'
            )
        tags = attrs.get('tags')
        if not tags:
            raise serializers.ValidationError(
                'Теги обязательны.'
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                'Теги должны быть уникальными.'
            )
        return attrs

    def create(self, validated_data):
        ing_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            ) for item in ing_data
        ])
        return recipe

    def update(self, instance, validated_data):
        ing_data = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance = super().update(
            instance, validated_data
        )
        if tags is not None:
            instance.tags.set(tags)
        if ing_data is not None:
            instance.ingredient_links.all().delete()
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=item['id'],
                    amount=item['amount']
                ) for item in ing_data
            ])
        return instance

    def to_representation(self, instance):
        from api.serializers import RecipeSerializer
        return RecipeSerializer(
            instance, context=self.context
        ).data


class UserRecipeRelationSerializer(
    serializers.ModelSerializer
):
    """Базовый сериализатор для связей user-recipe."""
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all()
    )

    class Meta:
        abstract = True
        fields = ('id', 'user', 'recipe')


class FavoriteSerializer(
    UserRecipeRelationSerializer
):
    """Сериализатор для избранного рецепта."""
    class Meta(
        UserRecipeRelationSerializer.Meta
    ):
        model = Favorite
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=['user', 'recipe']
            )
        ]

    def to_representation(self, instance):
        from api.serializers import RecipeSerializer
        return RecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class ShoppingCartSerializer(
    UserRecipeRelationSerializer
):
    """Сериализатор элемента корзины покупок."""
    class Meta(
        UserRecipeRelationSerializer.Meta
    ):
        model = ShoppingCart
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=['user', 'recipe']
            )
        ]

    def to_representation(self, instance):
        from api.serializers import RecipeSerializer
        return RecipeSerializer(
            instance.recipe,
            context=self.context
        ).data
