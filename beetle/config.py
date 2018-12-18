from enum import Enum

class VentureState(Enum):
  INACTIVE = 0
  ACTIVE = 1
  ALUMINI = 2
  SUSPENDED = 3
  
#New programs to be added only in the last.
#Donot alter the order.
#Donot remove any program even if the program is ended
class  VenturePrograms(Enum):
  UNDEFINED = 0 
  LAUNCHPAD = 1
  LAUNCHPAD_INCUBATES = 2
  IICDC = 3
  Social_MSDF = 4
  Social_Mphasis = 5
  Social_Ford = 6
  WSP_1 = 7
  WSP_2 = 8
  WOMEN_10K = 9

class  ParticipantDesignation(Enum):
  UNKNOWN = 0
  FOUNDER = 1 
  CO_FOUNDER = 2 
  EMPLOYEE = 3 
  INTERN = 4
  OTHER = 5
    
class ParticipantState(Enum):
  INACTIVE = 0 
  ACTIVE = 1
 


def get_enum_choice(e_obj):
  choice_set = []
  for s in e_obj:
    choice_set.append((s.value,s.name))    
  return choice_set 


