import datetime
import logging
import pathlib
from typing import Generator, Iterable, List, TypedDict, Union

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from polycal.types import Attendee, Event

LOG = logging.getLogger(__name__)

TOKEN_FILE = "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.acls.readonly",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.calendars.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def get_creds(path: pathlib.Path) -> Credentials:
    token_path = path / TOKEN_FILE
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                LOG.warning("Credentials couldn't be refreshed %r", e)
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(path / "client_secret.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with token_path.open("w") as token:
            token.write(creds.to_json())

    return creds


def iso_z(dt: datetime.datetime) -> str:
    assert not dt.tzinfo
    return dt.isoformat() + "Z"


def from_google_cal_date(dt: dict[str, str]) -> Union[datetime.datetime, datetime.date]:
    try:
        return datetime.datetime.fromisoformat(dt["dateTime"])
    except KeyError:
        return datetime.date.fromisoformat(dt["date"])


def to_google_cal_date(dt: Union[datetime.datetime, datetime.date]) -> dict[str, str]:
    return {
        ("dateTime" if isinstance(dt, datetime.datetime) else "date"): dt.isoformat()
    }


dt_str = str
d_str = str


class GooglePerson(TypedDict):
    id: str
    email: str
    displayName: str
    self: bool


class EventTime(TypedDict):
    date: d_str
    dateTime: dt_str
    timeZone: str


class ExtendedProperties(TypedDict):
    private: dict[str, str]
    shared: dict[str, str]


class GoogleAttendee(GooglePerson, total=False):
    organizer: bool
    resource: bool
    optional: bool
    responseStatus: str
    comment: str


class GoogleCalendarEvent(TypedDict, total=False):
    # https://developers.google.com/calendar/api/v3/reference/events#resource
    id: str
    created: dt_str
    updated: dt_str
    summary: str
    description: str
    location: str
    colorId: str
    creator: GooglePerson
    organizer: GooglePerson
    start: EventTime
    end: EventTime
    endTimeUnspecified: bool
    recurrence: List[str]
    recurringEventId: str
    originalStartTime: EventTime
    transparency: str
    visibility: str
    iCalUID: str
    sequence: int
    extendedProperties: ExtendedProperties
    anyoneCanAddSelf: bool
    guestsCanInviteOthers: bool
    guestsCanModify: bool
    guestsCanSeeOtherGuests: bool
    privateCopy: bool
    locked: bool
    eventType: str
    attendees: list[GoogleAttendee]


class GoogleCalendarService:
    def __init__(self, creds):
        self.service = build("calendar", "v3", credentials=creds)

    def yield_all(self, query):
        fetch_more = True
        page_token = None
        while fetch_more:
            result = query(page_token=page_token)
            yield from result["items"]
            page_token = result.get("nextPageToken")
            fetch_more = bool(page_token)

    def get_calendar_owner_emails(self, calendar_id: str) -> Generator[str, None, None]:
        if "@" in calendar_id and not calendar_id.endswith("calendar.google.com"):
            yield calendar_id
        return
        for acl in self.yield_all(
            lambda page_token: self.service.acl()
            .list(
                calendarId=calendar_id,
                pageToken=page_token,
            )
            .execute(),
        ):
            if acl["role"] == "owner":
                scope = acl["scope"]
                if scope["type"] == "user":
                    yield scope["value"]

    def list_events(
        self, calendar_id: str, start: datetime.datetime, end: datetime.datetime
    ) -> Generator[Event, None, None]:
        """
        List events which calendar owner is/was attending
        """

        emails = set(self.get_calendar_owner_emails(calendar_id))
        for google_event in self.yield_all(
            lambda page_token: self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=iso_z(start),
                timeMax=iso_z(end),
                maxResults=2500,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        ):
            google_event: GoogleCalendarEvent
            if any(
                attendee.get("email") in emails
                and attendee.get("responseStatus") == "declined"
                for attendee in google_event.get("attendees", [])
            ):
                continue

            yield self._gevent_to_event(google_event)

    def _gevent_to_event(self, google_event: GoogleCalendarEvent) -> Event:
        uid = google_event["iCalUID"]
        if not uid.endswith("@polycal"):
            uid = f"{google_event['id']}@polycal"
        return Event(
            src=google_event,
            source_ids=[google_event["id"]],
            iCalUID=uid,
            sequence=google_event.get("sequence", 0),
            start=from_google_cal_date(google_event["start"]),
            end=from_google_cal_date(google_event["end"]),
            type=google_event.get("eventType"),
            title=google_event.get("summary"),
            deleted=google_event.get("status") == "cancelled",
            location=google_event.get("location"),
            busy=google_event.get("transparency", "opaque") == "opaque",
            attendees=[
                Attendee(email=attendee["email"], status=attendee.get("responseStatus"))
                for attendee in google_event.get("attendees", [])
            ],
        )

    def _event_to_gevent(self, event: Event) -> GoogleCalendarEvent:
        return {
            "iCalUID": event.iCalUID,
            "sequence": event.sequence,
            "summary": event.title,
            "start": to_google_cal_date(event.start),
            "end": to_google_cal_date(event.end),
            "status": "cancelled" if event.deleted else "confirmed",
            "location": event.location,
            "transparency": "opaque" if event.busy else "transparent",
            "eventType": event.type,
        }

    def sync_events(self, calendar_id: str, sync_events: Iterable[Event]):
        sync_events = list(sync_events)
        batch = self.service.new_batch_http_request()

        def cb(request_id, response, exception):
            if exception is not None:
                raise exception

        updated = set()
        for event in sync_events:
            if event.deleted:
                for source_id in set(event.source_ids) - updated:
                    batch.add(
                        self.service.events().delete(
                            calendarId=calendar_id,
                            eventId=source_id,
                            sendNotifications=False,
                            sendUpdates="none",
                        ),
                        callback=cb,
                    )
            else:
                batch.add(
                    self.service.events().import_(
                        calendarId=calendar_id, body=self._event_to_gevent(event)
                    ),
                    callback=cb,
                )
                updated.update(event.source_ids)
        batch.execute()
