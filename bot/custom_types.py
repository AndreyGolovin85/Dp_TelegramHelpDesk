from enum import Enum
from typing import Literal, TypeAlias

from pydantic import BaseModel

status_type: TypeAlias = Literal["new", "in_work", "completed", "rejected"]


class StatusEnum(Enum):
    new = "new"
    in_work = "in_work"
    completed = "completed"
    rejected = "rejected"


class UserDict(BaseModel):
    user_uid: int
    first_name: str
    last_name: str
    department: str = ""
    is_priority: int = 0


class TicketDict(BaseModel):
    user_uid: int
    title: str
    description: str
    status: status_type = "new"

class Ticket_ID_Dict(TicketDict):
    id: int
