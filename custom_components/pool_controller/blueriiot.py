"""BlueRiiot GATT reader using Home Assistant's Bluetooth adapters and proxies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


SERVICE_UUID = "F3300001-F0A2-9B06-0C59-1BC4763B5C00"
COMMAND_CHARACTERISTIC_UUID = "F3300002-F0A2-9B06-0C59-1BC4763B5C00"
NOTIFY_CHARACTERISTIC_UUID = "F3300003-F0A2-9B06-0C59-1BC4763B5C00"

RETRY_INTERVAL = timedelta(minutes=1)
MAX_FAST_RETRIES = 2
REACHABILITY_GRACE = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class BlueRiiotReading:
    """Decoded measurement values from a BlueRiiot notification."""

    temperature: float
    ph: float
    orp: float
    salt: float
    conductivity: float
    battery: float


class BlueRiiotReader:
    """Fetch one BlueRiiot notification at a controlled polling interval."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._address: str | None = None
        self._failed_attempts = 0
        self._last_attempt = None
        self.last_success = None
        self.last_error: str | None = None
        self.reading: BlueRiiotReading | None = None
        self._lock = asyncio.Lock()

    async def async_read_if_due(
        self,
        address: str,
        minimum_interval: timedelta,
        *,
        force: bool = False,
        salt_divisor: float = 18.0,
    ) -> BlueRiiotReading | None:
        """Read once when due, or immediately when explicitly requested."""
        normalized_address = address.upper()
        now = dt_util.now()
        if normalized_address != self._address:
            self._address = normalized_address
            self._failed_attempts = 0
            self._last_attempt = None
            self.last_success = None
            self.last_error = None
            self.reading = None

        if (
            not force and self._last_attempt
            and now - self._last_attempt < self._attempt_interval(minimum_interval)
        ):
            return self.reading

        async with self._lock:
            now = dt_util.now()
            if (
                not force and self._last_attempt
                and now - self._last_attempt < self._attempt_interval(minimum_interval)
            ):
                return self.reading
            self._last_attempt = now
            if self._failed_attempts > MAX_FAST_RETRIES:
                self._failed_attempts = 0
            self._failed_attempts += 1
            if salt_divisor <= 0:
                self.last_error = "invalid_salt_divisor"
                return self.reading

            device = bluetooth.async_ble_device_from_address(
                self._hass, normalized_address, connectable=True
            )
            if device is None:
                self.last_error = "device_not_found"
                return self.reading

            notification = self._hass.loop.create_future()

            def _handle_notification(_: int, payload: bytearray) -> None:
                if not notification.done():
                    notification.set_result(bytes(payload))

            client = None
            try:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    "Pool Controller BlueRiiot",
                )
                await client.start_notify(NOTIFY_CHARACTERISTIC_UUID, _handle_notification)
                await client.write_gatt_char(
                    COMMAND_CHARACTERISTIC_UUID, b"\x01", response=True
                )
                payload = await asyncio.wait_for(notification, timeout=20)
                self.reading = self._decode(payload, salt_divisor=salt_divisor)
                self.last_success = dt_util.now()
                self.last_error = None
                self._failed_attempts = 0
            except asyncio.TimeoutError:
                self.last_error = "notification_timeout"
            except Exception as err:  # BLE backends expose several backend-specific errors.
                self.last_error = type(err).__name__
            finally:
                if client is not None:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                self._last_attempt = dt_util.now()
        return self.reading

    def _attempt_interval(self, minimum_interval: timedelta) -> timedelta:
        if (
            self.last_error and self.last_error != "invalid_salt_divisor"
            and 0 < self._failed_attempts <= MAX_FAST_RETRIES
        ):
            return min(minimum_interval, RETRY_INTERVAL)
        return minimum_interval

    def is_recently_reachable(self, maximum_age: timedelta) -> bool:
        """Return whether a successful direct measurement is still recent."""
        return bool(
            self.last_success
            and timedelta(0) <= dt_util.now() - self.last_success
            <= maximum_age + REACHABILITY_GRACE
        )

    @staticmethod
    def _decode(payload: bytes, *, salt_divisor: float = 18.0) -> BlueRiiotReading:
        if len(payload) < 12:
            raise ValueError(f"incomplete_payload_{len(payload)}")

        def _int16(offset: int) -> int:
            return int.from_bytes(payload[offset : offset + 2], "little", signed=True)

        if salt_divisor <= 0:
            raise ValueError("invalid_salt_divisor")
        raw_ph = float(_int16(3))
        raw_salt = _int16(7)
        return BlueRiiotReading(
            temperature=_int16(1) / 100.0,
            ph=(2048.0 - raw_ph) / 232.0 + 7.0,
            orp=_int16(5) / 3.86 - 21.57826,
            salt=raw_salt / salt_divisor,
            conductivity=_int16(9) / 4.134,
            battery=min(100.0, max(0.0, payload[11] / 36.0 * 100.0)),
        )