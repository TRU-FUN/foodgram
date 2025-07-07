from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet,
    TagViewSet,
    RecipeViewSet,
    DownloadShoppingCart,
    UserViewSet,
    SubscriptionListView,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path(
        'recipes/download_shopping_cart/',
        DownloadShoppingCart.as_view(),
        name='download_shopping_cart',
    ),
    path(
        'users/<int:pk>/subscribe/',
        UserViewSet.as_view({'post': 'subscribe', 'delete': 'subscribe'}),
        name='subscribe',
    ),
    path(
        'users/subscriptions/',
        SubscriptionListView.as_view(),
        name='subscriptions'
    ),
    path('', include(router.urls)),
]
