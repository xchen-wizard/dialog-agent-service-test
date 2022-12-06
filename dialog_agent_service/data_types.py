from __future__ import annotations

from enum import Enum
from typing import NamedTuple
from typing import Optional


class FlowType(Enum):
    """
    predefined flow types
    """
    CAMPAIGN = 'campaign'
    WELCOME = 'welcome'
    CHECKOUT = 'checkout'


class TemplateMessage(NamedTuple):
    templateTypeId: str
    templateVariables: dict | None = {}


class DASResponse(NamedTuple):
    vendorId: int
    templateMessages: list[dict] = []
    message: str = ''
    autoResponse: bool = True
