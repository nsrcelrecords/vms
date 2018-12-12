#from django import forms
from django.forms import ModelForm
from beetle.models import *
from django import forms

'''
class BnrForm(forms.Form): 
  banner_code = forms.IntegerField(
    widget=forms.Select(choices=get_banner_choice()) )
'''
class ventureForm(ModelForm): 
  class Meta:
    model = Venture
    fields = ['program',
              'venture_name',
              'start_date',
              'end_date',
              ]
    #"__all__"

    widgets = {
            'start_date': forms.DateInput(attrs={
              'class':'SelectDateWidget', 'size' : 10 }),
            'end_date': forms.DateInput(attrs={
              'class':'SelectDateWidget'}),
     }

    def __init__(self, *args, **kwargs):
      print("Venture form init called")

class ventureModifyForm(ModelForm): 
  class Meta:
    model = Venture
    fields = [
              'venture_name',
              'venture_state',
              'end_date',
              ]

    def __init__(self, *args, **kwargs):
      print("Venture form init called")
      super(ventureModifyForm, self).__init__(self)

class participantForm(ModelForm):
  class Meta:
    model = Participant
    fields = "__all__"
    exclude = ('registration_number','userid','last_modified','state')

    def __init__(self, *args, **kwargs):
      print("Participant form init called")
 

class participantModifyForm(ModelForm):
  class Meta:
    model = Participant
    fields = "__all__"
    exclude = ('registration_number','userid','last_modified',
        'company')

    def __init__(self, *args, **kwargs):
      print("Participant form init called")
   
