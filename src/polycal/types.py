import datetime
import enum
from typing import Optional, Union

import pydantic


@enum.unique
class AttendeeRSVP(str, enum.Enum):
    needs_action = "needsAction"
    declined = "declined"
    tentative = "tentative"
    accepted = "accepted"


class Attendee(pydantic.BaseModel):
    email: str
    status: AttendeeRSVP = AttendeeRSVP.needs_action


class Event(pydantic.BaseModel):
    iCalUID: pydantic.constr(max_length=255)
    sequence: int = 0
    source_ids: list[str]
    start: Union[datetime.datetime, datetime.date]
    end: Union[datetime.datetime, datetime.date]
    type: str = "default"
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    deleted: bool = False
    busy: bool = True
    attendees: list[Attendee] = []

    @property
    def duration(self) -> datetime.timedelta:
        return self.end - self.start
