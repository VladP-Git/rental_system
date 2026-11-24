from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self) -> tuple[int, dict[str, int]]:
        updated = self.update(is_deleted=True, deleted_at=timezone.now())
        return updated, {self.model._meta.label: updated}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        return super().delete()

    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(is_deleted=False)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(is_deleted=True)


class ActiveObjectsManager(models.Manager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)
