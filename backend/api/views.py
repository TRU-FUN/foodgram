import base64
import time

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED, HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST
)
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from recipes.models import (
    Favorite, Ingredient, Recipe, ShoppingCart,
    RecipeIngredient, Tag, User
)
from recipes.serializers import (
    IngredientSerializer, RecipeCreateUpdateSerializer,
    RecipeSerializer, TagSerializer
)
from users.models import Subscription
from users.serializers import (
    PasswordChangeSerializer, SubscriptionListSerializer,
    UserCreateSerializer, UserSerializer
)
from .utils import generate_shopping_cart_pdf
from .paginations import SubscriptionPagination
from .filters import IngredientFilter, RecipeFilter
from .mixins import RelationHandlerMixin


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
    filter_backends = [DjangoFilterBackend]
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
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


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
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'get_link']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
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

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        return self.handle_relation(request, pk, Favorite, 'избранное')

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        return self.handle_relation(
            request, pk, ShoppingCart, 'список покупок'
        )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='get-link',
        url_name='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        full_link = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return Response({'short-link': full_link})


class DownloadShoppingCart(APIView):
    """
    Эндпоинт для скачивания списка покупок в PDF-формате.

    Группирует ингредиенты по рецептам и создает PDF-документ.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        if not shopping_cart.exists():
            return HttpResponse(
                'Ваш список покупок пуст.',
                content_type='text/plain'
            )

        ingredients_by_recipe = {}
        combined_ingredients = {}

        for item in shopping_cart:
            recipe = item.recipe
            name = recipe.name
            ingredients = RecipeIngredient.objects.filter(
                recipe=recipe
            ).select_related('ingredient')

            ingredients_by_recipe[name] = []
            for ri in ingredients:
                ingredient = ri.ingredient
                text = (
                    f'{ingredient.name} ({ingredient.measurement_unit}) - '
                    f'{ri.amount}'
                )
                ingredients_by_recipe[name].append(text)

                if ingredient.name in combined_ingredients:
                    combined_ingredients[ingredient.name]['amount'] += (
                        ri.amount
                    )
                else:
                    combined_ingredients[ingredient.name] = {
                        'amount': ri.amount,
                        'unit': ingredient.measurement_unit
                    }

        pdf_file = generate_shopping_cart_pdf(
            ingredients_by_recipe, combined_ingredients
        )

        if not pdf_file:
            return HttpResponse(
                'Ошибка при генерации PDF',
                content_type='text/plain',
                status=500
            )

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.pdf"'
        )
        return response


class UserAvatarView(APIView):
    """
    Эндпоинт для обновления и удаления аватара пользователя.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def put(self, request):
        """
        Загрузка нового аватара (файл или base64).
        """
        user = request.user
        avatar = request.FILES.get('avatar')
        if not avatar and 'avatar' in request.data:
            try:
                format, imgstr = request.data['avatar'].split(';base64,')
                ext = format.split('/')[-1]
                avatar = ContentFile(
                    base64.b64decode(imgstr), name=f'avatar.{ext}')
            except Exception:
                return Response(
                    {'error': 'Некорректный формат изображения'},
                    status=400)

        if not avatar:
            return Response({'error': 'Файл не найден'}, status=400)

        if user.avatar:
            old_avatar_path = user.avatar.name
            if default_storage.exists(old_avatar_path):
                default_storage.delete(old_avatar_path)

        user.avatar = avatar
        user.save()
        return Response(
            {
                'message': 'Аватар обновлён',
                'avatar_url': f'{user.avatar.url}?t={int(time.time())}',
            },
            status=200
        )

    def delete(self, request):
        """
        Удаление текущего аватара пользователя.
        """
        user = request.user
        if user.avatar:
            old_avatar_path = user.avatar.name
            user.avatar.delete(save=True)
            if default_storage.exists(old_avatar_path):
                default_storage.delete(old_avatar_path)
            return Response({'message': 'Аватар удалён'}, status=204)
        return Response({'error': 'Аватар отсутствует'}, status=400)


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
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
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
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        if request.method == 'POST':
            if Subscription.objects.filter(
                follower=request.user, following=author
            ).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя.'},
                    status=HTTP_400_BAD_REQUEST
                )
            if author == request.user:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя.'},
                    status=HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(
                follower=request.user,
                following=author
            )
            return Response(
                {'success': f'Вы подписались на {author.email}'},
                status=HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                follower=request.user, following=author
            )
            if subscription.exists():
                subscription.delete()
                return Response(
                    {'success': f'Вы отписались от {author.email}'},
                    status=HTTP_204_NO_CONTENT
                )
            return Response(
                {'error': 'Вы не подписаны на этого пользователя.'},
                status=HTTP_400_BAD_REQUEST
            )


class SubscriptionListView(ListAPIView):
    """
    Эндпоинт для получения списка подписок текущего пользователя.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionListSerializer
    pagination_class = SubscriptionPagination

    def get_queryset(self):
        return User.objects.filter(subscribers__follower=self.request.user)
