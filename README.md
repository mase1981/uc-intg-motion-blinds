# Motion Blinds Integration for Unfolded Circle Remote 2/3

Control your **Motion Blinds** motorized blinds and shades directly from your Unfolded Circle Remote 2 or Remote 3. Open, close, stop, set position, and tilt each blind - controlled **entirely locally** over your network through the Motion gateway, with **no cloud account** required.

Motion Blinds is the Coulisse motorization platform sold under many brands, including **Brel Home, Smart Home, Bloc Blinds, 3 Day Blinds, Gaviota, Havana Shade** and others that use the Motion gateway and app.

![Motion Blinds](https://img.shields.io/badge/Motion-Blinds-2E7D32)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-motion-blinds?style=flat-square)](https://github.com/mase1981/uc-intg-motion-blinds/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-motion-blinds?style=flat-square)](https://github.com/mase1981/uc-intg-motion-blinds/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-motion-blinds/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Supported Devices

Any blind or shade paired to a **Motion gateway** (Coulisse Motion, Brel Home hub, and equivalents), including roller, roman, honeycomb/cellular, curtain, venetian, and shutter types. Blinds that support tilt (venetian, wood shutter, and similar) get tilt control in addition to position.

> A **Motion gateway** (bridge) is required. Bluetooth-only or RF-only blinds without a gateway are not reachable over the local network and are not supported.

## Features

- **🪟 Cover entity per blind** - each paired blind becomes its own cover with **Open**, **Close**, **Stop**, and **Set Position** (0-100%).
- **🎚️ Tilt control** - venetian blinds and shutters also expose **tilt position**, tilt open/close, and tilt stop.
- **📡 Automatic discovery** - the gateway is found on the network automatically; you only supply the API key.
- **🔄 Live state** - position, tilt, and open/closed/opening/closing state are polled from the gateway.
- **🔒 Fully local** - direct LAN control through the gateway; no Motion/Brel cloud account and no internet in the loop.
- **Multi-gateway** - add each Motion gateway on your network; all of its blinds appear as covers.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

## How It Works

The Motion gateway exposes a local UDP control API secured by a per-gateway **API key**. This integration speaks that protocol directly:

- **No account, no cloud** - control runs entirely over your local network. Nothing is sent to Motion's or the brand's servers.
- **API key from the app** - the gateway is protected by a 16-character key you retrieve once from the Motion Blinds app.
- **State follows the blinds** - position, tilt, and movement state are polled from the gateway and pushed to the Remote.

## Getting Your API Key

1. Open the **Motion Blinds** app (or your brand's equivalent: Brel Home, Smart Home, etc.).
2. Open the app **menu / About** screen.
3. **Tap the app version 5 times** to reveal the **Key** (a 16-character code).
4. Copy that key - you will enter it during setup.

> The key changes if you reset the gateway or re-run its initial pairing. If control stops working after a gateway reset, re-run setup with the new key.

## Requirements

- A Motion gateway with at least one blind paired, on the same network as your Remote.
- The gateway's 16-character API key (see above).
- Unfolded Circle Remote 2 / 3 with firmware supporting custom integrations.

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Download the latest `uc-intg-motion-blinds-<version>.tar.gz` from the [**Releases**](https://github.com/mase1981/uc-intg-motion-blinds/releases) page.
2. Open your Remote's web interface (`http://your-remote-ip`).
3. Go to **Settings -> Integrations -> Add Integration -> Install Custom** and upload the `.tar.gz`.

### Option 2: Docker (Advanced Users)

**Image**: `ghcr.io/mase1981/uc-intg-motion-blinds:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-motion-blinds:
    image: ghcr.io/mase1981/uc-intg-motion-blinds:latest
    container_name: uc-intg-motion-blinds
    network_mode: host
    volumes:
      - ./config:/config
    environment:
      - UC_CONFIG_HOME=/config
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-intg-motion-blinds --restart unless-stopped --network host -v $(pwd)/config:/config -e UC_CONFIG_HOME=/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-motion-blinds:latest
```

## Configuration

1. Make sure your Motion gateway is **powered on** and on the same network as the Remote, with blinds paired in the app.
2. Start setup and enter the **16-character API key** from the app. Leave the IP address blank to **discover the gateway automatically**, or enter it manually if discovery finds nothing.
3. The integration enumerates every blind paired to the gateway and creates a **cover entity** for each.
4. Repeat setup to add additional gateways.

For each gateway the integration creates:

| Entity | Purpose |
|--------|---------|
| **Cover** (one per blind) | Open, close, stop, and set position; plus tilt position / tilt open-close-stop for venetian and shutter blinds. |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No Motion Blinds gateway was found" | Ensure the gateway is powered on and on the same network/subnet as the Remote, then re-run setup and enter the gateway IP manually. |
| "The API Key must be exactly 16 characters" | Re-copy the key from the app (tap the version 5 times on the About screen). |
| Blinds do not move / commands fail | The API key is wrong or was changed by a gateway reset. Re-run setup with the current key. |
| A blind shows no tilt controls | Tilt only appears for blind types that support it (venetian, shutter, and similar). |
| Position looks inverted | Motion uses 0 = open internally; the integration presents 0 = closed / 100 = open to match the Remote. If a blind's limits are reversed, re-set its limits in the Motion app. |

## Credits

- **Developer**: Meir Miyara
- **Motion Blinds local protocol**: built on the [`motionblinds`](https://github.com/starkillerOG/motion-blinds) library by starkillerOG, the same library used by the Home Assistant Motion Blinds integration.
- **Unfolded Circle**: Remote 2/3 integration framework ([ucapi](https://github.com/unfoldedcircle/integration-python-library) / [ucapi-framework](https://github.com/JackJPowell/ucapi-framework)).

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-motion-blinds/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
