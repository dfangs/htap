import asyncio
from datetime import timedelta
from typing import AsyncIterator, final

from typing_extensions import override

from defio.client import AsyncClient
from defio.utils.time import get_current_time
from defio.workload import Workload
from defio.workload.query import Query
from defio.workload.reporter import PrintReporter
from defio.workload.runner import run_workload
from defio.workload.schedule import Once, Repeat
from defio.workload.user import User


@final
class NoopClient(AsyncClient[str]):
    @override
    async def connect(self) -> None:
        return

    @override
    async def close(self) -> None:
        return

    @override
    async def execute(self, query: str) -> AsyncIterator[str]:
        yield query


async def main() -> None:
    current_time = get_current_time()
    interval = timedelta(seconds=1)

    workload = Workload.combine(
        [
            Workload.serial(
                [
                    Query(f"SELECT {i};", Once(at=current_time + 0.47 * i * interval))
                    for i in range(10)
                ],
                user=User.with_label("Once"),
            ),
            Workload.serial(
                [
                    Query(
                        "SELECT *;",
                        Repeat.starting_now(interval=interval, num_repeat=20),
                    ),
                ],
                user=User.with_label("Repeat"),
            ),
        ]
    )

    reporter = PrintReporter()

    async with NoopClient() as client:
        await run_workload(workload, client, reporter)


asyncio.run(main())
