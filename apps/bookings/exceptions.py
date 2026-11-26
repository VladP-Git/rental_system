from django.utils.translation import gettext_lazy as _


class BookingError(Exception):
    default_message = _("Booking operation failed.")

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class BookingDateOverlapError(BookingError):
    default_message = _("The selected dates overlap with an existing booking.")


class BookingPermissionError(BookingError):
    default_message = _("You do not have permission to perform this action on the booking.")


class BookingStatusTransitionError(BookingError):
    default_message = _("Invalid booking status transition or deadline exceeded.")
