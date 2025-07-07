from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    ShoppingCart, Tag, User
)
from users.models import Subscription
from api.serializers import (
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeSerializer,
    TagSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
    PasswordChangeSerializer,
    SubscriptionListSerializer,
    UserCreateSerializer,
    UserSerializer
)
from .filters import IngredientFilter, RecipeFilter
from .mixins import RelationHandlerMixin
from .paginations import SubscriptionPagination
from .utils import generate_shopping_cart_pdf


class IngredientViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с ингредиентами.

    Позволяет:
    - Получать список ингредиентов
    - Фильтровать по имени (поиск начинается с начала строки)
    """
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с тегами.

    Позволяет:
    - Получать список тегов
    - Только авторизованные пользователи могут изменять
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (AllowAny(),)
        return (IsAuthenticated(),)


class RecipeViewSet(RelationHandlerMixin, viewsets.ModelViewSet):
    """
    ViewSet для рецептов:
    - Список, просмотр, создание, изменение, удаление
    - Добавление в избранное и список покупок
    - Генерация ссылки
    - Поддержка фильтрации
    """
    queryset = Recipe.objects.all().order_by('-id')
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'get_link'):
            return (AllowAny(),)
        return (IsAuthenticated(),)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Вы не можете удалить этот рецепт.'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(
            {'success': 'Рецепт успешно удален.'},
            status=status.HTTP_204_NO_CONTENT
        )

    def perform_destroy(self, instance):
        if instance.image:
            instance.image.delete()
        instance.delete()

    @action(detail=True, methods=('post', 'delete'))
    def favorite(self, request, pk=None):
        return self.handle_relation(
            request, Favorite, 'избранное', FavoriteSerializer
        )

    @action(detail=True, methods=('post', 'delete'))
    def shopping_cart(self, request, pk=None):
        return self.handle_relation(
            request,
            ShoppingCart,
            'список покупок',
            ShoppingCartSerializer
        )

    @action(
        detail=True, methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link', url_name='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        full_link = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return Response({'short-link': full_link})


class DownloadShoppingCart(APIView):
    """Скачивание PDF списка покупок."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user

        recipes = Recipe.objects.filter(in_carts__user=user).prefetch_related(
            'ingredient_links__ingredient'
        )

        if not recipes.exists():
            return HttpResponse(
                'Ваш список покупок пуст.', content_type='text/plain'
            )

        ingredients_by_recipe = {}
        for recipe in recipes:
            items = []
            for link in recipe.ingredient_links.all():
                ingredient = link.ingredient
                items.append(
                    f"{ingredient.name} ({ingredient.measurement_unit}) - "
                    f"{link.amount}"
                )
            ingredients_by_recipe[recipe.name] = items

        aggregated = (
            RecipeIngredient.objects
            .filter(recipe__in_carts__user=user)
            .values(
                'ingredient__name',
                'ingredient__measurement_unit'
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        combined_ingredients = {
            item['ingredient__name']: {
                'unit': item['ingredient__measurement_unit'],
                'amount': item['total_amount']
            }
            for item in aggregated
        }

        pdf = generate_shopping_cart_pdf(
            ingredients_by_recipe,
            combined_ingredients
        )

        return HttpResponse(
            pdf, content_type='application/pdf',
            headers={
                'Content-Disposition': (
                    'attachment; filename="shopping_cart.pdf"'
                )
            }
        )


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для пользователей:
    - регистрация, получение себя, смена пароля
    - подписка/отписка на других пользователей
    """
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

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def set_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(
                serializer.validated_data['new_password']
            )
            request.user.save()
            return Response({'status': 'Пароль успешно изменен'})
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            if Subscription.objects.filter(
                follower=request.user, following=author
            ).exists():
                return Response(
                    {'error': 'Уже подписаны.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if author == request.user:
                return Response(
                    {'error': 'Нельзя подписаться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(
                follower=request.user, following=author
            )
            return Response(
                {'success': 'Подписка оформлена.'},
                status=status.HTTP_201_CREATED
            )
        deleted, _ = Subscription.objects.filter(
            follower=request.user, following=author
        ).delete()
        if deleted:
            return Response(
                {'success': 'Подписка удалена.'},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {'error': 'Подписка не найдена.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class SubscriptionListView(ListAPIView):
    """
    Список подписок текущего пользователя.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = SubscriptionListSerializer
    pagination_class = SubscriptionPagination

    def get_queryset(self):
        return User.objects.filter(subscribers__follower=self.request.user)
