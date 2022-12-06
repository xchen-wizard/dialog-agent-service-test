from typing import NamedTuple, Optional
from enum import Enum


class FlowType(Enum):
    """
    predefined flow types
    """
    CAMPAIGN = 'campaign'
    WELCOME = 'welcome'
    CHECKOUT = 'checkout'


class TemplateMessage(NamedTuple):
    templateTypeId: str
    templateVariables: Optional[dict]


class DASResponse(NamedTuple):
    vendorId: int
    templateMessages: list[TemplateMessage]
    message: str = ''
    autoResponse: bool = True


