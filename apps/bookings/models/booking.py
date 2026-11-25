from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.constants import (
    DEFAULT_CANCELLATION_DELTA,
    MAX_BOOKING_HORIZON_DELTA,
    MIN_GUESTS_COUNT,
)
from apps.core.models import SoftDeleteModel
from apps.listings.models.listing import Listing


class BookingStatus(models.IntegerChoices):
    PENDING = 1, _("Pending confirmation")
    CONFIRMED = 2, _("Confirmed")
    REJECTED = 3, _("Rejected by landlord")
    CANCELED = 4, _("Canceled by tenant")
    COMPLETED = 5, _("Completed")


class Booking(SoftDeleteModel):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Listing"),
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Tenant"),
    )
    check_in = models.DateField(
        verbose_name=_("Check-in date"),
    )
    check_out = models.DateField(
        verbose_name=_("Check-out date"),
    )
    guests_count = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(MIN_GUESTS_COUNT)],
        verbose_name=_("Guests count"),
    )
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Fixed price per night (EUR)"),
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Applied discount (EUR)"),
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Fixed total price (EUR)"),
    )
    status = models.PositiveSmallIntegerField(
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        verbose_name=_("Booking status"),
    )
    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Canceled at"),
    )

    class Meta:
        db_table = "bookings_bookings"
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="chk_booking_checkout_after_checkin",
            ),
            models.CheckConstraint(
                condition=models.Q(total_price__gt=Decimal("0.00")),
                name="chk_booking_total_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(guests_count__gte=MIN_GUESTS_COUNT),
                name="chk_booking_guests_positive",
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
        if not self.check_in:
            return

        today = timezone.localdate()

        if self._state.adding:
            if self.check_in < today:
                raise ValidationError({"check_in": _("Check-in date cannot be in the past.")})
            if self.check_in > today + MAX_BOOKING_HORIZON_DELTA:
                raise ValidationError(
                    {"check_in": _("Booking cannot be made more than 360 days in advance.")}
                )
            if self.listing_id and self.guests_count > self.listing.max_guests:
                raise ValidationError(
                    {"guests_count": _("Number of guests exceeds the maximum allowed for this listing.")}
                )

        if self.status == BookingStatus.CANCELED and not self.canceled_at:
            cancellation_deadline = self.check_in - DEFAULT_CANCELLATION_DELTA
            if today > cancellation_deadline:
                raise ValidationError(
                    {"status": _("Cancellation deadline for this booking has passed.")}
                )

    def save(self, *args, **kwargs):
        if self._state.adding and self.listing_id and self.check_in and self.check_out:
            if not self.price_per_night:
                self.price_per_night = self.listing.price
            if not self.total_price:
                nights = (self.check_out - self.check_in).days
                raw_total = self.price_per_night * Decimal(nights)
                self.total_price = max(Decimal("0.01"), raw_total - self.discount_amount)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Booking #{self.pk} | Listing #{self.listing_id} ({self.check_in} — {self.check_out})"
