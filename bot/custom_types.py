from dataclasses import dataclass
from typing import TypeAlias, Literal


status_type: TypeAlias = Literal["new", "in_work", "completed", "rejected"]


@dataclass
class UserDict:
    user_uid: int
    first_name: str
    last_name: str
    department: str = ""
    is_priority: int = 0


@dataclass
class TicketDict:
    user_uid: int
    title: str
    description: str
    status: status_type = "new"
