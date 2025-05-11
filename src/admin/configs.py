from pydantic import BaseModel
from typing import Dict, Optional

# Schema para receber as configurações do Admin
class ConfigPayload(BaseModel):
    layout: Optional[str]
    placeholder: Optional[str]
    blockPosition: Optional[str]
    colors: Dict[str, str]
    structure: Optional[list]
