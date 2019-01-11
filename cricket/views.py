from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .forms import *
from .models import *
import datetime as dt
import ims.settings as settings
import random 
from beetle import models as bmodel
from threading import Lock
import cricket.sms_api as sa
from .resources import *
from beetle import views as bview
from tablib import Dataset
from threading import Timer
import cricket.config as ccfg
from ims.imslog import logger
import pprint as p_print


pp = p_print.PrettyPrinter(indent = 2,width = 50,depth = None)
# Create your views here.
user_otp = {}
visitor_otp = {}

class UserType(Enum):
  PARTICIPANT = 0
  VISITOR = 1

class AuthState(Enum):

  init = 0
  awaiting_otp = 1
  awaiting_approval = 2
  approved = 3

def render_status(request,status):
  status_string =\
  {
      tStatus.SUCCESS:tStatus.SUCCESS.name+'Operation Successful',
      tStatus.INVALID_USER:
        tStatus.INVALID_USER.name+'Invalid Registration Number',
      tStatus.TOKEN_EXHAUSTED:
        tStatus.TOKEN_EXHAUSTED.name+'Please contact admin',
      tStatus.INVALID_OTP:
        tStatus.INVALID_OTP.name+'Please try again',
      tStatus.INVALID_PARAMETER:
        tStatus.INVALID_PARAMETER.name+\
            'Session timeout. Please try after sometime',
      tStatus.UNKNOWN_ERROR:
        tStatus.UNKNOWN_ERROR.name+'Operation Failed',
      tStatus.TOKEN_REISSUED:
        tStatus.TOKEN_REISSUED.name+'Existing token not expired',
        }
  return render(request,'cricket/status.html',
          {'baseurl': settings.SITE_URL,'remove_header': True,
            'status_str':status_string[status]})

class tokenEntryView(LoginRequiredMixin,View):

  def post(self,request):
    
    user = request.user.username
    html_file = None
    html_var = None
    token_form = gForm(request.POST) 
    
    if token_form.is_valid(): 
      ttype = token_form.cleaned_data['token_type']
      print('ttype',ttype,UserType.PARTICIPANT.value)

      if int(ttype) == UserType.PARTICIPANT.value: #participant
        html_file = 'cricket/itoken_view.html'
        html_var = {'tlist': ParticipantToken.objects.all(),
          'baseurl': settings.SITE_URL}
        ttoken = ParticipantToken()
        logger.info('Created token %s type by %s',
            UserType.PARTICIPANT.name,user)

      else:  #visitor
        html_file = 'cricket/vtoken_view.html'
        html_var = {'tlist': VisitorToken.objects.all(),
          'baseurl': settings.SITE_URL}
        ttoken = VisitorToken()
        logger.info('Created token %s type by %s',
            UserType.VISITOR.name,user)
      
      ttoken.userid = token_form.cleaned_data['userid']
      ttoken.password = token_form.cleaned_data['password']
      ttoken.token_state = ccfg.TokenState.NEW.value
      ttoken.validity = token_form.cleaned_data['validity']
      ttoken.created_on = dt.date.today()
      ttoken.issued_on = dt.date.today()
      ttoken.save()

    elif 'myfile' in request.FILES.keys():

      logger.info('Uploading token for %s by %s of validity %s',
          request.POST['token_for'],user,request.POST['validity'])

      if request.POST['token_for']=="VISITOR":
        html_file = 'cricket/vtoken_view.html'
        html_var = {'tlist': VisitorToken.objects.all(),
          'baseurl': settings.SITE_URL}
        t_resource = VisitorTokenResource(
            request.POST['validity'])

      else:
        html_file = 'cricket/itoken_view.html'
        html_var = {'tlist': ParticipantToken.objects.all(),
          'baseurl': settings.SITE_URL}
        t_resource = ParticipantTokenResource(
            request.POST['validity'])
    
      new_tokens = request.FILES['myfile']
      dataset = bview.get_dataset(new_tokens)
      result = t_resource.import_data(dataset, dry_run=True)  

      if not result.has_errors():
        t_resource.import_data(dataset, dry_run=False)  
        logger.info('token upload successful %s ',user)

      else:
        logger.warning('token upload unsuccessful %s ',user)

    return render(request,html_file,html_var)
 
  def get(self,request):

    user = request.user.username
    form = gForm()
    logger.info('%s accessing token entry view',user)
    return render(request, 
        'cricket/token_entry.html', 
        {'form': form,'baseurl': settings.SITE_URL})


class iTokenTableView(LoginRequiredMixin,View):

  def get(self,request):

    user = request.user.username
    logger.info('%s accessing participant token table view',user)
    return render(request, 
        'cricket/itoken_view.html',
        {'tlist': ParticipantToken.objects.all(),
          'baseurl': settings.SITE_URL})
    
        
class vTokenTableView(LoginRequiredMixin,View):

  def get(self,request):

    user = request.user.username
    logger.info('%s accessing visitor token table view',user)
    return render(request, 
        'cricket/vtoken_view.html',
        {'tlist': VisitorToken.objects.all(),
          'baseurl': settings.SITE_URL})


def session_expired(session_id,otp_dict):

  if session_id in otp_dict.keys():
    logger.info('Deleting otp dict entry %s for %s',
        pp.pformat(otp_dict[session_id]),session_id)
    otp_dict[session_id]['thandle'].cancel()
    del otp_dict[session_id]['thandle']
    otp_dict.pop(session_id,None)
    logger.debug(
        'In session expired : otp dict entries after pop \n%s\n',
        pp.pformat(otp_dict))

  else:
    logger.warning('Session id %d not found in otp_dict %s',
        session_id,otp_dict)


class OtpHandler(View):

  utype = None
  var = 0
  ss_key = None
  vinfo = None
  fsm = {} 


  def __init__(self,utype,var,ss_key, vinfo = None):

    self.fsm = {
      AuthState.awaiting_otp : self.handle_awaiting_otp,
      AuthState.awaiting_approval : self.handle_awaiting_approval
      }
    self.utype = utype
    self.var = var
    self.ss_key = ss_key
    self.vinfo = vinfo
    logger.info('Otphandler created for %s, user %s var %d ',
        ss_key, utype.name, var)

  def send_otp(self,otp):

    mobile_number = 0

    if self.utype == UserType.PARTICIPANT:
      mobile_number = \
        bmodel.get_participant_info(self.var).mobile_number

    else:
      mobile_number = self.var
    
    if mobile_number:
      sa.send_otp(mobile_number,otp)
      print("OTP %d sent to %d"%(otp,mobile_number))

    else:
      print("Send OTP failed")
      logger.error('Mobile number not found for sending OTP %d user  %s var %d session_key %d',
          otp, self.utype.name, self.var, self.ss_key)

  def get_otp(self,otp_dict,request):

    if self.ss_key in otp_dict.keys():
      logger.info('Session id %s count %d utype %s',self.ss_key,
          otp_dict[self.ss_key]['count'],self.utype.name)
      if otp_dict[self.ss_key]['count'] >= bmodel.otp_max_retries():
        return False

    else:
      otp_dict[self.ss_key] = {
          'otp':random.randint(1000,9999),
          'var':self.var,
          'utype':self.utype,
          'count':0,
          'vinfo':self.vinfo,
          'thandle' : Timer(bmodel.session_timeout(),
            session_expired,[self.ss_key,otp_dict]),
          'state' : AuthState.awaiting_otp,
          }
      request.session.set_expiry(bmodel.session_timeout())
      otp_dict[self.ss_key]['thandle'].start()
      logger.info(
          'Generated otp %d for new session %s for utype %s',
          otp_dict[self.ss_key]['otp'],self.ss_key,self.utype.name)
      self.send_otp(otp_dict[self.ss_key]['otp'])

    otp_dict[self.ss_key]['count'] += 1
    return True

  def get(self,request):

    otp_dict = None

    if self.utype == UserType.PARTICIPANT:
      otp_dict = user_otp

    else:
      otp_dict = visitor_otp

    logger.debug(
      'In otp handler : get otp_dict entries before get_otp \n%s\n',
      pp.pformat(otp_dict))

    if self.get_otp(otp_dict,request):
      form = OtpForm()
      logger.info(
          'user %s attemptting to access otp page session id %s',
          self.utype.name, self.ss_key)
      logger.debug(
        'In otp handler : get otp_dict entries after get_otp \n%s\n',
          pp.pformat(otp_dict))
      return render(request,'cricket/get_otp.html',
          {'form' : form, 'count': otp_dict[self.ss_key]['count'],
            'baseurl': settings.SITE_URL,'remove_header': True,})

    else:
      logger.info('Calling session expired function')
      session_expired(self.ss_key,otp_dict)
      return HttpResponse(
          "You exceeded number of tries. Please try after sometime") 
  
  def is_otp_valid(self,request):

    oform = OtpForm(request.POST)
    uotp = None
    otp = None

    if oform.is_valid():
      uotp = oform.cleaned_data['otp']

    if self.utype == UserType.PARTICIPANT:
      otp_dict = user_otp

    else:
      otp_dict = visitor_otp

    otp = otp_dict[self.ss_key]['otp']
    logger.debug(
        'session id %s utype %s provided otp %d sent otp %d',
        self.ss_key, self.utype.name, uotp, otp)

    if uotp and otp and uotp==otp:
      return True

    else:
      return False

  def handle_participant(self, request):

    status = tStatus.UNKNOWN_ERROR
    token = None

    if self.is_otp_valid(request):
      logger.info('Recieved valid otp session id %s utype %s ',
        self.ss_key, self.utype)

      status,token = issue_new_itoken(self.var)
      logger.info('Calling session expired function')
      session_expired(self.ss_key,user_otp)

    else:
      logger.warning('Recieved Invalid otp session id %s utype %s ',
        self.ss_key, self.utype)
      status = tStatus.INVALID_OTP

    if status == tStatus.SUCCESS:
      return render(request,
        'cricket/token_assigned.html',{'uid': token.userid,
        'pwd': token.password,'baseurl': settings.SITE_URL,
        'remove_header': True,'status': 'NEW'})

    elif status == tStatus.TOKEN_REISSUED:
      logger.debug('Rendering same token to %d',self.var)
      return render(request,
        'cricket/token_assigned.html',{'uid': token.userid,
        'pwd': token.password,'baseurl': settings.SITE_URL,
        'remove_header': True,'status': 'OLD'})

    elif status == tStatus.INVALID_OTP:
      return self.get(request)

    else:
      logger.error(
          'Error in Otp handler session_id %s utype %s status %s',
          self.ss_key , self.utype.name, status.name)
      return render_status(request,status)
      #return HttpResponse(status.name)

  def handle_awaiting_approval(self,request):
    return None
  

  def handle_awaiting_otp(self,request):

    status = tStatus.UNKNOWN_ERROR
    token = None

    if self.is_otp_valid(request):
      logger.info('Recieved valid otp session id %s utype %s ',
        self.ss_key, self.utype)

      visitor_otp[self.ss_key]['state'] = \
        AuthState.awaiting_approval
      status = tStatus.SUCCESS

    else:
      logger.warning('Recieved Invalid otp session id %s utype %s ',
        self.ss_key, self.utype)
      status = tStatus.INVALID_OTP

    if status == tStatus.SUCCESS:
      return render(request,
        'cricket/awaiting_approval.html',
        {'baseurl': settings.SITE_URL,'remove_header': True,})

    elif status == tStatus.INVALID_OTP:
      return self.get(request)

    else:
      logger.error(
          'Error in Otp handler session_id %s utype %s status %s',
          self.ss_key , self.utype.name, status.name)
      return render_status(request,status)
      #return HttpResponse(status.name)


  def handle_visitor(self, request):

    status = tStatus.UNKNOWN_ERROR
    token = None
    
    otp_dict = visitor_otp

    if otp_dict[self.ss_key]['state'] in self.fsm.keys():
      return self.fsm[otp_dict[self.ss_key]['state']](request)

    else:
      logger.critical('Invalid state for session %s visitor %s',
          self.ss_key,otp_dict[self.ss_key])


  def post(self,request):

    if self.utype == UserType.PARTICIPANT:
      return self.handle_participant(request)

    else:
      return self.handle_visitor(request)


class approveView(View,LoginRequiredMixin):

  def get(self,request):
    vlist = []
    for sess,visitor in visitor_otp.items():
      print('visitor state',visitor['state'])
      if visitor['state'] == AuthState.awaiting_approval:
        vlist.append((
          sess,
          visitor['vinfo']['timestamp'],
          visitor['vinfo']['name'],
          visitor['vinfo']['mobile_number'],
          visitor['vinfo']['email_address'],
          visitor['vinfo']['refered_by']
          ))

    return render(request,
      'cricket/approve_view.html',{'vlist': vlist,
      'baseurl': settings.SITE_URL,})

  def post(self,request,session_id):
    
    visitor = None
    status = tStatus.UNKNOWN_ERROR

    if session_id and session_id in visitor_otp.keys():
      visitor = visitor_otp[session_id]
      visitor['state'] = AuthState.approved
      
    if not visitor:

      logger.warning('Invalid session id %s received for approval',
        session_id)
      status = tStatus.INVALID_PARAMETER

    else:

      vinfo = visitor['vinfo']
      logger.info(
          'Recieved approval request for session id %s name %s',
          session_id,vinfo['name'])
      status,token = issue_new_vtoken(vinfo['name'],
            vinfo['email_address'],vinfo['mobile_number'],
            vinfo['refered_by'])

      logger.info('Calling session expired function')
      session_expired(session_id,visitor_otp)


    if status == tStatus.SUCCESS:
      logger.info('Issued new token to visitor %s : %d',
          vinfo['name'],vinfo['mobile_number'])
      return self.get(request)

    elif status == tStatus.TOKEN_REISSUED:
      logger.warning('Re-Issued valid token to visitor %s : %d',
          vinfo['name'],vinfo['mobile_number'])
      return self.get(request)

    else:
      logger.error(
          'Error in AuthState session_id %s status %s',
          session_id, status.name)
      return render_status(request,status)
      #return HttpResponse(status.name)


class getTokenBaseView(View):

  lock = Lock()

  def get(self,request,otp_dict,form,u_url):

    if not request.session.session_key:
      request.session.save()
      logger.info('storing session key %s',
          request.session.session_key)

    logger.info('get token page %s accessed session id %s',
        u_url, request.session.session_key)
    return render(request,u_url,
      {'form' : form,
       'baseurl': settings.SITE_URL,'remove_header': True,})

  def post(self,request,otp_dict,u_type):

    ss = request.session

    if ss.session_key in otp_dict.keys():
      logger.debug('Entering critical section session id %s',
          ss.session_key)
      if bmodel.is_thread_safe_mode():
        self.lock.acquire()

      otph = OtpHandler(u_type,
          otp_dict[ss.session_key]['var'],ss.session_key)
      response = otph.post(request)
      if bmodel.is_thread_safe_mode():
        self.lock.release()

      logger.debug('Exiting critical section session id %s',
          ss.session_key)
      return response

    if u_type == UserType.VISITOR:
      form = visitorTokenForm(request.POST)

    else:
      form = participantTokenForm(request.POST)

    status = tStatus.UNKNOWN_ERROR
    mobile_number = 0
    reg_num = 0 
    i_key = 0
    vinfo = None

    if form.is_valid():
      logger.info('valid form received from user %s session id %s',
          u_type.name, ss.session_key)

      if u_type == UserType.VISITOR:
        vinfo = {}
        mobile_number = form.cleaned_data['mobile_number']
        i_key = mobile_number
        vinfo['name'] = form.cleaned_data['visitor_name']
        vinfo['email_address'] = form.cleaned_data['email_address']
        vinfo['mobile_number'] = form.cleaned_data['mobile_number']
        vinfo['refered_by'] = form.cleaned_data['refered_by']
        vinfo['timestamp'] = dt.datetime.now()
        logger.debug('Visitor info %s session %s',
              vinfo, ss.session_key)
        status = tStatus.SUCCESS

      else:
        reg_num = form.cleaned_data['registration_number']
        i_key = reg_num
        participant_info = bmodel.get_participant_info(reg_num)

        if participant_info:
          logger.debug('Participant info %s session %s',
              participant_info, ss.session_key)
          status = tStatus.SUCCESS

        else:
          logger.warning(
              'Invalid registration number %d from session %s ',
              reg_num, ss.session_key)
          status = tStatus.INVALID_USER

    else:
      logger.warning(
          'Invalid form received from user %s session id %s',
          u_type.name, ss.session_key)
      status = tStatus.INVALID_PARAMETER
    
    if status == tStatus.SUCCESS:
      logger.debug('Entering critical section session id %s',
          ss.session_key)
      if bmodel.is_thread_safe_mode():
        self.lock.acquire()

      otph = OtpHandler(u_type,i_key,
          ss.session_key,vinfo)
      response = otph.get(request)
      if bmodel.is_thread_safe_mode():
        self.lock.release()

      logger.debug('Exiting critical section session id %s',
          ss.session_key)
      return response

    return render_status(request,status)
    #return HttpResponse(status.name) 

class getTokenView(getTokenBaseView):

  def get(self,request):

    i_form = participantTokenForm()
    return super(getTokenView,self).get(request,
        user_otp,i_form,
        'cricket/get_token.html')

  def post(self,request):

    return super(getTokenView,self).post(request,
        user_otp,UserType.PARTICIPANT)


class getTokenVisitorView(getTokenBaseView):

  def get(self,request):

    v_form = visitorTokenForm()
    return super(getTokenVisitorView,self).get(request,
        visitor_otp,v_form,
        'cricket/get_token_visitor.html')

  def post(self,request):

    return super(getTokenVisitorView,self).post(request,
        visitor_otp,UserType.VISITOR)



