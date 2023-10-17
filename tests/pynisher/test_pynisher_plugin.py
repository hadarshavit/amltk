from __future__ import annotations

import logging
import time
import warnings
from concurrent.futures import Executor, ProcessPoolExecutor
from typing import Iterator

import pytest
from dask.distributed import Client, LocalCluster, Worker
from distributed.cfexecutor import ClientExecutor
from pytest_cases import case, fixture, parametrize_with_cases

from amltk.pynisher import PynisherPlugin
from amltk.scheduling import Scheduler, Task


@case(tags=["executor"])
def case_process_executor() -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=2)


@case(tags=["executor"])
def case_loky_executor() -> ProcessPoolExecutor:
    from loky import get_reusable_executor

    return get_reusable_executor(max_workers=2)  # type: ignore


@case(tags=["executor"])
def case_dask_executor() -> ClientExecutor:
    # Dask will raise a warning when re-using the ports, hence
    # we silence the warnings here.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cluster = LocalCluster(
            n_workers=2,
            silence_logs=logging.ERROR,
            worker_class=Worker,
            processes=True,
        )

    client = Client(cluster)
    executor = client.get_executor()
    assert isinstance(executor, ClientExecutor)
    return executor


@fixture()
@parametrize_with_cases("executor", cases=".", has_tag="executor")
def scheduler(executor: Executor) -> Iterator[Scheduler]:
    yield Scheduler(executor)


def big_memory_function(mem_in_bytes: int) -> bytearray:
    z = bytearray(mem_in_bytes)
    return z  # noqa: RET504


def time_wasting_function(duration: int) -> int:
    time.sleep(duration)
    return duration


def cpu_time_wasting_function(iterations: int) -> int:
    while iterations > 0:
        iterations -= 1
    return iterations


def test_memory_limited_task(scheduler: Scheduler) -> None:
    one_half_gb = int(1e9 * 1.5)
    two_gb = int(1e9) * 2

    pynisher = PynisherPlugin(memory_limit=one_half_gb)
    task = Task(
        big_memory_function,
        scheduler,
        plugins=[pynisher],
    )

    @scheduler.on_start
    def start_task() -> None:
        task(mem_in_bytes=two_gb)

    with pytest.raises(PynisherPlugin.MemoryLimitException):
        scheduler.run(on_exception="raise")

    assert task.event_counts == {
        task.SUBMITTED: 1,
        task.DONE: 1,
        task.EXCEPTION: 1,
        pynisher.MEMORY_LIMIT_REACHED: 1,
    }

    assert scheduler.event_counts == {
        scheduler.STARTED: 1,
        scheduler.STOP: 1,
        scheduler.FINISHING: 1,
        scheduler.FINISHED: 1,
        scheduler.EMPTY: 1,
        scheduler.FUTURE_SUBMITTED: 1,
        scheduler.FUTURE_DONE: 1,
    }


def test_time_limited_task(scheduler: Scheduler) -> None:
    pynisher = PynisherPlugin(wall_time_limit=1)
    task = Task(
        time_wasting_function,
        scheduler,
        plugins=[pynisher],
    )

    @scheduler.on_start
    def start_task() -> None:
        task(duration=3)

    with pytest.raises(PynisherPlugin.WallTimeoutException):
        scheduler.run(on_exception="raise")

    assert task.event_counts == {
        task.SUBMITTED: 1,
        task.DONE: 1,
        task.EXCEPTION: 1,
        pynisher.TIMEOUT: 1,
        pynisher.WALL_TIME_LIMIT_REACHED: 1,
    }

    counts = {
        scheduler.STARTED: 1,
        scheduler.STOP: 1,
        scheduler.FINISHING: 1,
        scheduler.FINISHED: 1,
        scheduler.EMPTY: 1,
        scheduler.FUTURE_SUBMITTED: 1,
        scheduler.FUTURE_DONE: 1,
    }
    assert scheduler.event_counts == counts


def test_cpu_time_limited_task(scheduler: Scheduler) -> None:
    pynisher = PynisherPlugin(cpu_time_limit=1)
    task = Task(
        cpu_time_wasting_function,
        scheduler,
        plugins=[pynisher],
    )

    @scheduler.on_start
    def start_task() -> None:
        task(iterations=int(1e16))

    with pytest.raises(PynisherPlugin.CpuTimeoutException):
        scheduler.run(on_exception="raise")

    assert task.event_counts == {
        task.SUBMITTED: 1,
        task.DONE: 1,
        task.EXCEPTION: 1,
        pynisher.TIMEOUT: 1,
        pynisher.CPU_TIME_LIMIT_REACHED: 1,
    }

    assert scheduler.event_counts == {
        scheduler.STARTED: 1,
        scheduler.STOP: 1,
        scheduler.FINISHING: 1,
        scheduler.FINISHED: 1,
        scheduler.EMPTY: 1,
        scheduler.FUTURE_SUBMITTED: 1,
        scheduler.FUTURE_DONE: 1,
    }
