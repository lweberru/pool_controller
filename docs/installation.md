# Installation & Setup

[← Back to README](../README.md)

## Hardware Requirements

### Essential
1. **Smart Switch** for main pool pump (on/off relay, WiFi/Zigbee compatible with HA)
2. **Home Assistant** instance with custom components support
3. **Optional: Temperature Sensors**
   - Water temperature (for heating calculations)
   - Outdoor temperature (for frost protection)

### For Water Quality Monitoring (Optional but Recommended)
1. **ESP32 Microcontroller** (e.g., ESP32-S3-DevKitC-1)
2. **Blueriiot Sensor** ([Blue Connect GO](https://www.blueriiot.com/eu-en/products/blue-connect-go))
   - Measures: Temperature, pH, ORP (Chlorine), Salt, Conductivity, Battery
3. **ESPHome Configuration** (provided as reference)

### For Auxiliary Heating (Optional)
- Secondary smart switch controlling auxiliary heater

## My personal setup (example)

This is the setup I’m running Pool Controller with (as a concrete reference/example):

- Softub Poseidon X
- Connected via Zigbee smart plug (ZHA)
- Blueriiot Blue Connect Go for the measurements
- ESP32 to read the Blueriiot data
- 2500 W immersion heater as auxiliary heating
- Immersion heater connected via Zigbee smart plug

## Install Custom Component via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Go to **HACS → Integrations → ⋮ (menu) → Custom repositories**
3. Add custom repository:
   - **Repository**: `https://github.com/lweberru/pool_controller`
   - **Category**: `Integration`
4. Click **Create**
5. Go to **HACS → Integrations** and search for **"Pool Controller"**
6. Click **Install**
7. Restart Home Assistant
8. Go to **Settings → Devices & Services → Create Automation → Pool Controller**

## Dashboard Card (Separate HACS Plugin)

The dashboard card shown in the README preview is available as a separate HACS plugin:

**Repository**: [lweberru/pool_controller_dashboard_frontend](https://github.com/lweberru/pool_controller_dashboard_frontend)

**Installation:**
1. Go to **HACS → Frontend → ⋮ (menu) → Custom repositories**
2. Add custom repository:
   - **Repository**: `https://github.com/lweberru/pool_controller_dashboard_frontend`
   - **Category**: `Lovelace`
3. Click **Add**
4. Search for "Pool Controller Dashboard" and install
5. HACS will automatically register the resource (`/hacsfiles/pool_controller_dashboard_frontend/main.js`)
6. Add the card to your dashboard:
   - **Type**: `custom:pc-pool-controller`
   - **Config**: Use "Automatically load from instance" in the card editor

**Features:**
- 📊 Real-time water quality monitoring (pH, Chlorine, Salt, TDS)
- 🎮 Quick action buttons (Pause, Bathing, Filter, Quick Chlorine)
- 🌡️ Temperature display and climate control
- ⏱️ Timer displays for all active sessions
- 🔔 Status indicators and alerts
- 🎨 Customizable themes and layout
- 🌍 Multi-language support (de, en, es, fr)

## Alternative: Manual Installation

If you prefer manual installation without HACS:

1. Copy the `custom_components/pool_controller` directory to your Home Assistant `custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Create Automation → Pool Controller**
