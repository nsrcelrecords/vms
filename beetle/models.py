from django.db import models
import datetime as dt
from enum import Enum
import beetle.config as bcfg
from ims.imslog import logger
# Create your models here.

class ImsConfiguration(models.Model):

  session_timeout = models.PositiveIntegerField(default = 300)
  otp_max_retries = models.PositiveIntegerField(default = 3)
  send_reg_num_via_sms = models.BooleanField(default = True)
  send_token_via_sms = models.BooleanField(default = True)
  thread_safe_mode = models.BooleanField(default = False)

  def __str__(Self):
    return 'Configuration Parameters'


def otp_max_retries():
  cplist = ImsConfiguration.objects.all()

  if not cplist or len(cplist) > 1:
    logger.critical('Error in configuration parameter %s',cplist)

  cp = cplist[0]
  return cp.otp_max_retries


def session_timeout():
  cplist = ImsConfiguration.objects.all()
  if not cplist or len(cplist) > 1:
    logger.critical('Error in configuration parameter %s',cplist)

  cp = cplist[0]
  return cp.session_timeout

def send_reg_num_via_sms():
  cplist = ImsConfiguration.objects.all()
  if not cplist or len(cplist) > 1:
    logger.critical('Error in configuration parameter %s',cplist)

  cp = cplist[0]
  return cp.send_reg_num_via_sms

def send_token_via_sms():
  cplist = ImsConfiguration.objects.all()
  if not cplist or len(cplist) > 1:
    logger.critical('Error in configuration parameter %s',cplist)

  cp = cplist[0]
  return cp.send_token_via_sms

def is_thread_safe_mode():
  cplist = ImsConfiguration.objects.all()
  if not cplist or len(cplist) > 1:
    logger.critical('Error in configuration parameter %s',cplist)

  cp = cplist[0]
  return cp.thread_safe_mode


class VentureId(models.Model):
  year = models.PositiveIntegerField(default = 0, unique = True)
  counter = models.PositiveIntegerField(default = 0) 

def get_next_venture_id(year):
  vlist = VentureId.objects.filter(year = year)

  if not vlist:
    logger.debug('Creating new venture id for year %d',year)
    vid = VentureId()
    vid.year = year
    vid.counter = 1

  else:
    vid = vlist[0]
    vid.counter += 1
    logger.debug('Increasing venture id %d for year %d',
        vid.counter,year)

  vid.save()  
  return vid.counter

class Venture(models.Model): 

  registration_number = models.PositiveIntegerField(default = 0, 
      unique = True)
   
  PROGRAMS = bcfg.get_enum_choice(bcfg.VenturePrograms)

  program = models.PositiveIntegerField(
  choices = PROGRAMS,default = 0,)
  venture_name = models.CharField(max_length = 200)
  start_date = models.DateField()
  end_date = models.DateField()

  V_STATES = bcfg.get_enum_choice(bcfg.VentureState)

  venture_state = models.PositiveIntegerField(
    choices = V_STATES,default = 0,)
  
  userid = models.CharField(max_length = 30)
  last_modified = models.DateTimeField()
  employee_id_counter = models.PositiveIntegerField(default = 0)

  def __str__ (self):
    return self.venture_name

  def get_venture_state(self):
    for e in self.V_STATES:
      if self.venture_state == e[0]:
        return e[1]
    return 'UNKNOWN STATE'

  def get_program(self):
    for e in self.PROGRAMS:
      if self.program == e[0]:
        return e[1]
    return 'UNKNOWN PROGRAM'
  
  def get_program_number(self,pgm_str):
    for e in self.PROGRAMS:
      if pgm_str == e[1]:
        return e[0]
    return 0
  
  def update_registration_number(self):

    vid = get_next_venture_id(self.start_date.year)
    new_registration_number = str(self.start_date.year)+str(
        int(self.start_date.month/3)+1)+str(self.program)+"%04d"%vid
    self.registration_number = int(new_registration_number)
    logger.info('%d regnum assign to %s',
        self.registration_number,self.venture_name)

  def get_number_of_employees(self):
    return len(self.participant_set.all())

class Participant(models.Model):

  company = models.ForeignKey(
      Venture, on_delete=models.CASCADE, default = 0)  

  registration_number = models.PositiveIntegerField(default = 0)
  first_name = models.CharField(max_length=75,default = '')
  last_name = models.CharField(max_length=75,default = '')
  mobile_number = models.PositiveIntegerField()
  email_address = models.EmailField(max_length=200,)
  start_date = models.DateField()
  end_date = models.DateField()

  DESIGNATIONS = bcfg.get_enum_choice(bcfg.ParticipantDesignation)
  
  designation = models.PositiveIntegerField(
    choices = DESIGNATIONS,default = 0,)
   
  P_STATE = bcfg.get_enum_choice(bcfg.ParticipantState)   

  participant_state = models.PositiveIntegerField(
    choices = P_STATE,default = 1,)
    
  #userid = models.CharField(max_length = 30)
  #last_modified = models.DateTimeField()
  
  def __str__ (self):
    return self.first_name + ' ' + self.last_name

  def update_registration_number(self):
    self.company.employee_id_counter += 1
    id = str(self.company.registration_number) +\
    "%02d"%self.company.employee_id_counter
    self.registration_number = int(id)
    self.company.save()
    logger.info(
        '%d regnum assign to %s company %s employee id counter %d',
        self.registration_number, self.first_name, 
        self.company.venture_name, self.company.employee_id_counter )

  def get_designation(self):
    for e in self.DESIGNATIONS:
      if self.designation == e[0]:
        return e[1]
    return 'UNKNOWN DESIGNATION'
  
  def get_state(self):
    for e in self.P_STATE:
      if self.participant_state == e[0]:
        return e[1]
    return 'UNKNOWN STATE'
  
  def get_designation_number(self,d_str):
    for e in self.DESIGNATIONS:
      if d_str == e[1]:
        return e[0]
    return 0
 

def get_participant_info(reg_num):

  ilist = Participant.objects.filter(registration_number = reg_num)
  if ilist and ilist[0].company.venture_state == \
      bcfg.VentureState.ACTIVE.value:
        
    if ilist[0].participant_state == \
        bcfg.ParticipantState.ACTIVE.value:

      if ilist[0].end_date < dt.date.today():
        ilist[0].participant_state = \
            bcfg.ParticipantState.INACTIVE.value
        ilist[0].save()
        logger.warning('Moving Participant %s to Inactive state',
            ilist[0])
        
      else:
        logger.debug('%s returned for %d',ilist[0],reg_num)
        return ilist[0]

  logger.warning('No records found for %d',reg_num)
  return None

