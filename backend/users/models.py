from django.core.exceptions import ValidationError
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Менеджер пользователей, позволяющий создавать обычных и
    суперпользователей по email.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email обязателен'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError(_('Суперпользователь должен иметь is_staff=True'))
        if not extra_fields.get('is_superuser'):
            raise ValueError(
                _('Суперпользователь должен иметь is_superuser=True')
            )

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Пользовательская модель, использующая email для аутентификации.
    """
    username = models.CharField(
        _('Имя пользователя'),
        max_length=150,
        unique=True,
        help_text=_('Обязательное. Не более 150 символов.'),
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'unique': _("Пользователь с таким именем уже существует."),
        },
    )
    email = models.EmailField(_('Email'), unique=True)
    first_name = models.CharField(_('Имя'), max_length=150)
    last_name = models.CharField(_('Фамилия'), max_length=150)
    avatar = models.ImageField(
        _('Аватар'),
        upload_to='avatars/',
        blank=True,
        default='',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['email']

    def __str__(self):
        return self.email


class Subscription(models.Model):
    """
    Модель подписки между пользователями.
    """
    follower = models.ForeignKey(
        User,
        related_name='subscriptions',
        on_delete=models.CASCADE,
        verbose_name=_('Подписчик'),
    )
    following = models.ForeignKey(
        User,
        related_name='subscribers',
        on_delete=models.CASCADE,
        verbose_name=_('Вы подписаны на'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        verbose_name = _('Подписка')
        verbose_name_plural = _('Подписки')

    def __str__(self):
        return f'{self.follower} → {self.following}'

    def clean(self):
        if self.follower == self.following:
            raise ValidationError(_('Нельзя подписаться на самого себя.'))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
