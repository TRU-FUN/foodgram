from django_filters import rest_framework as filters

from recipes.models import Recipe, Ingredient


class RecipeFilter(filters.FilterSet):
    tags = filters.CharFilter(method='filter_tags', label='Filter by tags')
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ['tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_tags(self, queryset, name, value):
        tag_slugs = self.request.query_params.getlist('tags')
        if tag_slugs:
            queryset = queryset.filter(tags__slug__in=tag_slugs)
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        return (queryset.filter(favorited_by__user=user)
                if value else queryset.exclude(favorited_by__user=user))

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(in_carts__user=user)
        else:
            return queryset.exclude(in_carts__user=user)


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(method='filter_name')

    class Meta:
        model = Ingredient
        fields = ['name']

    def filter_name(self, queryset, name, value):
        return queryset.filter(name__icontains=value)
