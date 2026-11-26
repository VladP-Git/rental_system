from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self) -> tuple[int, dict[str, int]]:
        updated = self.update(deleted_at=timezone.now())
        return updated, {self.model._meta.label: updated}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        return super().delete()

    def restore(self) -> int:
        return self.update(deleted_at=None)

    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=False)


class ActiveObjectsManager(models.Manager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)
