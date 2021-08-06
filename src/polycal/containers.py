import pathlib

import yaml
from dependency_injector import containers, providers

from polycal.services.calprocessor import CalendarProcessor, ConfigModel
from polycal.services.gcal import GoogleCalendarService, get_creds


def get_config_path(paths: list[pathlib.Path]):
    for path in paths:
        if path.is_dir():
            return path
    raise ValueError("None of potential config paths %r exists", paths)


def get_config(config_path: pathlib.Path) -> ConfigModel:
    with (config_path / "polycal.yml").open() as f:
        return ConfigModel(
            **yaml.safe_load(f),
        )


DEFAULT_PATHS = [
    pathlib.Path(".polycal/"),
    pathlib.Path("~/.polycal/").expanduser(),
]


class PolycalAppContainer(containers.DeclarativeContainer):
    config_path = providers.Singleton(
        get_config_path,
        DEFAULT_PATHS,
    )
    config = providers.Singleton(get_config, config_path)
    g_client_credentials = providers.Singleton(get_creds, config_path)

    google_calendar_service = providers.Singleton(
        GoogleCalendarService, g_client_credentials
    )
    calendar_processor = providers.Singleton(
        CalendarProcessor,
        config=config,
        gcal_service=google_calendar_service,
    )
