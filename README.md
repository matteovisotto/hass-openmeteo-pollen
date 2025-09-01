# Open Meteo Pollen – Home Assistant Integration

This custom integration provides **current pollen** from [open-meteo.com](https://open-meteo.com/).  

## Features
- Fetches **current pollen values**.
- Configurable update interval (default: 30 minutes).  
- Supports translations (`en`, `it`).

## Installation

### Via HACS
1. Go to HACS → Integrations → **Custom repositories**.
2. Add repository URL: `https://github.com/matteovisotto/hass-openmeteo-pollen`.
3. Category: Integration.
4. Install, restart Home Assistant.

### Manual
1. Copy `custom_components/openmeteo_pollen` into your Home Assistant config folder.
2. Restart Home Assistant.

## Configuration
Once installed, add via **UI**:
- Go to *Settings → Devices & Services → Add Integration → Open Meteo Pollen*.
- Enter your **latitude** and **longitude**.
- Set **update interval** (minutes).

