from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.bookings.models.booking import Booking, BookingStatus
from apps.core.constants import (
    MAX_BOOKING_HORIZON_DELTA,
    MAX_GUESTS_COUNT,
    MIN_GUESTS_COUNT,
)
from apps.listings.models.listing import Listing


class BookingListSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_city = serializers.CharField(source="listing.address.city", read_only=True)
    tenant_email = serializers.EmailField(source="tenant.email", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    nights_count = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "listing",
            "listing_title",
            "listing_city",
            "tenant",
            "tenant_email",
            "check_in",
            "check_out",
            "guests_count",
            "price_per_night",
            "nights_count",
            "total_price",
            "status",
            "status_display",
            "canceled_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.filter(is_active=True),
        label=_("Listing"),
    )
    check_in = serializers.DateField(label=_("Check-in date"))
    check_out = serializers.DateField(label=_("Check-out date"))
    guests_count = serializers.IntegerField(
        min_value=MIN_GUESTS_COUNT,
        max_value=MAX_GUESTS_COUNT,
        default=1,
        label=_("Guests count"),
    )

    def validate(self, attrs: dict) -> dict:
        check_in = attrs["check_in"]
        check_out = attrs["check_out"]
        listing = attrs["listing"]
        guests_count = attrs["guests_count"]
        today = timezone.localdate()

        if check_out <= check_in:
            raise serializers.ValidationError(
                {"check_out": _("Check-out date must be later than check-in date.")}
            )

        if check_in < today:
            raise serializers.ValidationError(
                {"check_in": _("Check-in date cannot be in the past.")}
            )

        if check_in > today + MAX_BOOKING_HORIZON_DELTA:
            raise serializers.ValidationError(
                {"check_in": _("Booking cannot be made more than 360 days in advance.")}
            )

        if guests_count > listing.max_guests:
            raise serializers.ValidationError(
                {"guests_count": _("Number of guests exceeds the maximum allowed for this listing.")}
            )

        request = self.context.get("request")
        if request and request.user.is_authenticated and listing.landlord_id == request.user.id:
            raise serializers.ValidationError(
                {"listing": _("Landlord cannot book their own listing.")}
            )

        return attrs


class BookingStatusActionSerializer(serializers.Serializer):
    """
    An empty serializer for Swagger/OpenAPI documentation of status-change endpoints
    (confirm, reject, cancel, complete) that do not require a request body.
    """

    status = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    canceled_at = serializers.DateTimeField(read_only=True)
