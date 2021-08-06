import base64
import datetime
import hashlib
import itertools
import json
import time
from typing import Generator, Optional, Union

import pydantic

from polycal.services.gcal import GoogleCalendarEvent, GoogleCalendarService
from polycal.transforms import TRANSFORMERS
from polycal.types import Event


class BaseModel(pydantic.BaseModel):
    class Config:
        extra = "forbid"


class TransformModel(BaseModel):
    type: str
    kwargs: Optional[dict[str, Union[bool, int, str]]] = None


class SourceModel(BaseModel):
    id: str
    name: Optional[str]
    transforms: list[TransformModel] = ()


class TargetModel(BaseModel):
    id: str
    name: str


class ConfigModel(BaseModel):
    sources: list[SourceModel]
    target: TargetModel
    user_agent: str = "polycal"


class CalendarProcessor:
    def __init__(self, config: ConfigModel, gcal_service: GoogleCalendarService):
        self.config = config
        self.gcal_service = gcal_service

    def process(self, start: datetime.datetime, end: datetime.datetime):
        events = itertools.chain.from_iterable(
            self.process_source(source, start=start, end=end)
            for source in self.config.sources
        )
        self.sync_to_target(events, start, end)

    def process_source(
        self, source: SourceModel, start: datetime.datetime, end: datetime.datetime
    ) -> Generator[GoogleCalendarEvent, None, None]:
        transforms = [
            TRANSFORMERS[transform_config.type](**(transform_config.kwargs or {}))
            for transform_config in source.transforms
        ]
        events = self.gcal_service.list_events(
            calendar_id=source.id, start=start, end=end
        )
        for transform in transforms:
            events = transform.process(events)
        yield from events

    def sync_to_target(
        self,
        events: Generator[Event, None, None],
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> None:
        events_to_remove = {
            event.iCalUID: event
            for event in self.gcal_service.list_events(
                calendar_id=self.config.target.id, start=start, end=end
            )
        }
        updated_events = []
        for event in events:
            old_event = events_to_remove.pop(event.iCalUID, None)
            if not old_event or pydantic_hash(event) != pydantic_hash(old_event):
                event.sequence = int(time.time())
                updated_events.append(event)

        for removed_event in events_to_remove.values():
            removed_event.deleted = True
        self.gcal_service.sync_events(
            self.config.target.id,
            itertools.chain(updated_events, events_to_remove.values()),
        )


def pydantic_hash(obj: pydantic.BaseModel) -> str:
    return base64.b85encode(
        hashlib.blake2s(
            json.dumps(
                obj.json(exclude={"sequence", "source_ids"}), sort_keys=True
            ).encode("utf-8")
        ).digest()
    ).decode()
