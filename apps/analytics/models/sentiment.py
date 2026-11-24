from django.db import models

from apps.core.models import TimeStampedModel
from apps.reviews.models.review import Review


class SentimentLabel(models.TextChoices):
    POSITIVE = "POSITIVE", "Позитивный"
    NEUTRAL = "NEUTRAL", "Нейтральный"
    NEGATIVE = "NEGATIVE", "Негативный"


class AutoActionStatus(models.TextChoices):
    PENDING = "PENDING", "Ожидает обработки"
    EMAIL_SENT = "EMAIL_SENT", "Письмо отправлено"
    FAILED = "FAILED", "Ошибка обработки"


class ReviewSentimentAnalysis(TimeStampedModel):
    review = models.OneToOneField(
        Review,
        on_delete=models.PROTECT,
        related_name="sentiment_analysis",
        verbose_name="Отзыв",
    )
    sentiment = models.CharField(
        max_length=20,
        choices=SentimentLabel.choices,
        verbose_name="Тональность",
    )
    provider_used = models.CharField(
        max_length=100,
        verbose_name="Использованный LLM-провайдер",
    )
    generated_response = models.TextField(
        verbose_name="Сгенерированный текст ответа/компенсации",
    )
    promo_code = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Сгенерированный промокод на скидку",
    )
    action_status = models.CharField(
        max_length=20,
        choices=AutoActionStatus.choices,
        default=AutoActionStatus.PENDING,
        verbose_name="Статус реакции",
    )
    error_details = models.TextField(
        blank=True,
        default="",
        verbose_name="Детали ошибки (при сбое)",
    )

    class Meta:
        db_table = "analytics_review_analyses"
        verbose_name = "ИИ-анализ отзыва"
        verbose_name_plural = "ИИ-анализы отзывов"
        indexes = [
            models.Index(fields=["sentiment", "action_status"], name="idx_sent_label_status"),
        ]

    def __str__(self) -> str:
        return f"Анализ отзыва #{self.review_id}: {self.get_sentiment_display()} ({self.provider_used})"
