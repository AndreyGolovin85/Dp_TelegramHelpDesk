from dataclasses import dataclass


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
    status: str = "new"
