from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.reviews.models.review import Review


class SentimentLabel(models.TextChoices):
    POSITIVE = "POSITIVE", _("Positive")
    NEUTRAL = "NEUTRAL", _("Neutral")
    NEGATIVE = "NEGATIVE", _("Negative")


class AutoActionStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    EMAIL_SENT = "EMAIL_SENT", _("Email sent")
    FAILED = "FAILED", _("Failed")


class ReviewSentimentAnalysis(TimeStampedModel):
    review = models.OneToOneField(
        Review,
        on_delete=models.PROTECT,
        related_name="sentiment_analysis",
        verbose_name=_("Review"),
    )
    sentiment = models.CharField(
        max_length=20,
        choices=SentimentLabel.choices,
        verbose_name=_("Sentiment"),
    )
    provider_used = models.CharField(
        max_length=100,
        verbose_name=_("LLM provider used"),
    )
    generated_response = models.TextField(
        verbose_name=_("Generated response text"),
    )
    action_status = models.CharField(
        max_length=20,
        choices=AutoActionStatus.choices,
        default=AutoActionStatus.PENDING,
        verbose_name=_("Action status"),
    )
    error_details = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Error details"),
    )

    class Meta:
        db_table = "analytics_review_analyses"
        verbose_name = _("Review AI analysis")
        verbose_name_plural = _("Review AI analyses")
        indexes = [
            models.Index(fields=["sentiment", "action_status"], name="idx_sent_label_status"),
        ]

    def __str__(self) -> str:
        return f"Analysis for review #{self.review_id}: {self.get_sentiment_display()} ({self.provider_used})"
