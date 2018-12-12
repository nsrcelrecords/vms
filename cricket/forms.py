from django import forms
from django.forms import ModelForm
from cricket.models import *

class tUpdateForm(ModelForm): 
  class Meta:
    model = WifiToken
    fields = "__all__"
    '''
    widgets = {
            'start_date': forms.DateInput(attrs={
              'class':'SelectDateWidget', 'size' : 10 }),
            'end_date': forms.DateInput(attrs={
              'class':'SelectDateWidget'}),
     }
    '''
    exclude = ('created_on','issued_on','token_state')

class gForm(tUpdateForm):
  TOKEN_TYPE = (
      (0,"Participant token"),
      (1,"Visitor token"),
      )
        
  token_type = forms.ChoiceField(choices = TOKEN_TYPE)

class participantTokenForm(forms.Form): 
  
  registration_number = forms.IntegerField()  
    
class visitorTokenForm(forms.Form): 
   
  visitor_name = forms.CharField()
  email_address = forms.EmailField()
  mobile_number = forms.IntegerField()
  refered_by = forms.CharField()

  
class OtpForm(forms.Form): 
  
  otp = forms.IntegerField()
