from datetime import date

from django.db.models import Case, QuerySet, Value, When

from apps.bookings.models.booking import Booking, BookingStatus
from apps.listings.models.listing import Listing


class BookingRepository:
    OCCUPYING_STATUSES: tuple[int, ...] = (
        BookingStatus.PENDING,
        BookingStatus.CONFIRMED,
    )

    @classmethod
    def has_overlapping_bookings(
        cls,
        listing: Listing,
        check_in: date,
        check_out: date,
    ) -> bool:
        """
        Проверяет наличие пересечений дат по индексу idx_bkg_overlap_lookup.
        Строгое неравенство (check_in < new_check_out и check_out > new_check_in)
        позволяет заезд нового гостя в день выезда предыдущего.
        """
        return Booking.objects.filter(
            listing=listing,
            status__in=cls.OCCUPYING_STATUSES,
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exists()

    @staticmethod
    def create_booking(
        *,
        listing: Listing,
        tenant,
        check_in: date,
        check_out: date,
        guests_count: int,
    ) -> Booking:
        booking = Booking(
            listing=listing,
            tenant=tenant,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests_count,
            price_per_night=listing.price,
            status=BookingStatus.PENDING,
        )
        booking.full_clean()
        booking.save()
        return booking

    @staticmethod
    def get_tenant_bookings(tenant) -> QuerySet[Booking]:
        return (
            Booking.objects.filter(tenant=tenant)
            .select_related("listing", "listing__address")
            .order_by("-check_in", "-created_at")
        )

    @staticmethod
    def get_landlord_bookings(landlord) -> QuerySet[Booking]:
        status_priority = Case(
            When(status=BookingStatus.PENDING, then=Value(0)),
            When(status=BookingStatus.CONFIRMED, then=Value(1)),
            When(status=BookingStatus.COMPLETED, then=Value(2)),
            When(status=BookingStatus.CANCELED, then=Value(3)),
            When(status=BookingStatus.REJECTED, then=Value(4)),
            default=Value(5),
        )
        return (
            Booking.objects.filter(listing__landlord=landlord)
            .select_related("listing", "listing__address", "tenant")
            .order_by(status_priority, "check_in")
        )
