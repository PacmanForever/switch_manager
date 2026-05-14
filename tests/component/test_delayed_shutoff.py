"""Component tests for switchflow_controller delayed shutoff behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from homeassistant.core import State

from custom_components.switchflow_controller.controller import ControllerRuntime
from custom_components.switchflow_controller.models import ControllerConfig, GlobalConfig


@pytest.mark.asyncio
async def test_mixed_detector_types_turn_off_early_when_all_clear(hass) -> None:
    """Mixed presence and motion detectors should still turn off early when all clear."""
    controller = ControllerConfig.from_mapping(
        {
            "id": "hallway",
            "name": "Hallway",
            "main_entity": "light.hallway",
            "detector_sensor_1": "binary_sensor.hallway_presence",
            "detector_sensor_2": "binary_sensor.hallway_motion",
            "wait_time": 60,
            "turn_off_when_presence_clears": True,
        }
    )
    hass.states.async_set("light.hallway", "on")
    hass.states.async_set(
        "binary_sensor.hallway_presence",
        "off",
        {"device_class": "presence"},
    )
    hass.states.async_set(
        "binary_sensor.hallway_motion",
        "off",
        {"device_class": "motion"},
    )

    runtime = ControllerRuntime(hass, GlobalConfig(), controller, "entry-1")
    runtime._async_turn_off_entity = AsyncMock()

    await runtime._async_handle_detector_state_change(
        State(
            "binary_sensor.hallway_presence",
            "off",
            {"device_class": "presence"},
        )
    )

    assert runtime._async_turn_off_entity.await_count == 1
    assert runtime._async_turn_off_entity.await_args_list[0].args[0] == "light.hallway"


@pytest.mark.asyncio
async def test_timer_expiry_restarts_when_detector_stays_on(hass, monkeypatch) -> None:
    """An active detector at timer expiry should extend the controller instead of turning it off."""
    controller = ControllerConfig.from_mapping(
        {
            "id": "hallway",
            "name": "Hallway",
            "main_entity": "light.hallway",
            "detector_sensor_1": "binary_sensor.hallway_presence",
            "wait_time": 60,
        }
    )
    hass.states.async_set("binary_sensor.hallway_presence", "on", {"device_class": "presence"})

    runtime = ControllerRuntime(hass, GlobalConfig(), controller, "entry-1")
    runtime._async_turn_off_controlled_entities = AsyncMock()
    runtime._async_all_detectors_are_clear = AsyncMock(side_effect=[False, True])

    sleep_calls = 0

    async def immediate_sleep(_seconds: int) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 2:
            raise AssertionError("timer worker looped more than expected")
        return None

    runtime._timer_task = object()

    with monkeypatch.context() as context:
        context.setattr(
            "custom_components.switchflow_controller.controller.asyncio.sleep",
            immediate_sleep,
        )
        await runtime._async_timer_worker()

    assert sleep_calls == 2
    assert runtime._async_all_detectors_are_clear.await_count == 2
    runtime._async_turn_off_controlled_entities.assert_awaited_once()
    assert runtime._timer_task is None


@pytest.mark.asyncio
async def test_timer_expiry_turns_off_when_detector_is_clear(hass, monkeypatch) -> None:
    """A cleared detector should allow shutoff on the next timer expiry."""
    controller = ControllerConfig.from_mapping(
        {
            "id": "hallway",
            "name": "Hallway",
            "main_entity": "light.hallway",
            "detector_sensor_1": "binary_sensor.hallway_presence",
            "wait_time": 60,
        }
    )
    hass.states.async_set("light.hallway", "on")
    hass.states.async_set("binary_sensor.hallway_presence", "off", {"device_class": "presence"})

    runtime = ControllerRuntime(hass, GlobalConfig(), controller, "entry-1")
    runtime._async_turn_off_entity = AsyncMock()

    async def immediate_sleep(_seconds: int) -> None:
        return None

    runtime._timer_task = object()

    with monkeypatch.context() as context:
        context.setattr(
            "custom_components.switchflow_controller.controller.asyncio.sleep",
            immediate_sleep,
        )
        await runtime._async_timer_worker()

    runtime._async_turn_off_entity.assert_awaited_once_with("light.hallway")
    assert runtime._timer_task is None


@pytest.mark.asyncio
async def test_timer_expiry_turns_off_without_detectors(hass, monkeypatch) -> None:
    """Controllers without detectors should still respect the turn-off delay."""
    controller = ControllerConfig.from_mapping(
        {
            "id": "hallway",
            "name": "Hallway",
            "main_entity": "light.hallway",
            "wait_time": 60,
        }
    )
    hass.states.async_set("light.hallway", "on")

    runtime = ControllerRuntime(hass, GlobalConfig(), controller, "entry-1")
    runtime._async_turn_off_entity = AsyncMock()

    async def immediate_sleep(_seconds: int) -> None:
        return None

    runtime._timer_task = object()

    with monkeypatch.context() as context:
        context.setattr(
            "custom_components.switchflow_controller.controller.asyncio.sleep",
            immediate_sleep,
        )
        await runtime._async_timer_worker()

    runtime._async_turn_off_entity.assert_awaited_once_with("light.hallway")
    assert runtime._timer_task is None


@pytest.mark.asyncio
async def test_concurrent_timer_restarts_do_not_leave_orphaned_tasks(
    hass, monkeypatch
) -> None:
    """Concurrent timer restarts should cancel superseded tasks cleanly."""
    controller = ControllerConfig.from_mapping(
        {
            "id": "hallway",
            "name": "Hallway",
            "main_entity": "light.hallway",
            "wait_time": 60,
        }
    )
    runtime = ControllerRuntime(hass, GlobalConfig(), controller, "entry-1")

    created_tasks: list[asyncio.Task[None]] = []

    async def parked_timer_worker() -> None:
        await asyncio.Future()

    monkeypatch.setattr(runtime, "_async_timer_worker", parked_timer_worker)

    original_create_task = hass.async_create_task

    def tracking_create_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(hass, "async_create_task", tracking_create_task)

    original_timer = original_create_task(parked_timer_worker())
    runtime._timer_task = original_timer

    restart_one = asyncio.create_task(runtime._async_restart_timer())
    restart_two = asyncio.create_task(runtime._async_restart_timer())
    await asyncio.gather(restart_one, restart_two)

    assert len(created_tasks) == 2
    assert created_tasks[0].cancelled()
    assert not created_tasks[1].done()
    assert runtime._timer_task is created_tasks[1]

    await runtime._async_cancel_timer()
    assert created_tasks[1].cancelled()