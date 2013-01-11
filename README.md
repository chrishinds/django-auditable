#django-auditable

_django-auditable_ provides audit records for django models. The audit
 records are designed to be human readable, include many-to-many
 fields, have transaction-like semantics, and cover bulk operations
 like update and delete.  The library is designed to be as djangonic
 as possible.

## Basic Use

This repo contains the development version. Ordinarily It's best to
install the production package *[pending release!]*

    $ sudo pip install django-auditable

Then define your models. Models which you'd like to audit, like
`PizzaOrder`, need to subclass `auditable.Model`. To make an audit
model, like `PizzaOrderAudit`, just add : `__metaclass__ =
auditable.metaclass_factory(PizzaOrder)`.  You can tailor other fields
as you wish.

    import auditable
    from django.db import models

    class Chef(models.Model):
        name = models.CharField('name', max_length=10)
        def __unicode__(self):
            return unicode(self.id) + ': ' + self.name

    class Topping(models.Model):
        name = models.CharField('name', max_length=10, primary_key=True)
        def __unicode__(self):
            return self.name

    class PizzaOrder(auditable.Model):
        customer_name = models.CharField(u'Baz', max_length=255, blank=False)
        cooked_by = models.ForeignKey(Chef, null=True)
        toppings = models.ManyToManyField(Topping)

    class PizzaOrderAudit(models.Model):
        __metaclass__ = auditable.metaclass_factory(PizzaOrder)
        audit_row_inserted_at = models.DateTimeField(editable=False, auto_now_add=True)
        audit_row_updated_at = models.DateTimeField(editable=False, auto_now=True)


For best results add the following to your `settings.py` file (note the order of the middleware items)

    AUDITABLE_CHECKPOINTED=True

    MIDDLEWARE_CLASSES = (
        ...
        'audible.AuditMiddleware',
        'django.middleware.transaction.TransactionMiddleware',
        ... )

If you had a view which did various things with pizza orders:

    def pizzaria(request):
        i = models.PizzaOrder(customer_name='Yoko', cooked_by = models.Chef.objects.get(name='Lennon'))
        i.save()
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        i.toppings.clear()

        ii = models.PizzaOrder(customer_name = 'McCartney', cooked_by = models.Chef.objects.get(name='Lennon'))
        ii.save()
        ii.toppings.add(models.Topping.objects.get(name='cheese'),
                        models.Topping.objects.get(name='vegetables'))
        ii.toppings.remove(models.Topping.objects.get(name='vegetables'))

        models.PizzaOrder.objects.update(cooked_by = models.Chef.objects.get(name='Starr'))
	...

Then after view execution, your `PizzaOrderAudit` table would look like this:

    $ ./manage.py dbshell
    demo=# SELECT * FROM demo_pizzaorderaudit;

     id | customer_name | cooked_by | toppings    | audit_row_inserted_at      | audit_row_updated_at 
    ----+---------------+-----------+-------------+----------------------------+----------------------------
     1  | Yoko          | 2: Starr  | []          | 2013-01-10 12:07:35.121369 | 2013-01-10 12:07:35.122018
     2  | McCartney     | 2: Starr  | [u'cheese'] | 2013-01-10 12:07:35.121596 | 2013-01-10 12:07:35.122343


## Other Topics Needing Documentation

* inheriting audit models
* manual checkpointing
* immediate auditing
* excluding fields
* auditable managers
* bulk insert operations