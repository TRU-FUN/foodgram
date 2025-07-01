from django.contrib import admin
from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    ordering = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'get_favorite_count', 'created_at')
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags', 'cooking_time')
    inlines = [RecipeIngredientInline]
    readonly_fields = ('get_favorite_count',)
    autocomplete_fields = ('author', 'tags')
    ordering = ('-created_at',)

    @admin.display(description='Добавлено в избранное')
    def get_favorite_count(self, obj):
        return obj.favorited_by.count()


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    list_select_related = ('recipe', 'ingredient')
    autocomplete_fields = ('recipe', 'ingredient')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_select_related = ('user', 'recipe')
    search_fields = ('user__email', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_select_related = ('user', 'recipe')
    search_fields = ('user__email', 'recipe__name')
