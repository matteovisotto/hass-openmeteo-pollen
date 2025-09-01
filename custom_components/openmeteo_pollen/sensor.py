from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
import aiohttp
import async_timeout

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_MANUFACTURER = "open-meteo.com"
DEVICE_MODEL = "Open Meteo Pollen"
UNIT = "grains/m³"

POLLEN_THRESHOLDS = {
    "grass_pollen": [
        (0, "level_none"),
        (10, "level_low"),       # symptoms begin
        (50, "level_moderate"),  # moderate symptom risk
        (100, "level_high")    # high / severe symptoms
    ],
    "birch_pollen": [
        (0, "level_none"),
        (10, "level_low"),       # start of season
        (50, "level_moderate"),
        (100, "level_high")
    ],
    "alder_pollen": [
        (0, "level_none"),
        (10, "level_low"),
        (50, "level_moderate"),
        (100, "level_high")
    ],
    "olive_pollen": [
        (0, "level_none"),
        (10, "level_low"),
        (50, "level_moderate"),
        (100, "level_high")
    ],
    "mugwort_pollen": [
        (0, "level_none"),
        (10, "level_low"),
        (50, "level_moderate"),
        (100, "level_high")
    ],
    "ragweed_pollen": [
        (0, "level_none"),
        (10, "level_low"),
        (37, "level_moderate"),  # mean threshold in Europe
        (100, "level_high")
    ],
}

LEVEL_RAW_NUM = {
    "level_none": 0,
    "level_low": 1,
    "level_moderate": 2,
    "level_ high": 3,
    "level_very_high": 4
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = PollenDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        AlderPollenSensor(coordinator, entry),
        BirchPollenSensor(coordinator, entry),
        GrassPollenSensor(coordinator, entry),
        MugwortPollenSensor(coordinator, entry),
        OlivePollenSensor(coordinator, entry),
        RagweedPollenSensor(coordinator, entry)
    ]
    async_add_entities(sensors)

def get_level(key, value):
    for threshold, label_key in POLLEN_THRESHOLDS[key]:
        if value <= threshold:
            return label_key
    return "level_very_high"

def get_level_raw_num(key):
    return LEVEL_RAW_NUM[key]

def get_trend(values):
    if len(values) < 2:
        return "trend_stable"
    first, last = values[0], values[-1]
    if last > first * 1.2:
        return "trend_increasing"
    elif last < first * 0.8:
        return "trend_decreasing"
    return "trend_stable"

class PollenDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.latitude = entry.data.get("latitude", hass.config.latitude)
        self.longitude = entry.data.get("longitude", hass.config.longitude)
        update_minutes = entry.options.get("update_interval", entry.data.get("update_interval", 30))
        super().__init__(
            hass,
            _LOGGER,
            name="Open Meteo Pollen",
            update_method=self._async_update_data,
            update_interval=timedelta(minutes=update_minutes),
        )

    async def _async_update_data(self):
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={self.latitude}&longitude={self.longitude}&hourly=alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen&current=alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen&timezone=auto&forecast_days=2"
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(10):
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"Error fetching data: {response.status}")
                        return await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")


class BasePollenSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Pollen Values."""

    _attr_native_unit_of_measurement = UNIT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: UVIndexDataUpdateCoordinator, entry: ConfigEntry, translation_key: str, uid_suffix: str, name: str):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_has_entity_name = True
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}_{uid_suffix}"
        self.raw_name = translation_key
        #self._attr_name = name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Pollen",
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )
        
    @property
    def native_value(self):
        return self.coordinator.data.get("current", {}).get(self.raw_name)
    
    @property
    def extra_state_attributes(self):
        attrs = {
            "updated_at": datetime.fromisoformat(
                self.coordinator.data.get("current", {}).get("time")
            ),
            "current_risk": get_level( self.raw_name, self.coordinator.data.get("current", {}).get(self.raw_name)),
            "current_risk_raw": get_level_raw_num(get_level( self.raw_name, self.coordinator.data.get("current", {}).get(self.raw_name))), 
        }

        hourly = self.coordinator.data.get("hourly", {})
        times = hourly.get("time", [])
        values = hourly.get( self.raw_name, [])

        offset_seconds = self.coordinator.data.get("utc_offset_seconds", 0)
        tz = timezone(timedelta(seconds=offset_seconds))
        now = datetime.now(tz)

        forecast = []
        future_values = []

        for t, v in zip(times, values):
            ts = datetime.fromisoformat(t)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=tz)

            if ts >= now:
                level_key = get_level( self.raw_name, v)
                forecast.append({
                    "datetime": ts.isoformat(),
                    "value": v,
                    "level": level_key,  # return translation key
                    "level_raw": get_level_raw_num(level_key),
                })
                future_values.append(v)

        # statistics
        if future_values:
            peak = max(future_values)
            avg = sum(future_values) / len(future_values)
            trend_key = get_trend(future_values)
            attrs.update({
                "forecast": forecast,
                "forecast_peak": peak,
                "forecast_peak_level": get_level( self.raw_name, peak),
                "forecast_peak_level_raw": get_level_raw_num(get_level( self.raw_name, peak)),
                "forecast_avg": round(avg, 2),
                "forecast_trend": trend_key,
            })
        else:
            attrs["forecast"] = []

        return attrs


class AlderPollenSensor(BasePollenSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "alder_pollen", "alder", "Alder")
        self._attr_icon = "mdi:flower-pollen"
        


class BirchPollenSensor(BasePollenSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "birch_pollen", "birch", "Birch")
        self._attr_icon = "mdi:flower-pollen"
        
        
class GrassPollenSensor(BasePollenSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "grass_pollen", "grass", "Grass")
        self._attr_icon = "mdi:flower-pollen"

    
        
class MugwortPollenSensor(BasePollenSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "mugwort_pollen", "mugwort", "Mugwort")
        self._attr_icon = "mdi:flower-pollen"
        
class OlivePollenSensor(BasePollenSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "olive_pollen", "olive", "Olive")
        self._attr_icon = "mdi:flower-pollen"



class RagweedPollenSensor(BasePollenSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "ragweed_pollen", "ragweed", "Ragweed")
        self._attr_icon = "mdi:flower-pollen"

 




