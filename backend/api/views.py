from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    ShoppingCart, Tag, User
)
from users.models import Subscription
from api.serializers import (
    FavoriteSerializer, IngredientSerializer, PasswordChangeSerializer,
    RecipeCreateUpdateSerializer, RecipeSerializer, ShoppingCartSerializer,
    SubscriptionListSerializer, TagSerializer, UserCreateSerializer,
    UserSerializer, AvatarSerializer
)
from .filters import IngredientFilter, RecipeFilter
from .mixins import RelationHandlerMixin
from .utils import generate_shopping_cart_pdf


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in ('GET',):
            return (AllowAny(),)
        return (IsAuthenticated(),)


class RecipeViewSet(RelationHandlerMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-id')
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.request.method in ('GET',):
            return (AllowAny(),)
        return (IsAuthenticated(),)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=('post', 'delete'))
    def favorite(self, request, pk=None):
        return self.handle_relation(
            request, Favorite, 'избранное', FavoriteSerializer
        )

    @action(detail=True, methods=('post', 'delete'))
    def shopping_cart(self, request, pk=None):
        return self.handle_relation(
            request, ShoppingCart, 'список покупок', ShoppingCartSerializer
        )

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        full_link = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return Response({'short-link': full_link})

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        recipes = Recipe.objects.filter(
            in_carts__user=user
        ).prefetch_related('ingredient_links__ingredient')

        if not recipes.exists():
            return HttpResponse(
                'Ваш список покупок пуст.', content_type='text/plain'
            )

        ingredients_by_recipe = {
            recipe.name: [
                f"{link.ingredient.name} "
                f"({link.ingredient.measurement_unit}) - {link.amount}"
                for link in recipe.ingredient_links.all()
            ] for recipe in recipes
        }

        aggregated = (
            RecipeIngredient.objects.filter(recipe__in_carts__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        combined_ingredients = {
            item['ingredient__name']: {
                'unit': item['ingredient__measurement_unit'],
                'amount': item['total_amount']
            } for item in aggregated
        }

        pdf = generate_shopping_cart_pdf(
            ingredients_by_recipe, combined_ingredients
        )

        return HttpResponse(
            pdf,
            content_type='application/pdf',
            headers={
                'Content-Disposition': (
                    'attachment; filename="shopping_cart.pdf"'
                )
            }
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return (AllowAny(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(
        detail=False,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def set_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(
                serializer.validated_data['new_password']
            )
            request.user.save()
            return Response({'status': 'Пароль успешно изменен'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        data = {
            'follower': request.user.id,
            'following': author.id
        }
        serializer = SubscriptionListSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        if request.method == 'POST':
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        Subscription.objects.filter(
            follower=request.user, following=author
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(
            subscribers__follower=request.user
        )
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionListSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=('put', 'delete'),
        permission_classes=(IsAuthenticated,),
        parser_classes=(MultiPartParser, FormParser, JSONParser),
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(
                instance=user,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                UserSerializer(user, context={'request': request}).data
            )

        if request.method == 'DELETE':
            if not user.avatar:
                return Response(
                    {'error': 'Аватар отсутствует'}, status=400
                )
            user.avatar.delete(save=True)
            return Response(
                {'message': 'Аватар удалён'},
                status=status.HTTP_204_NO_CONTENT
            )
