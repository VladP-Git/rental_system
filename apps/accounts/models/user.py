from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.managers import AllObjectsManager, SoftDeleteQuerySet
from apps.core.models import SoftDeleteModel


class CustomUserManager(BaseUserManager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def create_user(self, email: str, name: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError(_("The email field must be set."))
        if not name:
            raise ValueError(_("The name field must be set."))

        normalized_email = self.normalize_email(email).strip().lower()
        user = self.model(email=normalized_email, name=name.strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, name: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email=email, name=name, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name=_("Email address"),
    )
    name = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(2)],
        verbose_name=_("User name"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is active"),
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_("Staff status"),
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Date joined"),
    )

    objects = CustomUserManager()
    all_objects = AllObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "accounts_users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="uq_user_email_lower",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
