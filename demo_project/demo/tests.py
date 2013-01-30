"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test.utils import override_settings
import models
from datetime import datetime
import auditable
from datetime import datetime
from django.utils.timezone import now
import django.db.models

class Auditable(TestCase):
    
    def setUp(self):
        self.longMessage = True
        #add chefs and toppings
        for name in ['Starr', 'Lennon']:
            models.Chef(name=name).save()
        for name in ['cheese', 'more cheese', 'meat', 'fruit', 'vegetables']:
            models.Topping(name=name).save()


    def list_audits(self, order_by='id'):
        audits = []
        for audit in models.PizzaOrderAudit.objects.order_by(order_by):
            audits.append([audit.id, 
                           int(audit.audit_instance), 
                           audit.audit_instance_row_operation, 
                           audit.customer_name, 
                           audit.cooked_by,
                           audit.pizza_audit_record_examined,
                           audit.toppings
                           ])
        return audits

    def list_larder_audits(self, order_by='id'):
        audits = []
        for audit in models.LarderAudit.objects.order_by(order_by):
            audits.append([audit.id, 
                           int(audit.audit_instance), 
                           audit.audit_instance_row_operation, 
                           audit.ingredient, 
                           audit.quantity
                           ])
        return audits

    def check_ascending_datetimes(self, before, after):
        previous_datetime = before
        for audit in models.PizzaOrderAudit.objects.order_by('id'):
            min_datetime = min(audit.audit_row_updated_at, audit.audit_row_inserted_at)
            max_datetime = max(audit.audit_row_updated_at, audit.audit_row_inserted_at)
            self.assertLess(previous_datetime, min_datetime)
            self.assertLessEqual(audit.audit_row_inserted_at, audit.audit_row_updated_at) #??
            previous_datetime = max_datetime
        self.assertLess(previous_datetime, after)


    def print_datetimes(self, before, after):
        print 'before', before
        for audit in models.PizzaOrderAudit.objects.order_by('id'):
            print 'id', audit.id, 'inserted', audit.audit_row_inserted_at, 'updated', audit.audit_row_updated_at
        print 'after', after


    def test_immediate_single_instance(self):
        before = now()

        #audit record 1
        instance = models.PizzaOrder(customer_name='Yoko')
        instance.save()
        #audit record 2
        instance.cooked_by = models.Chef.objects.get(name='Starr')
        instance.save()
        #audit record 3
        instance.toppings.add(models.Topping.objects.get(name='cheese'),
                              models.Topping.objects.get(name='more cheese'))
        #audit record 4
        instance.toppings.remove(models.Topping.objects.get(name='more cheese'))
        #audit record 5
        instance.toppings.clear()

        #edit a field on the last of the audit records
        a_record = models.PizzaOrderAudit.objects.get(pk=5)
        a_record.pizza_audit_record_examined=True
        a_record.save()

        #audit record 6
        instance.delete()

        audits = self.list_audits()

        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [3, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                     [4, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese']"], 
                     [5, 1, u'update', u'Yoko', u'1: Starr', True, u'[]'], 
                     [6, 1, u'delete', u'Yoko', u'1: Starr', False, u'[]']]

        self.assertEqual(audits, expected, 'audit records must match expected values')

        self.check_ascending_datetimes(before, now())


    def test_immediate_multiple_instances(self):
        before = now()

        #audit record 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()

        #audit record 2
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()

        #audit record 3
        ii = models.PizzaOrder()
        ii.customer_name = 'McCartney'
        ii.cooked_by = models.Chef.objects.get(name='Lennon')
        ii.save()

        #audit record 4
        ii.toppings.add(models.Topping.objects.get(name='cheese'),
                        models.Topping.objects.get(name='vegetables'))

        #audit record 5
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))

        #audit record 6
        ii.toppings.remove(models.Topping.objects.get(name='vegetables'))

        #audit record 7
        i.toppings.clear()

        #audit record 8
        ii.toppings.add(models.Topping.objects.get(name='more cheese'))

        #audit record 9
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))

        #audit record 10
        i.toppings.clear()

        #audit record 11
        ii.customer_name = 'Harrison'
        ii.save()

        #audit record 12
        i.delete()

        #audit record 13
        ii.cooked_by = models.Chef.objects.get(name='Starr')
        ii.save()

        audits = self.list_audits()

        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [3, 2, u'insert', u'McCartney', u'2: Lennon', False, u'[]'], 
                     [4, 2, u'update', u'McCartney', u'2: Lennon', False, u"[u'cheese', u'vegetables']"], 
                     [5, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                     [6, 2, u'update', u'McCartney', u'2: Lennon', False, u"[u'cheese']"], 
                     [7, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [8, 2, u'update', u'McCartney', u'2: Lennon', False, u"[u'cheese', u'more cheese']"], 
                     [9, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [10, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [11, 2, u'update', u'Harrison', u'2: Lennon', False, u"[u'cheese', u'more cheese']"], 
                     [12, 1, u'delete', u'Yoko', u'1: Starr', False, u'[]'], 
                     [13, 2, u'update', u'Harrison', u'1: Starr', False, u"[u'cheese', u'more cheese']"]]

        self.assertEqual(audits, expected, 'audit records must match expected values')

        self.check_ascending_datetimes(before, now())


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_single_instance(self):
        before = now()

        #ensure audit records are empty before we begin.
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')
        
        #audit record 1
        instance = models.PizzaOrder(customer_name='Yoko')
        instance.save()
        instance.cooked_by = models.Chef.objects.get(name='Starr')
        instance.save()
        instance.toppings.add(models.Topping.objects.get(name='cheese'),
                              models.Topping.objects.get(name='more cheese'))
        auditable.checkpoint()

        #audit record 2
        instance.toppings.remove(models.Topping.objects.get(name='more cheese'))
        auditable.checkpoint()

        #audit record 3
        instance.toppings.clear()
        auditable.checkpoint()

        #edit a field on the last of the audit records
        a_record = models.PizzaOrderAudit.objects.get(pk=3)
        a_record.pizza_audit_record_examined=True
        a_record.save()

        #audit record 4
        instance.delete()
        auditable.checkpoint()

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                     [2, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese']"], 
                     [3, 1, u'update', u'Yoko', u'1: Starr', True, u'[]'], 
                     [4, 1, u'delete', u'Yoko', u'1: Starr', False, u'[]']]
        self.assertEqual(audits, expected, 'audit records must match expected values')
        self.check_ascending_datetimes(before, now())


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_insert_delete(self):
        """
        if an instance is inserted and deleted in the same checkpoint then make only a single audit row containing values of the object at time of the delete
        but the operation should be 'insert_delete'
        """
        before = now()

        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        #audit record 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        i.toppings.clear()
        i.toppings.add(models.Topping.objects.get(name='cheese'))
        i.delete()

        auditable.checkpoint()

        audits = self.list_audits()
        expected = [[1, 1, u'insert_delete', u'Yoko', u'1: Starr', False, u"[u'cheese']"]]
        self.assertEqual(audits, expected, 'audit records must match expected values')


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_insert(self):
        """
        if an instance is inserted, but then later updated, then we want a single audit row which looks like a single insert
        """

        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        #audit record 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        i.cooked_by = models.Chef.objects.get(name='Lennon')
        i.toppings.clear()
        i.toppings.add(models.Topping.objects.get(name='cheese'))
        i.save()
        auditable.checkpoint()

        audits = self.list_audits()
        expected = [[1, 1, u'insert', u'Yoko', u'2: Lennon', False, u"[u'cheese']"]]
        self.assertEqual(audits, expected, 'audit records must match expected values')


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_update(self):
        """
        if an instance is updated, then later updated again, then we want a single audit row which looks like a single update
        """

        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        #audit record 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        auditable.checkpoint()
        
        #audit record 2
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        i.cooked_by = models.Chef.objects.get(name='Lennon')
        i.toppings.clear()
        i.toppings.add(models.Topping.objects.get(name='cheese'))
        i.save()
        auditable.checkpoint()

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 1, u'update', u'Yoko', u'2: Lennon', False, u"[u'cheese']"] ]
        self.assertEqual(audits, expected, 'audit records must match expected values')


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_delete(self):
        """
        if an instance is deleted...
        """

        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        #audit record 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        auditable.checkpoint()
        
        #audit record 2
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        i.cooked_by = models.Chef.objects.get(name='Lennon')
        i.toppings.clear()
        i.toppings.add(models.Topping.objects.get(name='cheese'))
        i.save()
        i.delete()
        auditable.checkpoint()

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 1, u'delete', u'Yoko', u'2: Lennon', False, u"[u'cheese']"] ]
        self.assertEqual(audits, expected, 'audit records must match expected values')


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_m2m(self):
        """
        if m2m is changed, then we want a single audit row which looks like a single update
        """

        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        #audit record 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()
        auditable.checkpoint()
        
        #audit record 2
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        auditable.checkpoint()

        #audit record 3
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        auditable.checkpoint()

        #audit record 4
        i.toppings.clear()
        auditable.checkpoint()

        #audit record 5
        i.toppings.add(models.Topping.objects.get(name='cheese'))
        auditable.checkpoint()


        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', u'1: Starr', False, u'[]'], 
                     [2, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                     [3, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese']"], 
                     [4, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [5, 1, u'update', u'Yoko', u'1: Starr', False, u"[u'cheese']"] ]
        self.assertEqual(audits, expected, 'audit records must match expected values')
    

    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_multiple_instances(self):
        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        #audit record 1
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
        ii.toppings.remove(models.Topping.objects.get(name='vegetables'))
        i.toppings.clear()
        ii.toppings.add(models.Topping.objects.get(name='more cheese'))
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        i.toppings.clear()
        ii.customer_name = 'Harrison'
        ii.save()
        ii.cooked_by = models.Chef.objects.get(name='Starr')
        ii.save()
        i.delete()
        auditable.checkpoint()
        
        audits = self.list_audits()
        expected = [ [1, 1, u'insert_delete', u'Yoko', u'1: Starr', False, u'[]'], 
                     [2, 2, u'insert', u'Harrison', u'1: Starr', False, u"[u'cheese', u'more cheese']"] ]
        self.assertEqual(audits, expected, 'audit records must match expected values')

        # inserted_at timestamp should follow the ids
        audits = self.list_audits(order_by='audit_row_inserted_at')
        self.assertEqual(audits, expected, 'audit records must match expected values')
        
        # updated_at timestamp should give opposite ordering, as instance i was updated last
        audits = self.list_audits(order_by='audit_row_updated_at')
        expected = [ [2, 2, u'insert', u'Harrison', u'1: Starr', False, u"[u'cheese', u'more cheese']"],
                     [1, 1, u'insert_delete', u'Yoko', u'1: Starr', False, u'[]'] ]
        self.assertEqual(audits, expected, 'audit records must match expected values')

    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_audit_does_not_interfere_with_methods(self):
        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        i = models.PizzaOrder(customer_name='Yoko', cooked_by=models.Chef.objects.get(name='Starr'))
        i.save()
        auditable.checkpoint()
        self.assertEqual(i.calculate_cost(), 12.99)
        self.assertEqual(i.order_kind, 'web')


    def test_overload_model_to_audit_field(self):
        MetaClass = auditable.metaclass_factory(models.PizzaOrder)

        #it's not okay to overload reserved audit fields
        with self.assertRaises(auditable.AuditableException):
            BadModel = MetaClass.__new__(MetaClass, 
                                         'BadModel', 
                                         (models.BaseAudit,), 
                                         { 'audit_instance_row_operation': 'bad_field', 
                                           '__module__': self.__module__ } )
        with self.assertRaises(auditable.AuditableException):
            BadModel = MetaClass.__new__(MetaClass, 
                                         'BadModel', 
                                         (models.BaseAudit,), 
                                         { '_instances_for_audit': 'bad_field', 
                                           '__module__': self.__module__ } )
        with self.assertRaises(auditable.AuditableException):
            BadModel = MetaClass.__new__(MetaClass, 
                                         'BadModel', 
                                         (models.BaseAudit,), 
                                         { 'audit_instance': 'bad_field', 
                                           '__module__': self.__module__ } )

        #also not okay to redefine fields which are used on PizzaOrder
        with self.assertRaises(auditable.AuditableException):
            BadModel = MetaClass.__new__(MetaClass, 
                                         'BadModel', 
                                         (models.BaseAudit,), 
                                         { 'customer_name': 'bad_field', 
                                           '__module__': self.__module__ } )
        with self.assertRaises(auditable.AuditableException):
            BadModel = MetaClass.__new__(MetaClass, 
                                         'BadModel', 
                                         (models.BaseAudit,), 
                                         { 'toppings': 'bad_field', 
                                           '__module__': self.__module__ } )

    def test_exclude_fields(self):
        fields = [ f.name for f in models.SlimlineAudit._meta.fields + models.SlimlineAudit._meta.many_to_many ]
        self.assertEqual(fields, ['id', 'audit_row_inserted_at', 'audit_row_updated_at', 'audit_instance_row_operation', 'audit_instance', 'customer_name'])
        

    def test_bulk_update_immediate(self):
        before = now()
        #audit 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()

        #audit 2
        ii = models.PizzaOrder(customer_name='George')
        ii.save()

        #audit 3
        iii = models.PizzaOrder(customer_name='Paul')
        iii.save()
        
        #audit 4,5,6
        rows = models.PizzaOrder.objects.all().update(cooked_by=models.Chef.objects.get(name='Starr'))

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 2, u'insert', u'George', None, False, u'[]'], 
                     [3, 3, u'insert', u'Paul', None, False, u'[]'], 
                     [4, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [5, 2, u'update', u'George', u'1: Starr', False, u'[]'], 
                     [6, 3, u'update', u'Paul', u'1: Starr', False, u'[]'] ]
        self.assertEqual(audits, expected)
        self.check_ascending_datetimes(before, now())


    def test_bulk_delete_immediate(self):
        before = now()
        #audit 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()

        #audit 2
        ii = models.PizzaOrder(customer_name='George')
        ii.save()

        #audit 3
        iii = models.PizzaOrder(customer_name='Paul')
        iii.save()
        
        #audit 4,5,6
        models.PizzaOrder.objects.all().delete()

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 2, u'insert', u'George', None, False, u'[]'], 
                     [3, 3, u'insert', u'Paul', None, False, u'[]'], 
                     [4, 1, u'delete', u'Yoko', None, False, u'[]'], 
                     [5, 2, u'delete', u'George', None, False, u'[]'], 
                     [6, 3, u'delete', u'Paul', None, False, u'[]'] ]
        self.assertEqual(audits, expected)
        self.check_ascending_datetimes(before, now())


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_bulk_update_checkpointed(self):
        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        before = now()
        #audit 1,2,3
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        ii = models.PizzaOrder(customer_name='George')
        ii.save()
        iii = models.PizzaOrder(customer_name='Paul')
        iii.save()
        auditable.checkpoint()

        #audit 4,5,6
        rows = models.PizzaOrder.objects.all().update(cooked_by=models.Chef.objects.get(name='Starr'))
        auditable.checkpoint()

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 2, u'insert', u'George', None, False, u'[]'], 
                     [3, 3, u'insert', u'Paul', None, False, u'[]'], 
                     [4, 1, u'update', u'Yoko', u'1: Starr', False, u'[]'], 
                     [5, 2, u'update', u'George', u'1: Starr', False, u'[]'], 
                     [6, 3, u'update', u'Paul', u'1: Starr', False, u'[]'] ]
        self.assertEqual(audits, expected)
        self.check_ascending_datetimes(before, now())


    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_bulk_delete_checkpointed(self):
        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        before = now()
        #audit 1,2,3
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        ii = models.PizzaOrder(customer_name='George')
        ii.save()
        iii = models.PizzaOrder(customer_name='Paul')
        iii.save()
        auditable.checkpoint()

        #audit 4,5,6
        models.PizzaOrder.objects.all().delete()
        auditable.checkpoint()

        audits = self.list_audits()
        expected = [ [1, 1, u'insert', u'Yoko', None, False, u'[]'], 
                     [2, 2, u'insert', u'George', None, False, u'[]'], 
                     [3, 3, u'insert', u'Paul', None, False, u'[]'], 
                     [4, 1, u'delete', u'Yoko', None, False, u'[]'], 
                     [5, 2, u'delete', u'George', None, False, u'[]'], 
                     [6, 3, u'delete', u'Paul', None, False, u'[]'] ]
        self.assertEqual(audits, expected)
        self.check_ascending_datetimes(before, now())


    def test_overload_manager(self):
        MetaClass = auditable.metaclass_factory(models.PizzaOrder)

        #it's not okay to have a manager on an object which isn't auditable
        with self.assertRaises(auditable.AuditableException):
            BadModel = MetaClass.__new__(MetaClass, 
                                         'BadModel', 
                                         (models.BaseAudit,), 
                                         { 'my_bad_manager': django.db.models.Manager(), 
                                           '__module__': self.__module__ } )
        

    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_checkpoint_multiple_models(self):
        #ensure audit records empty before we begin
        self.assertEqual([], models.PizzaOrderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')
        self.assertEqual([], models.LarderAudit._instances_for_audit, 'audit records must be empty; previous test has been untidy')        
        
        #checkpoint 1
        i = models.PizzaOrder(customer_name='Yoko')
        i.save()
        i.cooked_by = models.Chef.objects.get(name='Starr')
        i.save()
        j = models.Larder(ingredient='flour', quantity=12)
        j.save()
        ii = models.PizzaOrder()
        ii.customer_name = 'McCartney'
        ii.cooked_by = models.Chef.objects.get(name='Lennon')
        ii.save()
        ii.toppings.add(models.Topping.objects.get(name='cheese'),
                        models.Topping.objects.get(name='vegetables'))
        i.toppings.add(models.Topping.objects.get(name='cheese'),
                       models.Topping.objects.get(name='more cheese'))
        ii.toppings.remove(models.Topping.objects.get(name='vegetables'))
        jj = models.Larder(ingredient='yeast', quantity=1)
        jj.save()
        auditable.checkpoint()

        #checkpoint 2
        i.toppings.clear()
        ii.toppings.add(models.Topping.objects.get(name='more cheese'))
        i.toppings.remove(models.Topping.objects.get(name='more cheese'))
        i.toppings.clear()
        models.Larder.objects.all().update(quantity=0)
        ii.customer_name = 'Harrison'
        ii.save()
        ii.cooked_by = models.Chef.objects.get(name='Starr')
        ii.save()
        i.delete()
        auditable.checkpoint()
        
        audits = self.list_audits()        
        expected = [[1, 1, u'insert', u'Yoko', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                    [2, 2, u'insert', u'McCartney', u'2: Lennon', False, u"[u'cheese']"], 
                    [3, 2, u'update', u'Harrison', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                    [4, 1, u'delete', u'Yoko', u'1: Starr', False, u'[]']]
        self.assertEqual(audits, expected, 'audit records must match expected values')

        larder_audits = self.list_larder_audits()
        expected_larder = [[1, 1, u'insert', u'flour', u'12'], 
                           [2, 2, u'insert', u'yeast', u'1'], 
                           [3, 1, u'update', u'flour', u'0'], 
                           [4, 2, u'update', u'yeast', u'0']]
        self.assertEqual(larder_audits, expected_larder, 'audit records must match expected values')

        
    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_double_audit_models(self):
        """
        two audit models must be able to audit the same model correctly
        it's not that this is a super-useful feature, it's more that this is
        a common typo and the right semantics is important.
        """
        #ensure audit records empty before we begin
        self.assertEqual([], models.DoubleTestAuditOne._instances_for_audit, 'audit records must be empty; previous test has been untidy')
        self.assertEqual([], models.DoubleTestAuditTwo._instances_for_audit, 'audit records must be empty; previous test has been untidy')

        two = models.DoubleTest(number=2)
        two.save()
        four = models.DoubleTest(number=4) 
        four.save()
        six = models.DoubleTest(number=6) 
        six.save()
        auditable.checkpoint()
    
        qs1 = models.DoubleTestAuditOne.objects.all().order_by('id')
        qs2 = models.DoubleTestAuditTwo.objects.all().order_by('id')
        ls1 = [ i.number for i in qs1 ]
        ls2 = [ i.number for i in qs2 ]

        expected = [u'2', u'4', u'6']
        self.assertEqual(ls1, expected)
        self.assertEqual(ls2, expected)

    @override_settings(AUDITABLE_CHECKPOINTED=True)
    def test_middleware_checkpoints(self):
        """
        Tests that the middleware is correctly checkpointing requests
        """
        self.client.get('/one')
        self.client.get('/two')
        expected = [ [1, 1, u'insert', u'Yoko', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                     [2, 2, u'insert', u'McCartney', u'2: Lennon', False, u"[u'cheese', u'vegetables']"], 
                     [3, 2, u'update', u'Harrison', u'1: Starr', False, u"[u'cheese', u'more cheese']"], 
                     [4, 1, u'update', u'Yoko', u'1: Starr', False, u'[]']]
        self.assertEqual(self.list_audits(), expected)
        
