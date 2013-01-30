from django.db import models
from django.conf import settings

from models import Manager as AuditableManager, bulk_delete, bulk_update


class AuditableException(Exception): pass

def _do_audit(AuditModel, instance, operation):
    audit = AuditModel(audit_instance = unicode(instance.pk),
                       audit_instance_row_operation = operation)
                    
    def audit_field_fn(value):
        return None if value is None else unicode(value)

    #copy ordinary fields into audit
    for field in instance.__class__._meta.fields:
        if field.name != 'id':
            value = audit_field_fn(getattr(instance, field.name)) 
            setattr(audit, field.name, value)

            #copy the (current) value of m2m fields, 
            #be careful to attach this to post_ m2m signals
            for m2m_field in instance.__class__._meta.many_to_many:
                m2m_models = getattr(instance, m2m_field.name).all()
                m2m_value = unicode([ unicode(model.pk) for model in m2m_models ])
                setattr(audit, m2m_field.name, m2m_value)
    return audit



def metaclass_factory(model_to_audit, exclude={}):
    #Must subclass models.base.ModelBase to be a metaclass for subclasses of models.Model
    class FactoryInnerMetaClass(models.base.ModelBase):
        ModelToAudit = model_to_audit
        exclude_fields = exclude

        def __new__(AuditMetaClass, name, bases, attrs):
            #same check as models.base.ModelBase but bail on irregularity
            parents = [ b for b in bases if isinstance(b, models.base.ModelBase) ]
            if not parents:
                raise AuditableException('Error during audit class construction '
                                              '"%s" does not subclass django.db.models.Model' 
                                              % name)

            #examine the fields, and check the AuditModel doesn't redefine anything it shouldn't
            forbidden_field_names = ['audit_instance_row_operation', 
                                     'audit_instance',
                                     '_instances_for_audit'] 
            forbidden_field_names.extend([ field.name for field in FactoryInnerMetaClass.ModelToAudit._meta.many_to_many ])
            forbidden_field_names.extend([ field.name for field in FactoryInnerMetaClass.ModelToAudit._meta.fields ])
            if any(( attr in attrs for attr in forbidden_field_names)):
                raise AuditableException("Audit Model's definition (%s) cannot overload any field in the model it is auditing"
                                         "or the reserved fields audit_instance_row_operation, audit_instance, or _instances_for_audit" % name)

            #examine fields to ensure any Manager is also an AuditableManager
            for attr_name in attrs:
                if isinstance(attrs[attr_name], models.Manager) and not isinstance(attrs[attr_name], AuditableManager):
                    raise AuditableException("Manager field '%s' of AuditableModel '%s' is not also an audible.models.Manager" % (attr_name, name))

            #the following fields are always added to audit models
            attrs['audit_instance_row_operation'] = models.CharField(max_length=16, blank=False, editable=False)
            #better not to have ForeignKey, we don't want a model delete to also remove audit rows
            attrs['audit_instance'] = models.TextField(blank=False, editable=False)
            attrs['_instances_for_audit'] = []

            #create attrs for all non m2m fields in ModelToAudit
            for field in FactoryInnerMetaClass.ModelToAudit._meta.fields:
                if field.name != 'id' and field.name not in FactoryInnerMetaClass.exclude_fields:
                    attrs[field.name] = models.TextField(blank=True, null=True, editable=False)

            #create attrs for all m2m fields in ModelToAudit
            for m2m in FactoryInnerMetaClass.ModelToAudit._meta.many_to_many:
                if m2m.name not in FactoryInnerMetaClass.exclude_fields:
                    attrs[m2m.name] = models.TextField(blank=True, null=True, editable=False)

            #create the model which would have resulted from ordinary 
            #subclassing of the AuditModel, but with additional attrs
            super_new = super(FactoryInnerMetaClass, AuditMetaClass).__new__
            AuditModel = super_new(AuditMetaClass, name, bases, attrs)

            #define the following signal functions as closures on AuditModel

            #immediate signal handler saves a fresh audit instance for every signal received
            def audit_handler(instance, operation):
                if getattr(settings, 'AUDITABLE_CHECKPOINTED', False):
                    #if we have a CHECKPOINTED setting, handle the audit as checkpointed
                    #ie record the instance, and do the audit later, on call to checkpoint()
                    if operation == 'delete':
                        #build an audit instance now, before the model is deleted, and pass this to checkpoint() to save
                        AuditModel._instances_for_audit.append((instance.pk, _do_audit(AuditModel, instance, operation), operation, None))
                    else:
                        #pass instance.pk and retrieve the model afresh on checkpoint()
                        AuditModel._instances_for_audit.append((instance.pk, None, operation, FactoryInnerMetaClass.ModelToAudit))
                else:
                    #not checkpointed setting, do this audit as an immediate 
                    audit = _do_audit(AuditModel, instance, operation)
                    audit.save()
            
            def insert_update_signal(sender, instance, created, **kwargs):
                audit_handler(instance, 'insert' if created else 'update')

            def delete_signal(sender, instance, **kwargs):
                audit_handler(instance, 'delete')

            def m2m_signal(sender, instance, action, pk_set, **kwargs):
                #must attach audit to post_ m2 signals, so that m2m values can be scraped from instance
                if action in ['post_clear', 'post_add', 'post_remove']: 
                    #audit record will have clearer semantics if all m2m signals get flattened into 'update'
                    audit_handler(instance, 'update')

            def bulk_update_signal(sender, instance, **kwargs):
                audit_handler(instance, 'update')

            def bulk_delete_signal(sender, instance, **kwargs):
                audit_handler(instance, 'delete')

            #connect the auditing functions to the classes
            SenderModel = FactoryInnerMetaClass.ModelToAudit
            models.signals.post_save.connect(insert_update_signal, 
                                             sender=SenderModel,
                                             weak=False, 
                                             dispatch_uid='post_save_%s.%s' % (AuditModel.__module__, AuditModel.__name__))
            models.signals.pre_delete.connect(delete_signal, 
                                              sender=SenderModel, 
                                              weak=False, 
                                              dispatch_uid='pre_delete_%s.%s'  % (AuditModel.__module__, AuditModel.__name__))

            m2m_fields = [ f.name for f in FactoryInnerMetaClass.ModelToAudit._meta.many_to_many ]
            for m2m_field_name in m2m_fields:
                models.signals.m2m_changed.connect(m2m_signal, 
                                                   sender=getattr(SenderModel, m2m_field_name).through, 
                                                   weak=False, 
                                                   dispatch_uid='m2m_changed_%s.%s.%s'  % (AuditModel.__module__, AuditModel.__name__, m2m_field_name))

            bulk_update.connect(bulk_update_signal,
                                sender=SenderModel,
                                weak=False,
                                dispatch_uid='bulk_update_%s.%s' % (AuditModel.__module__, AuditModel.__name__))
            bulk_delete.connect(bulk_delete_signal,
                                sender=SenderModel,
                                weak=False,
                                dispatch_uid='bulk_delete_%s.%s' % (AuditModel.__module__, AuditModel.__name__))

            return AuditModel

    return FactoryInnerMetaClass


def clear():
    for AuditModel in models.get_models():
        AuditModel._instances_for_audit = []        

            
def checkpoint():
    #find all registered AuditModels 
    for AuditModel in models.get_models():
        if hasattr(AuditModel, '_instances_for_audit'):
            #then AuditModel is really an audit model
            audit_list = getattr(AuditModel, '_instances_for_audit', [])
            _prune_delete_operations(audit_list)
            _prune_other_operations(audit_list)
            audit_instances_so_far = {}
            for instance_pk, audit_instance, operation, ModelToAudit in audit_list:
                if instance_pk in audit_instances_so_far:
                    #then we need to re-save the model so that auto_now fields make sense
                    audit_instance = audit_instances_so_far[instance_pk]
                else:
                    if isinstance(audit_instance, AuditModel) and operation in ['delete', 'insert_delete']:
                        #if we have been given a ready-made AuditModel, then it must be a delete operation (as fields would have gone by now)
                        pass
                    elif audit_instance is None and operation not in ['delete', 'insert_delete']:
                        #otherwise it's an insert/update/m2m and we should form an audit model from the current model
                        instance = ModelToAudit.objects.get(pk = instance_pk)
                        audit_instance = _do_audit(AuditModel, instance, operation)
                    else:
                        raise AuditableException('Badly formed audit records')
                    audit_instances_so_far[instance_pk] = audit_instance
                audit_instance.save()
            #clear list 
            AuditModel._instances_for_audit = []


def _prune_delete_operations(audit_list):
    indexes_to_delete = []
    for index in range(0, len(audit_list)):
        instance_pk, audit_instance, operation, ModelToAudit = audit_list[index]
        if operation=='delete':
            earlier_audits = audit_list[:index]
            later_audits = audit_list[index+1:] if index+1 < len(audit_list) else []
            earlier_pks = [ row[0] for row in earlier_audits ]
            later_pks = [ row[0] for row in later_audits ]
            if instance_pk in later_pks:
                raise AuditableException("Badly formed audit checkpoint: can't have later audit records for an instance (%s: %s) which has earlier been deleted" % 
                                         (instance_pk, ModelToAudit))
            for i, pk in enumerate(earlier_pks):
                if instance_pk == pk:
                    #if we have audit records for a record that we later delete, then we should prune these earlier records.
                    #unless they're inserts
                    if earlier_audits[i][2] == 'insert':
                        #if we're inserting and deleting within the same checkpoint, change the operation
                        audit_instance.audit_instance_row_operation = 'insert_delete'
                        audit_list[index] = (instance_pk, audit_instance, 'insert_delete', ModelToAudit)
                        #and modify the earlier insert operation, so that auto_now_add datestamps reflect the insert time
                        audit_list[i] = (instance_pk, audit_instance, 'insert_delete', ModelToAudit)
                    else:
                        indexes_to_delete.append(i)

    #indexes are in ascending order, so reverse list before deleting from original list
    indexes_to_delete.reverse()
    for index in indexes_to_delete:
        del audit_list[index]
        
def _prune_other_operations(audit_list):
    indexes_to_delete = []
    for index in range(0, len(audit_list)):
        instance_pk, audit_instance, operation, ModelToAudit = audit_list[index]
        if operation=='delete':
            #we have already dealt with these
            pass
        else:
            earlier_audits = audit_list[:index]
            later_audits = audit_list[index+1:] if index+1 < len(audit_list) else []
            earlier_pks = [ row[0] for row in earlier_audits ]
            later_pks = [ row[0] for row in later_audits ]
            #we are only intersted in the first and last records, middle records can be removed.
            if instance_pk in earlier_pks and instance_pk in later_pks:
                indexes_to_delete.append(index)
    #indexes are in ascending order, so reverse list before deleting from original list
    indexes_to_delete.reverse()
    for index in indexes_to_delete:
        del audit_list[index]


class Middleware(object):
    def process_request(self, request):
        if not getattr(settings, 'AUDITABLE_CHECKPOINTED', False):
            raise AuditableException('AUDITABLE_CHECKPOINTED must be set True in settings.py before auditable.Middleware can be used within this application')
        clear()

    def process_response(self, request, response):
        checkpoint()
        return response
