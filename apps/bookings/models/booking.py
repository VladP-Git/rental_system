from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.constants import MAX_BOOKING_HORIZON_DELTA
from apps.core.models import SoftDeleteModel
from apps.listings.models.listing import Listing


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Ожидает подтверждения"
    CONFIRMED = "CONFIRMED", "Подтверждено"
    REJECTED = "REJECTED", "Отклонено арендодателем"
    CANCELED = "CANCELED", "Отменено арендатором"
    COMPLETED = "COMPLETED", "Завершено"


class Booking(SoftDeleteModel):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Объявление",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Арендатор",
    )
    check_in = models.DateField(
        verbose_name="Дата заезда",
    )
    check_out = models.DateField(
        verbose_name="Дата выезда",
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Итоговая стоимость (EUR)",
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        verbose_name="Статус бронирования",
    )

    class Meta:
        db_table = "bookings_bookings"
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="chk_booking_checkout_after_checkin",
            ),
        ]
        indexes = [
            models.Index(
                fields=["listing", "status", "check_in", "check_out"],
                name="idx_bkg_overlap_lookup",
            ),
            models.Index(
                fields=["tenant", "status", "-check_in"],
                name="idx_bkg_tenant_status",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.check_in and self.check_out:
            if self.check_out <= self.check_in:
                raise ValidationError({"check_out": "Дата выезда должна быть позже даты заезда."})

            today = timezone.localdate()
            if self.pk is None and self.check_in < today:
                raise ValidationError({"check_in": "Дата заезда не может быть в прошлом."})

            if self.check_in > today + MAX_BOOKING_HORIZON_DELTA:
                raise ValidationError(
                    {"check_in": "Бронирование возможно не более чем на 360 дней вперед."}
                )

    def __str__(self) -> str:
        return f"Бронь #{self.pk} | Объект #{self.listing_id} ({self.check_in} — {self.check_out})"
