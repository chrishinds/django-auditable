# Create your views here.
import models
from django.http import HttpResponse


def test_view_one(request):
    i = models.PizzaOrder(customer_name='Yoko')
    i.save()
    i.cooked_by = models.Chef.objects.get(name='Starr')
    i.save()
    ii = models.PizzaOrder()
    ii.customer_name = 'McCartney'
    ii.cooked_by = models.Chef.objects.get(name='Lennon')
    ii.save()
    ii.toppings.add(models.Topping.objects.get(name='cheese'),
                    models.Topping.objects.get(name='vegetables'))
    i.toppings.add(models.Topping.objects.get(name='cheese'),
                   models.Topping.objects.get(name='more cheese'))
    return HttpResponse('one')


def test_view_two(request):
    i = models.PizzaOrder.objects.get(pk=1)
    ii = models.PizzaOrder.objects.get(pk=2)
    ii.toppings.remove(models.Topping.objects.get(name='vegetables'))
    i.toppings.clear()
    ii.toppings.add(models.Topping.objects.get(name='more cheese'))
    ii.customer_name = 'Harrison'
    ii.save()
    models.PizzaOrder.objects.update(cooked_by = models.Chef.objects.get(name='Starr'))
    return HttpResponse('two')

