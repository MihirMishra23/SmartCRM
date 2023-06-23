from dataclasses import dataclass
from typing import List

from utils_email import Email

@dataclass(init=False)
class Contact:
  name: str
  email: str
  phone: str
  contact: List[Email]