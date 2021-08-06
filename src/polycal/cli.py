import datetime
import sys

import click
import coloredlogs
from dateutil import relativedelta
from dependency_injector.wiring import Provide, inject

from polycal.containers import PolycalAppContainer
from polycal.services.calprocessor import CalendarProcessor


@click.command()
@inject
def cli(
    processor: CalendarProcessor = Provide[PolycalAppContainer.calendar_processor],
) -> None:
    """polycal command line"""
    coloredlogs.install()

    now = datetime.datetime.utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start + relativedelta.relativedelta(months=1)
    processor.process(start=start, end=end)


def main():
    container = PolycalAppContainer()
    container.init_resources()
    container.wire(modules=[sys.modules[__name__]])
    cli()


if __name__ == "__main__":
    main()
