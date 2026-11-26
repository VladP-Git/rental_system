from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.models.booking import Booking, BookingStatus
from apps.core.constants import MAX_RATING_VALUE, MIN_RATING_VALUE, REVIEW_WINDOW_DELTA
from apps.core.models import SoftDeleteModel


class Review(SoftDeleteModel):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name=_("Booking"),
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_RATING_VALUE),
            MaxValueValidator(MAX_RATING_VALUE),
        ],
        verbose_name=_("Rating (1-5)"),
    )
    comment = models.TextField(
        validators=[MinLengthValidator(5)],
        verbose_name=_("Review text"),
    )

    class Meta:
        db_table = "reviews_reviews"
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_active_review_per_booking",
            ),
        ]
        indexes = [
            models.Index(fields=["deleted_at", "-created_at"], name="idx_rev_active_created"),
        ]

    def clean(self) -> None:
        super().clean()
        if not self.booking_id:
            return

        if self.booking.status != BookingStatus.COMPLETED:
            raise ValidationError({"booking": _("A review can only be submitted after the stay is completed.")})

        today = timezone.localdate()
        if today > self.booking.check_out + REVIEW_WINDOW_DELTA:
            raise ValidationError({"booking": _("The review submission period for this booking has expired.")})

    def __str__(self) -> str:
        return f"Review #{self.pk} for booking #{self.booking_id} (rating: {self.rating})"
