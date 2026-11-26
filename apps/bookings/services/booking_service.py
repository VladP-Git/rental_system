import logging
from datetime import date

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.exceptions import (
    BookingDateOverlapError,
    BookingError,
    BookingPermissionError,
    BookingStatusTransitionError,
)
from apps.bookings.models.booking import Booking, BookingStatus
from apps.bookings.repositories.booking_repository import BookingRepository
from apps.core.constants import DEFAULT_CANCELLATION_DELTA, MAX_BOOKING_HORIZON_DELTA
from apps.listings.models.listing import Listing

logger = logging.getLogger("apps.bookings")


class BookingService:
    @staticmethod
    @transaction.atomic
    def create_booking(
        *,
        tenant,
        listing_id: int,
        check_in: date,
        check_out: date,
        guests_count: int,
    ) -> Booking:
        today = timezone.localdate()

        if check_out <= check_in:
            raise BookingError(_("Check-out date must be later than check-in date."))
        if check_in < today:
            raise BookingError(_("Check-in date cannot be in the past."))
        if check_in > today + MAX_BOOKING_HORIZON_DELTA:
            raise BookingError(_("Booking cannot be made more than 360 days in advance."))

        try:
            listing = (
                Listing.objects.select_for_update()
                .select_related("landlord")
                .get(pk=listing_id)
            )
        except Listing.DoesNotExist as exc:
            raise BookingError(_("Listing not found.")) from exc

        if not listing.is_active:
            raise BookingError(_("This listing is currently inactive."))

        if listing.landlord_id == tenant.id:
            raise BookingPermissionError(_("Landlord cannot book their own listing."))

        if guests_count > listing.max_guests:
            raise BookingError(
                _("Number of guests exceeds the maximum allowed for this listing.")
            )

        if BookingRepository.has_overlapping_bookings(listing, check_in, check_out):
            raise BookingDateOverlapError(
                _("The selected dates are already occupied for this listing.")
            )

        booking = BookingRepository.create_booking(
            listing=listing,
            tenant=tenant,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests_count,
        )

        transaction.on_commit(
            lambda: logger.info(
                "Booking #%s created by user #%s for listing #%s (%s - %s)",
                booking.pk,
                tenant.id,
                listing.pk,
                check_in,
                check_out,
            )
        )
        return booking

    @staticmethod
    @transaction.atomic
    def confirm_booking(*, booking_id: int, landlord) -> Booking:
        try:
            booking = (
                Booking.objects.select_for_update()
                .select_related("listing")
                .get(pk=booking_id)
            )
        except Booking.DoesNotExist as exc:
            raise BookingError(_("Booking not found.")) from exc

        if booking.listing.landlord_id != landlord.id:
            raise BookingPermissionError(_("Only the listing owner can confirm this booking."))

        if booking.status != BookingStatus.PENDING:
            raise BookingStatusTransitionError(
                _("Only bookings in 'Pending confirmation' status can be confirmed.")
            )

        booking.status = BookingStatus.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])

        transaction.on_commit(
            lambda: logger.info("Booking #%s confirmed by landlord #%s", booking.pk, landlord.id)
        )
        return booking

    @staticmethod
    @transaction.atomic
    def reject_booking(*, booking_id: int, landlord) -> Booking:
        try:
            booking = (
                Booking.objects.select_for_update()
                .select_related("listing")
                .get(pk=booking_id)
            )
        except Booking.DoesNotExist as exc:
            raise BookingError(_("Booking not found.")) from exc

        if booking.listing.landlord_id != landlord.id:
            raise BookingPermissionError(_("Only the listing owner can reject this booking."))

        if booking.status != BookingStatus.PENDING:
            raise BookingStatusTransitionError(
                _("Only bookings in 'Pending confirmation' status can be rejected.")
            )

        booking.status = BookingStatus.REJECTED
        booking.save(update_fields=["status", "updated_at"])

        transaction.on_commit(
            lambda: logger.info("Booking #%s rejected by landlord #%s", booking.pk, landlord.id)
        )
        return booking

    @staticmethod
    @transaction.atomic
    def cancel_booking(*, booking_id: int, tenant) -> Booking:
        try:
            booking = Booking.objects.select_for_update().get(pk=booking_id)
        except Booking.DoesNotExist as exc:
            raise BookingError(_("Booking not found.")) from exc

        if booking.tenant_id != tenant.id:
            raise BookingPermissionError(_("Only the tenant who made the booking can cancel it."))

        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            raise BookingStatusTransitionError(
                _("Only pending or confirmed bookings can be canceled.")
            )

        today = timezone.localdate()
        cancellation_deadline = booking.check_in - DEFAULT_CANCELLATION_DELTA
        if today > cancellation_deadline:
            raise BookingStatusTransitionError(
                _("Cancellation is no longer allowed less than 2 days before check-in.")
            )

        booking.status = BookingStatus.CANCELED
        booking.canceled_at = timezone.now()
        booking.save(update_fields=["status", "canceled_at", "updated_at"])

        transaction.on_commit(
            lambda: logger.info("Booking #%s canceled by tenant #%s", booking.pk, tenant.id)
        )
        return booking

    @staticmethod
    @transaction.atomic
    def complete_booking(*, booking_id: int, actor) -> Booking:
        try:
            booking = (
                Booking.objects.select_for_update()
                .select_related("listing")
                .get(pk=booking_id)
            )
        except Booking.DoesNotExist as exc:
            raise BookingError(_("Booking not found.")) from exc

        is_landlord = booking.listing.landlord_id == actor.id
        if not (is_landlord or actor.is_staff):
            raise BookingPermissionError(_("You do not have permission to complete this booking."))

        if booking.status != BookingStatus.CONFIRMED:
            raise BookingStatusTransitionError(
                _("Only confirmed bookings can be marked as completed.")
            )

        if timezone.localdate() < booking.check_out:
            raise BookingStatusTransitionError(
                _("Booking cannot be marked as completed before the check-out date.")
            )

        booking.status = BookingStatus.COMPLETED
        booking.save(update_fields=["status", "updated_at"])

        transaction.on_commit(
            lambda: logger.info("Booking #%s marked as completed by user #%s", booking.pk, actor.id)
        )
        return booking
