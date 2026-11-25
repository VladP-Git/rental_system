from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.constants import (
    MAX_GUESTS_COUNT,
    MAX_LISTING_PRICE,
    MAX_ROOMS_COUNT,
    MIN_GUESTS_COUNT,
    MIN_LISTING_PRICE,
    MIN_ROOMS_COUNT,
)
from apps.core.managers import AllObjectsManager, SoftDeleteQuerySet
from apps.core.models import SoftDeleteModel, TimeStampedModel


class ListingQuerySet(SoftDeleteQuerySet):
    def bulk_create(self, objs, *args, **kwargs):
        for obj in objs:
            obj.full_clean()
        return super().bulk_create(objs, *args, **kwargs)


class ActiveListingManager(models.Manager):
    def get_queryset(self) -> ListingQuerySet:
        return ListingQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllListingManager(AllObjectsManager):
    def get_queryset(self) -> ListingQuerySet:
        return ListingQuerySet(self.model, using=self._db)


class PropertyType(models.TextChoices):
    APARTMENT = "APARTMENT", _("Apartment")
    HOUSE = "HOUSE", _("House")
    STUDIO = "STUDIO", _("Studio")
    ROOM = "ROOM", _("Room")
    TOWNHOUSE = "TOWNHOUSE", _("Townhouse")


class FederalState(models.TextChoices):
    BADEN_WUERTTEMBERG = "BW", "Baden-Württemberg"
    BAYERN = "BY", "Bayern"
    BERLIN = "BE", "Berlin"
    BRANDENBURG = "BB", "Brandenburg"
    BREMEN = "HB", "Bremen"
    HAMBURG = "HH", "Hamburg"
    HESSEN = "HE", "Hessen"
    MECKLENBURG_VORPOMMERN = "MV", "Mecklenburg-Vorpommern"
    NIEDERSACHSEN = "NI", "Niedersachsen"
    NORDRHEIN_WESTFALEN = "NW", "Nordrhein-Westfalen"
    RHEINLAND_PFALZ = "RP", "Rheinland-Pfalz"
    SAARLAND = "SL", "Saarland"
    SACHSEN = "SN", "Sachsen"
    SACHSEN_ANHALT = "ST", "Sachsen-Anhalt"
    SCHLESWIG_HOLSTEIN = "SH", "Schleswig-Holstein"
    THUERINGEN = "TH", "Thüringen"


class Address(SoftDeleteModel):
    federal_state = models.CharField(
        max_length=2,
        choices=FederalState.choices,
        verbose_name=_("Federal state"),
    )
    city = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        verbose_name=_("City"),
    )
    district = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("District"),
    )
    postal_code = models.CharField(
        max_length=5,
        validators=[RegexValidator(regex=r"^\d{5}$", message=_("German postal code must consist of 5 digits."))],
        verbose_name=_("Postal code"),
    )
    street = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(2)],
        verbose_name=_("Street"),
    )
    house_number = models.CharField(
        max_length=20,
        verbose_name=_("House number"),
    )
    apartment_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Apartment number"),
    )

    class Meta:
        db_table = "listings_addresses"
        verbose_name = _("Property address")
        verbose_name_plural = _("Property addresses")
        constraints = [
            models.UniqueConstraint(
                fields=["postal_code", "city", "street", "house_number", "apartment_number"],
                condition=models.Q(is_deleted=False),
                name="uq_active_property_address",
            ),
        ]
        indexes = [
            models.Index(fields=["city", "federal_state"], name="idx_addr_city_state"),
            models.Index(fields=["city", "district"], name="idx_addr_city_district"),
        ]

    def __str__(self) -> str:
        apt = f", apt. {self.apartment_number}" if self.apartment_number else ""
        return f"{self.postal_code} {self.city}, {self.street} {self.house_number}{apt}"


class Listing(SoftDeleteModel):
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listings",
        verbose_name=_("Landlord"),
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="listings",
        verbose_name=_("Address"),
    )
    title = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(5)],
        verbose_name=_("Title"),
    )
    description = models.TextField(
        validators=[MinLengthValidator(20)],
        verbose_name=_("Description"),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal(MIN_LISTING_PRICE)),
            MaxValueValidator(Decimal(MAX_LISTING_PRICE)),
        ],
        verbose_name=_("Price per night (EUR)"),
    )
    rooms_count = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_ROOMS_COUNT),
            MaxValueValidator(MAX_ROOMS_COUNT),
        ],
        verbose_name=_("Rooms count"),
    )
    max_guests = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(MIN_GUESTS_COUNT),
            MaxValueValidator(MAX_GUESTS_COUNT),
        ],
        verbose_name=_("Maximum guests"),
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT,
        verbose_name=_("Property type"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is active"),
    )

    objects = ActiveListingManager()
    all_objects = AllListingManager()

    class Meta:
        db_table = "listings_listings"
        verbose_name = _("Listing")
        verbose_name_plural = _("Listings")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    price__gt=Decimal("0.00"),
                    price__lte=Decimal(MAX_LISTING_PRICE),
                ),
                name="chk_listing_price_range",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    rooms_count__gte=MIN_ROOMS_COUNT,
                    rooms_count__lte=MAX_ROOMS_COUNT,
                ),
                name="chk_listing_rooms_range",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    max_guests__gte=MIN_GUESTS_COUNT,
                    max_guests__lte=MAX_GUESTS_COUNT,
                ),
                name="chk_listing_guests_range",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "is_deleted", "price"], name="idx_lst_act_price"),
            models.Index(fields=["is_active", "is_deleted", "rooms_count", "property_type"], name="idx_lst_act_specs"),
            models.Index(fields=["is_active", "is_deleted", "-created_at"], name="idx_lst_act_created"),
            models.Index(fields=["landlord", "is_deleted"], name="idx_lst_landlord"),
        ]

    def __str__(self) -> str:
        return f"[{self.get_property_type_display()}] {self.title} ({self.price} EUR)"


class SearchQueryHistory(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_queries",
        verbose_name=_("User"),
    )
    raw_query = models.CharField(
        max_length=255,
        verbose_name=_("Raw query"),
    )
    normalized_query = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_("Normalized query"),
    )

    class Meta:
        db_table = "listings_search_queries"
        verbose_name = _("Search query history")
        verbose_name_plural = _("Search queries history")
        indexes = [
            models.Index(fields=["normalized_query", "-created_at"], name="idx_search_norm_created"),
        ]

    def __str__(self) -> str:
        return f"{self.normalized_query} ({self.created_at:%Y-%m-%d %H:%M})"


class ListingViewHistory(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="views_history",
        verbose_name=_("Listing"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viewed_listings",
        verbose_name=_("User"),
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Viewed at"),
    )

    class Meta:
        db_table = "listings_listing_views"
        verbose_name = _("Listing view history")
        verbose_name_plural = _("Listing views history")
        indexes = [
            models.Index(fields=["listing", "-viewed_at"], name="idx_view_listing_time"),
            models.Index(fields=["user", "-viewed_at"], name="idx_view_user_time"),
        ]

    def __str__(self) -> str:
        return f"View #{self.listing_id} at {self.viewed_at:%Y-%m-%d %H:%M}"
