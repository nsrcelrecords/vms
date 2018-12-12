import urllib.request
import urllib.parse
import beetle.models as bm
from ims.imslog import logger
 
API_KEY = 'qfereyn98Rc-lNjUf8NiHuoSdtmoD9qkZ1wFLDDuJI'

REG_NUM_TPLT = "Registration Number : %d\n\nDear Participant, \nPlease note this registration number and use the same for any transaction with NSRCEL.\n-Team NSRCEL"

OTP_TPLT = "OTP for NSRCEL services %d . Do not disclose to anyone."

TOKEN_TPLT = "Dear User, \nHere is your %s Wi-Fi credentials.\nUser-Id: %s\nPassword: %s\nPlease connect to SSID:IIMB-Guest and provide the same to access internet."

def sendSMS(numbers, message, apikey=API_KEY,
    sender='NSRCEL'):
    data =  urllib.parse.urlencode({'apikey': apikey, 'numbers': numbers,
        'message' : message, 'sender': sender})
    data = data.encode('utf-8')
    request = urllib.request.Request("https://api.textlocal.in/send/?")
    f = urllib.request.urlopen(request, data)
    fr = f.read()
    logger.debug('Output of send SMS %s for mobile_number %d message %s',fr,numbers[0],message)
    return(fr)

def send_registration_number(mobile_number,registration_number):
  
  s = REG_NUM_TPLT%(registration_number)
  
  if bm.send_reg_num_via_sms():
    logger.info('Sending reg_num %s to %d',s,mobile_number)
    return sendSMS([mobile_number],s,)

  else:
    logger.info('Not sending reg_num %s to %d',s,mobile_number)
    return True

def send_otp(mobile_number,otp):
  
  s = OTP_TPLT%(otp)
  logger.info('Sending otp %s to %d',s,mobile_number)
  return sendSMS([mobile_number],s,)

def send_token(mobile_number,status,userid,password):
  
  s = TOKEN_TPLT%(status,userid,password)
  
  if bm.send_token_via_sms():
    logger.info('Sending token %s to %d',s,mobile_number)
    return sendSMS([mobile_number],s,)

  else:
    logger.info('Not sending token %s to %d',s,mobile_number)
    return True

