from django.db import models
import django.dispatch

bulk_update = django.dispatch.Signal(providing_args=["instance"])
bulk_delete = django.dispatch.Signal(providing_args=["instance"])

class QuerySet(models.query.QuerySet):
    def delete(self, *args, **kwargs):
        #copy the queryset
        qs = self.all()
        #execute the update
        super(QuerySet, self).delete(*args, **kwargs)
        for instance in qs:
            bulk_delete.send_robust(self.model, instance=instance)

    def update(self, *args, **kwargs):
        #copy the queryset
        qs = self.all()
        #execute the update
        rows = super(QuerySet, self).update(*args, **kwargs)
        for instance in qs:
            bulk_update.send_robust(self.model, instance=instance)
        #return the original update result
        return rows


class Manager(models.Manager):
    def get_query_set(self):
        return QuerySet(self.model, using=self._db)


class Model(models.Model): 
    class Meta:
        abstract = True

    objects = Manager()
