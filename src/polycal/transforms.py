import datetime
import itertools
import re
from collections import defaultdict
from datetime import timedelta
from typing import Generator, Optional, Type, Union

from polycal.types import AttendeeRSVP, Event


class Transform:
    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        yield from events


TRANSFORMERS: dict[str, Type[Transform]] = {}


def register(cls: Type[Transform]) -> None:
    type_ = cls.__name__
    assert type_ not in TRANSFORMERS, type_
    TRANSFORMERS[type_] = cls


@register
class ReplaceTitle(Transform):
    def __init__(self, pattern: str = r"^.*$", repl: str = "n/a", **kwargs):
        self.pattern = re.compile(pattern, **kwargs)
        self.repl = repl

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        for event in events:
            event.title = self.pattern.sub(self.repl, event.title or "")
            yield event


@register
class SetAttr(Transform):
    def __init__(self, **attrs):
        for attr_name in attrs:
            assert attr_name in Event.__fields__
        self.override = attrs

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        for event in events:
            for attr_name, value in self.override.items():
                setattr(event, attr_name, value)
            yield event


@register
class SkipByAttr(Transform):
    def __init__(self, **skip_by):
        self.skip_by = skip_by

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        for event in events:
            if not all(
                self.getattr_by_path(event, attr_name) == value
                for attr_name, value in self.skip_by.items()
            ):
                yield event

    @staticmethod
    def getattr_by_path(value, path: str):
        path_splitted = path.split(".")
        for attr in path_splitted:
            if isinstance(value, dict):
                value = value.get(attr)
            else:
                value = getattr(value, attr)
        return value


@register
class SkipByTitle(Transform):
    def __init__(self, titles: list[str]):
        self.patterns = [re.compile(title) for title in titles]

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        for event in events:
            if not any(pattern.match(event.title) for pattern in self.patterns):
                yield event


@register
class SkipByAttendee(Transform):
    def __init__(self, email: str, confirmed: bool = False):
        self.email = email
        self.confirmed = confirmed

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        for event in events:
            if not any(
                attendee.email == self.email
                and (not self.confirmed or attendee.status == AttendeeRSVP.accepted)
                for attendee in event.attendees
            ):
                yield event


@register
class SkipByDuration(Transform):
    def __init__(self, min_duration: str):
        self.min_duration = interpret_human_timedelta(min_duration)

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        for event in events:
            if event.duration > self.min_duration:
                yield event


@register
class Merge(Transform):
    """Merge events with the same title and overlapping time ranges."""

    def __init__(self, elipsis: Optional[str] = None):
        """
        :param elipsis: number of seconds
        """
        self.elipsis = interpret_human_timedelta(elipsis) if elipsis else timedelta()

    def process(
        self, events: Generator[Event, None, None]
    ) -> Generator[Event, None, None]:
        merged_events = defaultdict(list)

        def sort_dt_key(dt: Union[datetime.date, datetime.datetime]) -> datetime:
            return datetime.datetime.combine(dt, datetime.datetime.min.time())

        for event in sorted(events, key=lambda e: sort_dt_key(e.start)):
            similar_events = merged_events[event.title]
            for existing_event in similar_events:
                if isinstance(event.start, datetime.datetime) and isinstance(
                    existing_event.start, datetime.datetime
                ):
                    if (
                        existing_event.start <= event.start
                        and event.start - self.elipsis <= existing_event.end
                    ):
                        existing_event.end = max(existing_event.end, event.end)
                        break
            else:
                similar_events.append(event)
        yield from sorted(
            itertools.chain.from_iterable(
                similar_events for similar_events in merged_events.values()
            ),
            key=lambda e: sort_dt_key(e.start),
        )


def interpret_human_timedelta(timedelta_str: str) -> timedelta:
    """Convert string to timedelta

    >>> interpret_human_timedelta("5d")
    datetime.timedelta(days=5)
    >>> interpret_human_timedelta("1h")
    datetime.timedelta(seconds=3600)
    >>> interpret_human_timedelta("15m")
    datetime.timedelta(seconds=900)

    """
    match = re.match(
        r"(?P<num>\d+)(?P<spec>[dhms])?",
        timedelta_str,
    )
    if match:
        return timedelta(
            seconds=int(match.group("num"))
            * {
                "d": 24 * 60 * 60,
                "h": 60 * 60,
                "m": 60,
            }.get(match.group("spec"), 1)
        )
    else:
        raise ValueError(f"Invalid timedelta: {timedelta_str!r}")
