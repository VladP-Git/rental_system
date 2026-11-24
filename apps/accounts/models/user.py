from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from apps.core.managers import AllObjectsManager, SoftDeleteQuerySet
from apps.core.models import SoftDeleteModel


class CustomUserManager(BaseUserManager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def create_user(self, email: str, name: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Поле email обязательно для заполнения.")
        if not name:
            raise ValueError("Поле имени обязательно для заполнения.")

        normalized_email = self.normalize_email(email).lower()
        user = self.model(email=normalized_email, name=name.strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, name: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(email=email, name=name, password=password, **extra_fields)



class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name="Электронная почта",
    )
    name = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(2)],
        verbose_name="Имя пользователя",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Доступ в панель администратора",
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата регистрации",
    )

    objects = CustomUserManager()
    all_objects = AllObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "accounts_users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        indexes = [
            models.Index(fields=["email", "is_active"], name="idx_user_email_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
