from enum import Enum

class VentureState(Enum):
  INACTIVE = 0
  ACTIVE = 1
  ALUMINI = 2
  SUSPENDED = 3
  
class  VenturePrograms(Enum):
  UNDEFINED = 0 
  LAUNCHPAD = 1
  LAUNCHPAD_INCUBATES = 2
  IICDC = 3
  SOCIAL = 4
  WSP = 5
    
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


