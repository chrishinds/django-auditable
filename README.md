#django-auditable

_django-auditable_ provides audit records for django models. The
 records are designed to be tabular and human readable, include
 many-to-many fields, have transaction-like semantics, and cover bulk
 operations like update and delete. 

## Install

Install the production package

    $ sudo pip install django-auditable

or clone this repo which contains the auditable package itself and a
django app from which unittests can be run (`python manage.py test
demo`).


## Basic Use

* Models which you'd like to audit, like `PizzaOrder`, need to
subclass `auditable.Model`.  
* To make an audit model, like `PizzaOrderAudit`, add : `__metaclass__
= auditable.metaclass_factory(PizzaOrder)`, and any other fields you
need.

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


Add the following to your `settings.py` file (this order will commit
audit records within TransactionMiddleware)

    AUDITABLE_CHECKPOINTED=True

    MIDDLEWARE_CLASSES = (
        ...
        'django.middleware.transaction.TransactionMiddleware',
        'audible.AuditMiddleware',
        ... )

If you had a view which did various things with pizza orders:

    def pizzaria(request):
    	topping = models.Topping.objects.get
        i = models.PizzaOrder(customer_name='Yoko', cooked_by = models.Chef.objects.get(name='Lennon'))
        i.save()
        i.toppings.add(topping(name='cheese'), topping(name='more cheese'))
        i.toppings.clear()

        ii = models.PizzaOrder(customer_name = 'McCartney', cooked_by = models.Chef.objects.get(name='Lennon'))
        ii.save()
        ii.toppings.add(topping(name='cheese'), topping(name='vegetables'))
        ii.toppings.remove(topping(name='vegetables'))

        models.PizzaOrder.objects.update(cooked_by = models.Chef.objects.get(name='Starr'))
	...

After view execution, the `PizzaOrderAudit` table might resemble:

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