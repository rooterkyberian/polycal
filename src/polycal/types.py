import datetime
from typing import List, Optional, Union

import pydantic


class Event(pydantic.BaseModel):
    iCalUID: pydantic.constr(max_length=255)
    sequence: int = 0
    source_ids: List[str]
    start: Union[datetime.datetime, datetime.date]
    end: Union[datetime.datetime, datetime.date]
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    deleted: bool = False
    busy: bool = True

    @property
    def duration(self) -> datetime.timedelta:
        return self.end - self.start
