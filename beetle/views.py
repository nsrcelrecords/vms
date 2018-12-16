from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .forms import *
from .models import *
import datetime as dt
import ims.settings as settings 
from .resources import *
from tablib import Dataset
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render
import beetle.config as bcfg
from ims.imslog import logger
import cricket.sms_api as sa

def get_dataset(ufile):
    #stream = ufile.read().decode('utf-8')
    stream = ufile.read().decode('ISO-8859-1')
    #print('stream',stream)
    lines = stream.split('\r\n')
    logger.info('%d lines found in imported file %s',
        len(lines),ufile)
    #print('lines',lines)
    hdr = None
    val = []
    for x in range(len(lines)):
      if x==0:
        hdr = lines[x].split(',')
      else:
        val.append(lines[x].split(','))
    #print('hdr',hdr)
    #val = val[:-1]
    #print('val',val)
    
    dataset = Dataset(headers=hdr)
    for i in range(len(val)):
      try:
        dataset.append(val[i])
      except:
        logger.warning('Ingnoring row %d due to errors',i+1)

    logger.debug('dataset.csv : %s',dataset.csv)
    return dataset


class baseView(LoginRequiredMixin,View):
  
  url_lookup = {
      'HOME': 'beetle/home.html',
      'VENTURE_VIEW': 'beetle/venture_view.html',
      'VENTURE_ENTRY': 'beetle/venture_entry.html',
      'VENTURE_DETAIL': 'beetle/detail.html',
      'VENTURE_MODIFY': 'beetle/venture_modify_entry.html',
      'PART_DETAIL': 'beetle/participant_detail.html',
      'PART_VIEW': 'beetle/participant_view.html',
      'PART_ENTRY': 'beetle/participant_entry.html',
      'PART_MODIFY': 'beetle/participant_modify_entry.html',
      'INVALID_PARAMS': 'beetle/invalid_params.html',
      'INVALID_REG': 'beetle/invalid_reg.html',
      }
  tparams = {}
  render_url = None

  def get(self,request):
    user = request.user.username
    self.tparams['baseurl']= settings.SITE_URL

    if not self.render_url:
      self.render_url = 'INTERNAL_ERROR'

    logger.info('%s accessing %s',user,self.render_url)
    logger.debug('template parameters %s',tuple(self.tparams))
    return render(request, self.url_lookup[self.render_url],
        self.tparams)

  def post(self,request):
    user = request.user.username
    self.tparams['baseurl']= settings.SITE_URL
    if not self.render_url:
      self.render_url = 'INTERNAL_ERROR'

    logger.info('%s posting %s',user,self.render_url)
    logger.debug('template parameters %s',tuple(self.tparams))
    return render(request, self.url_lookup[self.render_url],
        self.tparams)

  def get_elist_strings(self,result): 
    elist = result.row_errors()
    ulist = []
    for e in elist:
      for f in e[1]:
        #print("row %d error %s"%(e[0],f.error))
        ulist.append('Row# %d: %s'%(e[0],f.error))
    return ulist


class changePasswordView(LoginRequiredMixin,View):
  def post(self,request):
    userid = request.user.username
    logger.info('%s posting change password ',userid)
    form = PasswordChangeForm(request.user, request.POST)

    if form.is_valid():
      user = form.save()
      update_session_auth_hash(request, user)  # Important!
      logger.info('%s Password change successfully',userid)
      return render(request,
        'beetle/home.html',{'baseurl': settings.SITE_URL})
    else:
      logger.warning('%s Invalid form submitted ',userid)

  def get(self,request):
    form = PasswordChangeForm(request.user)
    user = request.user.username
    logger.info('%s attemptting to change password ',user)
    return render(request, 'beetle/change_password.html', {
        'form': form})

class homeView(baseView):
  def get(self,request):
    self.render_url = 'HOME'
    return super(homeView,self).get(request)
 

class ventureEntryView(baseView):

  def post(self,request):
    user = request.user.username
    venture_form = ventureForm(request.POST) 

    if venture_form.is_valid(): 

      venture = venture_form.save(commit=False)
      venture.update_registration_number()
      venture.userid = user
      venture.last_modified = dt.datetime.now()
      venture.venture_state = bcfg.VentureState.ACTIVE.value
      venture.venture_name = venture.venture_name.strip()
      venture.save()
      logger.info('%s Venture successfully created by %s',
          venture.venture_name,user)

      self.render_url = 'VENTURE_VIEW'
      self.tparams['vlist'] = Venture.objects.all()

    elif 'myfile' in request.FILES.keys():

      venture_resource = VentureResource(user)
      new_ventures = request.FILES['myfile']

      dataset = get_dataset(new_ventures)
      result = venture_resource.import_data(dataset, dry_run=True)  

      if not result.has_errors():
        self.render_url = 'VENTURE_VIEW'
        self.tparams['vlist'] = Venture.objects.all()
        logger.info(
          'Venture info file successfully uploaded by %s',
          user)
        venture_resource.import_data(dataset, dry_run=False)  

      else:
        self.render_url = 'VENTURE_ENTRY'
        self.tparams['form'] = ventureForm()
        self.tparams['ulist'] = self.get_elist_strings(result)
        logger.warning(
          'Error uploading venture import file by %s',user)

    else:
      self.render_url = 'VENTURE_ENTRY'
      self.tparams['form'] = ventureForm()
      self.tparams['mlist'] = venture_form._errors
      #print('form errors',venture_form._errors)
      logger.warning(
          'Invalid form updated by %s:%s',
         user,venture_form._errors)

    return super(ventureEntryView,self).post(request)

  
  def get(self,request):
    user = request.user.username
    form = ventureForm()
    self.tparams = {}

    self.render_url = 'VENTURE_ENTRY'
    self.tparams['form'] = form
    return super(ventureEntryView,self).get(request)

class ventureModifyView(baseView):
  def post(self,request,registration_number):

    user = request.user.username
    venture_form = ventureModifyForm(request.POST) 
    #print('venture_form',venture_form) 
    if venture_form.is_valid(): 
      
      vlist = Venture.objects.filter(
          registration_number = registration_number)
      venture = vlist[0]
      
      venture.userid = user
      venture.last_modified = dt.datetime.now()
      venture.venture_state = \
        venture_form.cleaned_data['venture_state']
      venture.venture_name = \
        venture_form.cleaned_data['venture_name']
      venture.end_date = \
        venture_form.cleaned_data['end_date']
      venture.save()

      logger.info('%s Venture successfully modified by %s',
          venture.venture_name,user)

      self.render_url = 'VENTURE_DETAIL'
      self.tparams['ven'] = venture
      self.tparams['elist'] = venture.participant_set.all()
      return super(ventureModifyView,self).post(
          request)

    else:
      logger.warning(
          'Venture modification form not valid %s',user)
      self.tparams['mlist'] = venture_form._errors
      return self.get(request,registration_number)


  def get(self,request,registration_number):

    user = request.user.username
    vlist = Venture.objects.filter(
        registration_number = registration_number)
    if vlist:
      venture = vlist[0]

      form = ventureModifyForm(instance = venture)

      self.render_url = 'VENTURE_MODIFY'
      self.tparams['form'] = form

    else:
      logger.warning('Attemptting to modify venture(%d) from %s',
          registration_number,user)
      self.render_url = 'INVALID_REG'

    return super(ventureModifyView,self).get(
          request)


class ventureDeleteView(baseView):
  def get(self,request,registration_number):
    user = request.user.username
    vlist = Venture.objects.filter(
      registration_number = registration_number)
    if vlist:
      logger.info('Deleting venture %s by %s',
          vlist[0].venture_name,user)
      vlist.delete()

    else:
      logger.warning('Attemptting to delete venture(%d) from %s',
          registration_number,user)
    
    self.render_url = 'VENTURE_VIEW'
    self.tparams['vlist'] = Venture.objects.all()
    return super(ventureDeleteView,self).get(
        request)


class ventureTableView(baseView):

  def get(self,request):
    user = request.user.username
    print(user,"logged in")

    self.render_url = 'VENTURE_VIEW'
    self.tparams['vlist'] = Venture.objects.all()
    return super(ventureTableView,self).get(
          request)
  
  def post(self,request):

    user = request.user.username
    venture_resource = VentureResource(user)
    dataset = venture_resource.export()
    response = HttpResponse(dataset.csv,
        content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="venture.csv"'
    return response


class ventureDetailView(baseView):

  def get(self,request,registration_number):
    user = request.user.username
    venlist = Venture.objects.filter(
      registration_number = registration_number)

    if not venlist:
      self.render_url = 'INVALID_REG'
      logger.warning('Attemptting to view invalid venture(%d) by %s',
          registration_number,user)
    else:
      self.render_url = 'VENTURE_DETAIL'
      ven = venlist[0] # only one expected
      self.tparams['ven'] = ven
      self.tparams['elist'] = ven.participant_set.all()

    return super(ventureDetailView,self).get(
          request)
  
  
class participantEntryView(baseView):

  def post(self,request):
    user = request.user.username
    participant_form = participantForm(request.POST) 
    
    if participant_form.is_valid(): 

      participant = participant_form.save(commit=False)
      participant.update_registration_number()
      participant.venture_state = bcfg.VentureState.ACTIVE.value
      participant.last_modified = dt.datetime.now()
      participant.userid = user
      participant.save()
      sa.send_registration_number(participant.mobile_number,
          participant.registration_number)
      logger.info('Participant %s created succeccfully by %s',
          participant,user)

      self.render_url = 'PART_DETAIL'
      self.tparams['emp'] = participant
      return super(participantEntryView,self).post(request)
      self.render_url = 'PART_VIEW'
      self.tparams['elist'] = Participant.objects.all()
    
    elif 'myfile' in request.FILES.keys():

      participant_resource = ParticipantImportResource(user)
      new_participants = request.FILES['myfile']

      dataset = get_dataset(new_participants)
      result = participant_resource.import_data(dataset, 
          dry_run=True)  

      if not result.has_errors():
        participant_resource.import_data(
          dataset, dry_run=False)  
        logger.info(
         'Participant import file uploaded succeccfully by %s',
          user)
        self.render_url = 'PART_VIEW'
        self.tparams['elist'] = Participant.objects.all()

      else:
        logger.warning('Participant import file not uploaded')
        self.render_url = 'PART_ENTRY'
        self.tparams['ulist'] = self.get_elist_strings(result)
        self.tparams['form'] = participantForm()

    else:
      logger.warning(
          'invalid form submitted by %s: %s',
          user,participant_form._errors)    
      self.render_url = 'PART_ENTRY'
      self.tparams['form'] = participantForm()
      self.tparams['mlist'] = participant_form._errors 

    return super(participantEntryView,self).post(request)

  def get(self,request):
    user = request.user.username
    form = participantForm()
    self.tparams = {}


    self.render_url = 'PART_ENTRY'
    self.tparams['form'] = form
    return super(participantEntryView,self).get(request)


class participantDetailView(baseView):
  def get(self,request,registration_number):
    user = request.user.username
    ilist = Participant.objects.filter(
      registration_number = registration_number)

    if not ilist:
      logger.warning('Invalid registration number %d by %s',
          registration_number,user)
      self.render_url = 'INVALID_REG'

    else:
      participant = ilist[0] # only one expected
      self.render_url = 'PART_DETAIL'
      self.tparams['emp'] = participant
    return super(participantDetailView,self).get(request)


class participantModifyView(baseView):

  def post(self,request,registration_number):
    user = request.user.username

    participant_form = participantModifyForm(request.POST) 
    
    if participant_form.is_valid(): 
      
      ilist = Participant.objects.filter(
          registration_number = registration_number)
      participant = ilist[0]
      
      participant.userid = user
      participant.last_modified = dt.datetime.now()
      participant.first_name = \
        participant_form.cleaned_data['first_name']
      participant.last_name = \
        participant_form.cleaned_data['last_name']
      participant.designation = \
        participant_form.cleaned_data['designation']
      participant.email_address = \
        participant_form.cleaned_data['email_address']
      participant.mobile_number = \
        participant_form.cleaned_data['mobile_number']
      participant.start_date = \
        participant_form.cleaned_data['start_date']
      participant.end_date = \
        participant_form.cleaned_data['end_date']
      participant.participant_state = \
        participant_form.cleaned_data['participant_state']
      participant.save()
      logger.info('Participant %s successfully modified by %s',
          participant,user)

      self.render_url = 'PART_DETAIL'
      self.tparams['emp'] = participant
      return super(participantModifyView,self).post(request)

    else:
      logger.warning('Invalid Form submitted by %s',user)
      self.tparams['mlist'] = participant_form._errors
      return self.get(request,registration_number)

  def get(self,request,registration_number):

    user = request.user.username
    ilist = Participant.objects.filter(
        registration_number = registration_number)
    if ilist:
      participant = ilist[0]

      form = participantModifyForm(instance = participant)

      self.render_url = 'PART_MODIFY'
      self.tparams['form'] = form

    else:
      logger.warning(
          'Attempting to modify invalid participant(%d) by %s',
          registration_number,user)
      self.render_url = 'INVALID_REG'

    return super(participantModifyView,self).get(request)
 

class participantDeleteView(baseView):

  def get(self,request,registration_number):
    user = request.user.username
    plist = Participant.objects.filter(
      registration_number = registration_number)

    if plist:
      logger.info('Deleting participant %s by %s',
          plist[0],user)
      plist.delete() 

    else:
      logger.warning('Invliad Participant %d by %s',
          registration_number,user)

    self.render_url = 'PART_VIEW'
    self.tparams['elist'] = Participant.objects.all()
    return super(participantDeleteView,self).get(request)


class participantTableView(baseView):

  def get(self,request):
    user = request.user.username

    self.render_url = 'PART_VIEW'
    self.tparams['elist'] = Participant.objects.all()
    return super(participantTableView,self).get(request)
  
  def post(self,request):

    participant_resource = ParticipantExportResource()
    dataset = participant_resource.export()

    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="participant.csv"'

    return response


