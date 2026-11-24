from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models

from apps.core.constants import (
    MAX_LISTING_PRICE,
    MAX_ROOMS_COUNT,
    MIN_LISTING_PRICE,
    MIN_ROOMS_COUNT,
)
from apps.core.models import SoftDeleteModel, TimeStampedModel


class PropertyType(models.TextChoices):
    APARTMENT = "APARTMENT", "Квартира"
    HOUSE = "HOUSE", "Дом"
    STUDIO = "STUDIO", "Студия"
    ROOM = "ROOM", "Комната"
    TOWNHOUSE = "TOWNHOUSE", "Таунхаус"


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
        verbose_name="Федеральная земля",
    )
    city = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        verbose_name="Город",
    )
    district = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Район",
    )
    postal_code = models.CharField(
        max_length=5,
        validators=[RegexValidator(regex=r"^\d{5}$", message="Индекс в Германии состоит из 5 цифр.")],
        verbose_name="Почтовый индекс",
    )
    street = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(2)],
        verbose_name="Улица",
    )
    house_number = models.CharField(
        max_length=20,
        verbose_name="Номер дома",
    )
    apartment_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Номер квартиры",
    )

    class Meta:
        db_table = "listings_addresses"
        verbose_name = "Адрес объекта"
        verbose_name_plural = "Адреса объектов"
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
        apt = f", кв. {self.apartment_number}" if self.apartment_number else ""
        return f"{self.postal_code} {self.city}, {self.street} {self.house_number}{apt}"


class Listing(SoftDeleteModel):
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listings",
        verbose_name="Арендодатель",
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="listings",
        verbose_name="Адрес",
    )
    title = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(5)],
        verbose_name="Заголовок",
    )
    description = models.TextField(
        validators=[MinLengthValidator(20)],
        verbose_name="Описание",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal(MIN_LISTING_PRICE)),
            MaxValueValidator(Decimal(MAX_LISTING_PRICE)),
        ],
        verbose_name="Цена за ночь (EUR)",
    )
    rooms_count = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_ROOMS_COUNT),
            MaxValueValidator(MAX_ROOMS_COUNT),
        ],
        verbose_name="Количество комнат",
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT,
        verbose_name="Тип жилья",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Объявление активно",
    )

    class Meta:
        db_table = "listings_listings"
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
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
        verbose_name="Пользователь",
    )
    raw_query = models.CharField(
        max_length=255,
        verbose_name="Исходный запрос",
    )
    normalized_query = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Нормализованный запрос",
    )

    class Meta:
        db_table = "listings_search_queries"
        verbose_name = "История поискового запроса"
        verbose_name_plural = "История поисковых запросов"
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
        verbose_name="Объявление",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viewed_listings",
        verbose_name="Пользователь",
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время просмотра",
    )

    class Meta:
        db_table = "listings_listing_views"
        verbose_name = "История просмотра объявления"
        verbose_name_plural = "История просмотров объявлений"
        indexes = [
            models.Index(fields=["listing", "-viewed_at"], name="idx_view_listing_time"),
            models.Index(fields=["user", "-viewed_at"], name="idx_view_user_time"),
        ]

    def __str__(self) -> str:
        return f"Просмотр #{self.listing_id} в {self.viewed_at:%Y-%m-%d %H:%M}"
