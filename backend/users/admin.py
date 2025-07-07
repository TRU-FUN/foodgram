from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Subscription, User


class FollowingInline(admin.TabularInline):
    model = Subscription
    fk_name = 'follower'
    extra = 0
    verbose_name = 'Подписка на пользователя'
    verbose_name_plural = 'Подписки'


class FollowersInline(admin.TabularInline):
    model = Subscription
    fk_name = 'following'
    extra = 0
    verbose_name = 'Подписчик'
    verbose_name_plural = 'Подписчики'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id', 'email', 'first_name', 'last_name',
        'is_active', 'recipes_count', 'subscribers_count'
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('last_login', 'date_joined')
    inlines = [FollowingInline, FollowersInline]

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация', {
            'fields': (
                'first_name', 'last_name', 'avatar'
            )
        }),
        ('Права доступа', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            )
        }),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2',
                'first_name', 'last_name', 'avatar',
                'is_active', 'is_staff', 'is_superuser',
            ),
        }),
    )

    def recipes_count(self, obj):
        return obj.recipes.count()
    recipes_count.short_description = 'Рецептов'

    def subscribers_count(self, obj):
        return obj.subscribers.count()
    subscribers_count.short_description = 'Подписчиков'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following')
    search_fields = ('follower__email', 'following__email')
    list_filter = ('follower', 'following')
    ordering = ('follower',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'follower', 'following'
        )
