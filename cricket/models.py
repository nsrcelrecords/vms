from django.db import models
import datetime as dt
from beetle import models as bmodel
from enum import Enum
import beetle.config as bcfg
import cricket.config as ccfg
from ims.imslog import logger
import cricket.sms_api as sa

# Create your models here.

class tStatus(Enum):
  SUCCESS = 0
  INVALID_USER = 1
  TOKEN_EXHAUSTED = 2
  INVALID_OTP = 3
  INVALID_PARAMETER = 4
  UNKNOWN_ERROR = 5
  TOKEN_REISSUED = 6

class WifiToken(models.Model): 

  userid = models.CharField(max_length = 10,default='',)
  password = models.CharField(max_length = 10,default = '')
  validity = models.PositiveIntegerField(default = 0)

  TSTATE = bcfg.get_enum_choice(ccfg.TokenState)

  token_state = models.PositiveIntegerField(
    choices = TSTATE,default = 0,)
  created_on = models.DateField()
  issued_on = models.DateField()
  
  class Meta:
    abstract = True
  
  def get_token_state(self):
    for e in self.TSTATE:
      if self.token_state == e[0]:
        return e[1]
    return 'UNKNOWN TSTATE'
  
  def __str__(self):
    return self.userid

class ParticipantToken(WifiToken): 

  issued_to = models.PositiveIntegerField(default = 0)
  

class VisitorToken(WifiToken): 

  issued_to = models.CharField(max_length = 75,default = '')
  email_address = models.EmailField(
      max_length = 75, default = 'nobody@email.com' )
  mobile_number = models.PositiveIntegerField(default = 0)
  refered_by = models.CharField(max_length = 75,default = '')

def get_next_itoken():
  tlist = ParticipantToken.objects.filter(
      token_state = ccfg.TokenState.NEW.value)
  if tlist:
    return tlist[0]
  return None

def get_next_vtoken():
  tlist = VisitorToken.objects.filter(
      token_state = ccfg.TokenState.NEW.value)
  if tlist:
    return tlist[0]
  return None

def get_issued_valid_token_for_participant(registration_number):

  tdate = dt.date.today()
  issued_tokens = ParticipantToken.objects.filter(
      issued_to = registration_number)

  for entry in issued_tokens:
    tdelta = tdate - entry.issued_on

    if entry.token_state == ccfg.TokenState.ISSUED.value:
      if tdelta.days < entry.validity:
        return entry

      else:
        entry.token_state = ccfg.TokenState.EXPIRED.value
        entry.save()
        logger.warning(
            'Moving participant token %s to expired state %d',
            entry.userid,entry.registration_number)

  return None


def issue_new_itoken(registration_number):

  status = tStatus.UNKNOWN_ERROR
  participant_info = bmodel.get_participant_info(registration_number)
  itoken = None
  issued_token = None

  if participant_info:
    issued_token = get_issued_valid_token_for_participant(
      registration_number)
  
  else:
    status = tStatus.INVALID_USER
    logger.warning('Participant info not found for %d',
        registration_number)
    return status,None

  status_str = None

  if issued_token:
    itoken = issued_token
    status = tStatus.TOKEN_REISSUED
    status_str = 'OLD'

  else:
    itoken = get_next_itoken()

    if itoken:
      itoken.token_state = ccfg.TokenState.ISSUED.value
      itoken.issued_on = dt.date.today()
      itoken.issued_to = registration_number
      itoken.save()
      logger.info('%s token issued to %d',
          itoken.userid, registration_number)
      status = tStatus.SUCCESS
      status_str = 'NEW'

    else:
      logger.critical('Participant token exhausted %d',
          registration_number)
      status = tStatus.TOKEN_EXHAUSTED

  if itoken:
    sa.send_token(participant_info.mobile_number,
        status_str,itoken.userid,itoken.password)

  return status,itoken


def get_issued_valid_token_for_visitor(mobile_number):

  tdate = dt.date.today()
  issued_tokens = VisitorToken.objects.filter(
      mobile_number = mobile_number)
  for entry in issued_tokens:
    tdelta = tdate - entry.issued_on

    if entry.token_state == ccfg.TokenState.ISSUED.value:
      if tdelta.days < entry.validity:
        return entry

      else:
        entry.token_state = ccfg.TokenState.EXPIRED.value
        entry.save()
        logger.warning('Moving visitor token %s to expired state %s',
        vtoken.userid,vtoken.issued_to)


  return None


def issue_new_vtoken(name,email,mobile,refer):
  status = tStatus.UNKNOWN_ERROR
  vtoken = None
  issued_token = get_issued_valid_token_for_visitor(mobile)
  status_str = None

  if issued_token:
    vtoken = issued_token
    logger.debug('Valid issued token found for visitor %s : %d',
        vtoken.issued_to,vtoken.mobile_number)
    status = tStatus.TOKEN_REISSUED
    status_str = 'OLD'

  else:
    vtoken = get_next_vtoken()
    if vtoken:
      vtoken.token_state = ccfg.TokenState.ISSUED.value
      vtoken.issued_on = dt.date.today()
      vtoken.issued_to = name
      vtoken.email_address = email
      vtoken.mobile_number = mobile
      vtoken.refered_by = refer
      vtoken.save()
      logger.info('%s token issued to %d',vtoken.userid, mobile)
      status = tStatus.SUCCESS
      status_str = 'NEW'

    else:
      status = tStatus.TOKEN_EXHAUSTED
      logger.critical('Visitor token exhausted %d',mobile)

  if vtoken:
    sa.send_token(mobile,status_str,vtoken.userid,vtoken.password)
  return status,vtoken

