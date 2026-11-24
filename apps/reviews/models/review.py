from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.bookings.models.booking import Booking, BookingStatus
from apps.core.constants import MAX_RATING_VALUE, MIN_RATING_VALUE, REVIEW_WINDOW_DELTA
from apps.core.models import SoftDeleteModel
from apps.listings.models.listing import Listing


class Review(SoftDeleteModel):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="review",
        verbose_name="Бронирование",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name="Объявление",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name="Автор отзыва",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_RATING_VALUE),
            MaxValueValidator(MAX_RATING_VALUE),
        ],
        verbose_name="Оценка (1-5)",
    )
    comment = models.TextField(
        validators=[MinLengthValidator(5)],
        verbose_name="Текст отзыва",
    )

    class Meta:
        db_table = "reviews_reviews"
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        indexes = [
            models.Index(fields=["listing", "is_deleted", "-created_at"], name="idx_rev_listing_created"),
            models.Index(fields=["author", "is_deleted"], name="idx_rev_author"),
        ]

    def clean(self) -> None:
        super().clean()
        if not self.booking_id:
            return

        if self.booking.status != BookingStatus.COMPLETED:
            raise ValidationError({"booking": "Отзыв можно оставить только после завершения проживания."})

        if self.author_id and self.booking.tenant_id != self.author_id:
            raise ValidationError({"author": "Оставить отзыв может только арендатор данного бронирования."})

        today = timezone.localdate()
        if today > self.booking.check_out + REVIEW_WINDOW_DELTA:
            raise ValidationError({"booking": "Срок подачи отзыва по данному бронированию истек."})

    def __str__(self) -> str:
        return f"Отзыв #{self.pk} на объект #{self.listing_id} (оценка: {self.rating})"
