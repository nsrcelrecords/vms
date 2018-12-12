from import_export import resources
from .models import *
import datetime as dt
from ims.imslog import logger

class WifiTokenResource(resources.ModelResource):

  validity = None

  def __init__(self,validity):
    self.validity = validity
    logger.debug('Wifitoken resource created for validity %d',
        validity)
    super(WifiTokenResource,self).__init__()

  def after_save_instance(self,instance,using_transactions,dry_run):

    if not dry_run:
      instance.validity = self.validity
      instance.token_state = 1
      instance.save()

    super(WifiTokenResource,self).after_save_instance(instance,
          using_transactions,dry_run)

  def import_row(self, row, instance_loader, 
        using_transactions=True, dry_run=False, **kwargs):
      row['created_on'] = dt.date.today()
      row['issued_on'] = dt.date.today()
      
      return super(WifiTokenResource,self).import_row(
          row,instance_loader,using_transactions,dry_run,**kwargs)


class VisitorTokenResource(WifiTokenResource):

  class Meta:
    model = VisitorToken


class ParticipantTokenResource(WifiTokenResource):

  class Meta:
    model = ParticipantToken

