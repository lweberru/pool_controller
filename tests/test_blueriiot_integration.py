"""Verify source isolation, registry discovery and stale measurements without HA."""

import ast
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/pool_controller"
NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


def load_reader():
    helpers = ModuleType("homeassistant.helpers")
    helpers.device_registry = NS(async_get=lambda hass: hass.devices)
    helpers.entity_registry = NS(
        async_get=lambda hass: hass.registry,
        async_entries_for_device=lambda registry, device_id: [e for e in registry if e.device_id == device_id],
    )
    util = ModuleType("homeassistant.util")
    util.dt = NS(utcnow=lambda: NOW, parse_datetime=lambda s: datetime.fromisoformat(s))
    modules = {"homeassistant": ModuleType("homeassistant"), "homeassistant.helpers": helpers, "homeassistant.util": util}
    spec = importlib.util.spec_from_file_location("pool_blueriiot_integration_test", ROOT / "blueriiot_integration.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {**modules, spec.name: module}):
        spec.loader.exec_module(module)
    return module


MODULE = load_reader()


class IntegrationReaderTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.states = {}
        keys = ("temperature", "ph", "orp", "salt", "conductivity", "battery", "connected", "last_success", "last_error", "refresh")
        registry = [NS(device_id="pool", platform="blueriiot", disabled_by=None,
                       unique_id=f"AA:BB:CC:DD:EE:FF_{key}", entity_id=f"sensor.renamed_{key}") for key in keys]
        self.hass = NS(
            devices=NS(async_get=lambda device_id: NS(config_entries={"blue"}) if device_id == "pool" else None),
            config_entries=NS(async_get_entry=lambda eid: NS(domain="blueriiot", unique_id="AA:BB:CC:DD:EE:FF", options={"update_interval": 60})),
            registry=registry, states=NS(get=self.states.get),
            services=NS(async_call=AsyncMock()),
        )
        self.reader = MODULE.BlueRiiotIntegrationReader(self.hass)
        for key, value in {"temperature": 34.9, "ph": 7.09, "orp": 567, "connected": "on", "last_success": (NOW - timedelta(minutes=50)).isoformat()}.items():
            self.set_state(key, value)

    def set_state(self, key, value, **attrs):
        self.states[f"sensor.renamed_{key}"] = NS(state=str(value), attributes=attrs)

    async def read(self, **kwargs):
        return await self.reader.async_read_if_due("pool", timedelta(minutes=15), **kwargs)

    async def test_renamed_entities_and_source_interval_without_ble_or_poll(self):
        reading = await self.read()
        self.assertEqual(reading.temperature, 34.9)
        self.assertEqual(reading.orp, 567)
        self.assertIsNone(reading.salt)
        self.assertTrue(self.reader.is_recently_reachable(timedelta(minutes=30)))
        self.hass.services.async_call.assert_not_called()

    async def test_refresh_delegates_to_source_button_only(self):
        await self.read(force=True)
        self.hass.services.async_call.assert_awaited_once_with(
            "button", "press", {"entity_id": "sensor.renamed_refresh"}, blocking=True
        )

    async def test_stale_values_do_not_remain_reachable(self):
        await self.read()
        self.set_state("last_success", (NOW - timedelta(hours=3)).isoformat())
        await self.read()
        self.assertFalse(self.reader.is_recently_reachable(timedelta(days=1)))
        self.assertEqual(self.reader.last_error, "source_measurements_stale")

    async def test_disconnected_source_rejects_preserved_values(self):
        self.set_state("connected", "off")
        await self.read()
        self.assertFalse(self.reader.is_recently_reachable(timedelta(days=1)))

    async def test_missing_or_disabled_sensor_is_not_fabricated(self):
        await self.read()
        self.hass.registry[0].disabled_by = "user"
        self.assertIsNone(await self.read())
        self.assertFalse(self.reader.is_recently_reachable(timedelta(days=1)))

    async def test_deleted_device_clears_previous_reading(self):
        await self.read()
        self.assertIsNone(await self.reader.async_read_if_due("deleted", timedelta()))
        self.assertIsNone(self.reader.last_success)
        self.assertFalse(self.reader.is_recently_reachable(timedelta(days=1)))

    async def test_nonfinite_measurement_is_rejected(self):
        self.set_state("ph", "nan")
        self.assertIsNone(await self.read())

    async def test_temperature_unit_conversion(self):
        self.set_state("temperature", 95, unit_of_measurement="°F")
        self.assertAlmostEqual((await self.read()).temperature, 35)

    async def test_source_error_is_preserved(self):
        self.set_state("last_error", "BlueRiiotDeviceNotFoundError")
        await self.read()
        self.assertEqual(self.reader.last_error, "BlueRiiotDeviceNotFoundError")


class SourceOptionsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Exercise the real normalization function independently of HA's UI classes.
        constants = ast.parse((ROOT / "const.py").read_text())
        constants.body = [node for node in constants.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
        self.namespace = {"re": re}
        exec(compile(constants, "const.py", "exec"), self.namespace)
        flow = ast.parse((ROOT / "config_flow.py").read_text())
        flow.body = [node for node in flow.body if isinstance(node, ast.FunctionDef) and node.name == "_normalize_blueriiot_options"]
        exec(compile(flow, "config_flow.py", "exec"), self.namespace)
        self.normalize = self.namespace["_normalize_blueriiot_options"]

    def test_existing_direct_reader_stays_direct(self):
        result, errors = self.normalize({"enable_blueriiot": True, "blueriiot_mac": "aa:bb:cc:dd:ee:ff"})
        self.assertFalse(errors)
        self.assertEqual(result["blueriiot_source"], "native")

    def test_external_device_disables_native_reader_and_needs_no_mac(self):
        result, errors = self.normalize({"blueriiot_source": "integration", "blueriiot_device": "pool", "enable_blueriiot": True})
        self.assertFalse(errors)
        self.assertFalse(result["enable_blueriiot"])

    def test_external_requires_device(self):
        _, errors = self.normalize({"blueriiot_source": "integration"})
        self.assertIn("blueriiot_device", errors)

    def test_manual_entities_stay_manual(self):
        result, errors = self.normalize({})
        self.assertFalse(errors)
        self.assertEqual(result["blueriiot_source"], "entities")

    async def test_manual_read_dispatch_never_calls_native_reader_in_integration_mode(self):
        tree = ast.parse((ROOT / "coordinator.py").read_text())
        coordinator = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        tree.body = [node for node in coordinator.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_read_blueriiot_now"]
        self.namespace["timedelta"] = timedelta
        exec(compile(tree, "coordinator.py", "exec"), self.namespace)
        native = NS(async_read_if_due=AsyncMock(side_effect=AssertionError("native BLE must not run")))
        external = NS(async_read_if_due=AsyncMock(), last_error=None)
        instance = NS(entry=NS(data={"enable_blueriiot": True}, options={"blueriiot_source": "integration", "blueriiot_device": "pool"}),
                      _native_blueriiot_reader=native, _integration_blueriiot_reader=external)
        self.assertTrue(await self.namespace["async_read_blueriiot_now"](instance))
        native.async_read_if_due.assert_not_called()
        external.async_read_if_due.assert_awaited_once_with("pool", timedelta(), force=True)


if __name__ == "__main__":
    unittest.main()
