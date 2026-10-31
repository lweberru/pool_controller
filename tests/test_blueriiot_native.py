"""Exercise native BLE retry timing without a Home Assistant installation."""

import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).parents[1] / "custom_components/pool_controller"


class NativeReaderTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
        self.device = Mock(return_value="device")
        self.client = NS(start_notify=AsyncMock(), write_gatt_char=AsyncMock(), disconnect=AsyncMock())
        self.connect = AsyncMock(return_value=self.client)
        attrs = {
            "homeassistant": {},
            "homeassistant.components": {"bluetooth": NS(async_ble_device_from_address=self.device)},
            "homeassistant.core": {"HomeAssistant": object},
            "homeassistant.util": {"dt": NS(now=lambda: self.now)},
            "bleak_retry_connector": {"BleakClientWithServiceCache": object, "establish_connection": self.connect},
        }
        modules = {}
        for name, values in attrs.items():
            modules[name] = ModuleType(name)
            modules[name].__dict__.update(values)
        spec = importlib.util.spec_from_file_location("native_pool_test", ROOT / "blueriiot.py")
        module = importlib.util.module_from_spec(spec)
        modules[spec.name] = module
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)
        self.reader = module.BlueRiiotReader(NS(loop=asyncio.get_running_loop()))
        self.client.start_notify.side_effect = lambda uuid, cb: setattr(self, "notify", cb)

        async def write(*args, **kwargs):
            self.notify(0, bytearray(12))

        self.client.write_gatt_char.side_effect = write

    async def read(self, **kwargs):
        return await self.reader.async_read_if_due("AA:BB:CC:DD:EE:FF", timedelta(minutes=15), **kwargs)

    async def test_timeout_retries_after_one_minute_then_resumes_normal_polling(self):
        first = await self.read()
        success = self.reader.last_success
        self.now += timedelta(minutes=15)
        self.client.write_gatt_char.side_effect = TimeoutError()
        self.assertIs(await self.read(), first)
        self.assertEqual(self.reader.last_error, "notification_timeout")
        self.assertEqual(self.reader.last_success, success)
        self.client.disconnect.assert_awaited()
        self.now += timedelta(seconds=59)
        await self.read()
        self.assertEqual(self.connect.await_count, 2)
        self.now += timedelta(seconds=1)
        self.client.write_gatt_char.side_effect = lambda *a, **kw: self.notify(0, bytearray(12))
        await self.read()
        self.assertEqual(self.connect.await_count, 3)
        self.assertIsNone(self.reader.last_error)
        self.now += timedelta(minutes=1)
        await self.read()
        self.assertEqual(self.connect.await_count, 3)
        self.now += timedelta(minutes=14)
        await self.read()
        self.assertEqual(self.connect.await_count, 4)

    async def test_persistent_failure_has_only_two_fast_retries(self):
        self.connect.side_effect = TimeoutError()
        await self.read()
        for _ in range(2):
            self.now += timedelta(minutes=1)
            await self.read()
        self.assertEqual(self.connect.await_count, 3)
        self.now += timedelta(minutes=1)
        await self.read()
        self.assertEqual(self.connect.await_count, 3)
        self.now += timedelta(minutes=14)
        await self.read()
        self.assertEqual(self.connect.await_count, 4)
        self.assertFalse(self.reader.is_recently_reachable(timedelta(minutes=30)))

    async def test_missing_device_also_gets_fast_retry(self):
        self.device.return_value = None
        await self.read()
        self.assertEqual(self.reader.last_error, "device_not_found")
        self.now += timedelta(minutes=1)
        self.device.return_value = "device"
        self.assertIsNotNone(await self.read())
        self.assertIsNone(self.reader.last_error)

    async def test_grace_expires_and_future_timestamps_are_rejected(self):
        await self.read()
        success = self.reader.last_success
        for age, expected in ((-1, False), (34, True), (35, True), (36, False)):
            self.now = success + timedelta(minutes=age)
            self.assertEqual(self.reader.is_recently_reachable(timedelta(minutes=30)), expected)
