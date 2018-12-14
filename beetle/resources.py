from import_export import resources
from .models import * 
import datetime as dt
import beetle.config as bcfg
from ims.imslog import logger
import cricket.sms_api as sa

class VentureResource(resources.ModelResource):

  class Meta:
    model = Venture
    import_id_fields = ('registration_number',)
    exclude = ('venture_state',
        'id','userid','employee_id_counter')

    widgets = {
        'start_date': {'format': '%Y/%m/%d'},
        'end_date': {'format': '%Y/%m/%d'},
                }
  userid = ''

  def __init__(self,userid):
    self.userid = userid
    logger.debug('Venture resource created %s userid',userid)
    super(VentureResource,self).__init__()
  
  def import_row(self, row, instance_loader,
      using_transactions=True, dry_run=False, **kwargs):

    row['last_modified'] = row['start_date']
    instance = self.get_or_init_instance(instance_loader,row)
    row['program'] = instance[0].get_program_number(
        row['program'].strip().upper())

    return super(VentureResource,self).import_row(
        row,instance_loader,using_transactions,dry_run,**kwargs)

  def dehydrate_program(self, venture):
    return venture.get_program()

  def dehydrate_venture_state(self, venture):
    return venture.get_venture_state()

  def after_save_instance(self,instance,using_transactions,dry_run):

    print('After Save called')
    if not dry_run:
      instance.update_registration_number()
      instance.last_modified = dt.date.today()
      instance.userid = self.userid
      instance.venture_state = bcfg.VentureState.ACTIVE.value
      instance.employee_id_counter = 0
      print('Saving entry now',instance.registration_number)
      instance.save()

    super(VentureResource,self).after_save_instance(instance,
          using_transactions,dry_run)


class ParticipantExportResource(resources.ModelResource):

  class Meta:
    model = Participant
    import_id_fields = ('registration_number',)
    exclude = ('id','userid','last_modified',)
  
  def dehydrate_designation(self, participant):
    return participant.get_designation()
  
  def dehydrate_company(self, participant):
    return participant.company.venture_name
  
  def dehydrate_participant_state(self, participant):
    return participant.get_state()


class ParticipantImportResource(resources.ModelResource):

  class Meta:
    model = Participant
    import_id_fields = ('registration_number',)
    exclude = ('id','participant_state','last_modified','userid',)
    widgets = {
        'start_date': {'format': '%m/%d/%Y'},
        'end_date': {'format': '%m/%d/%Y'},
                }
  userid = ''

  def __init__(self,userid):
      self.userid = userid
      logger.debug('Participant resource created %s userid',userid)
      super(ParticipantImportResource,self).__init__()
  
  def import_row(self, row, instance_loader, 
        using_transactions=True, dry_run=False, **kwargs):

      row['last_modified'] = row['start_date']
      vlist = row['company'] = Venture.objects.filter(
          venture_name__iexact = row['company'].strip())
      
      if vlist:
        row['company'] = vlist[0].id

      instance = self.get_or_init_instance(instance_loader,row)
      row['designation'] = instance[0].get_designation_number(
          row['designation'].strip().upper())
      
      return super(ParticipantImportResource,self).import_row(
          row,instance_loader,using_transactions,dry_run,**kwargs)

  def after_save_instance(self,instance,using_transactions,dry_run):

    if not dry_run:
      instance.update_registration_number()
      instance.last_modified = dt.date.today()
      instance.userid = self.userid
      instance.participant_state = bcfg.ParticipantState.ACTIVE.value
      instance.save()
      sa.send_registration_number(instance.mobile_number,
          instance.registration_number)

    super(ParticipantImportResource,self).after_save_instance(
        instance,using_transactions,dry_run)

