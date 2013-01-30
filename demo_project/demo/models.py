import auditable
from django.db import models

#Pizza models

class Chef(models.Model):
    name = models.CharField('name', max_length=10)
    def __unicode__(self):
        return unicode(self.id) + ': ' + self.name


class Topping(models.Model):
    name = models.CharField('name', max_length=10, primary_key=True)
    def __unicode__(self):
        return self.name


class PizzaOrder(auditable.Model):
    order_kind = 'web'
    def calculate_cost(self):
        return 12.99
    customer_name = models.CharField(u'Baz', max_length=255, blank=False)
    cooked_by = models.ForeignKey(Chef, null=True)
    toppings = models.ManyToManyField(Topping)

    class Meta:
        app_label='demo'

class Larder(auditable.Model):
    ingredient = models.CharField(max_length=255)
    quantity = models.IntegerField()

class DoubleTest(auditable.Model):
    number = models.IntegerField()

# Audit models

class BaseAudit(models.Model):
    audit_row_inserted_at = models.DateTimeField(editable=False, auto_now_add=True)
    audit_row_updated_at = models.DateTimeField(editable=False, auto_now=True)
    class Meta:
        abstract = True
    
class PizzaOrderAudit(BaseAudit):
    __metaclass__ = auditable.metaclass_factory(PizzaOrder)
    pizza_audit_record_examined = models.BooleanField(default=False)

class SlimlineAudit(BaseAudit):
    __metaclass__ =  auditable.metaclass_factory(PizzaOrder, exclude={'toppings', 'cooked_by'})

class LarderAudit(BaseAudit):
    __metaclass__ = auditable.metaclass_factory(Larder)
    
class DoubleTestAuditOne(models.Model):
    __metaclass__ = auditable.metaclass_factory(DoubleTest)

class DoubleTestAuditTwo(models.Model):
    __metaclass__ = auditable.metaclass_factory(DoubleTest)

