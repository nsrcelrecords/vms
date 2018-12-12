from enum import Enum

  
class TokenState(Enum):
  INVALID = 0
  NEW = 1
  ISSUED = 2
  EXPIRED = 3

