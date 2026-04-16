# Deadpool HUD Dashboard - Setup Guide

A sleek, always-on-top overlay for Ubuntu featuring a dynamic Deadpool-themed smart bubble that expands into a multi-functional dashboard.

## Features

- **Dynamic Round Bubble**: A sleek, draggable Deadpool-themed circular hover icon.
- **Improved Draggability**: Smoothly drag the bubble or the fully expanded dashboard anywhere on your screen.
- **APT Lock Monitor**: Live detection of APT/DPKG locks with a one-click "REPAIR NOW" option.
- **System Monitoring**: Live CPU, RAM, and Disk arc gauges updated every 2 seconds.
- **Network Metrics**: Live upload and download speed sparkline graphs.
- **Secure File Sharing**: Built-in HTTP server to share files/clipboard seamlessly across your local network.
- **Pair Code Authentication**: Employs a random 6-digit `PAIR_CODE` using HTTP Basic Auth for maximum security during local network file transfers.
- **Auto-Refresh IP**: Dynamically updates the server IP and QR code if your network/WiFi changes.
- **Photo Slideshow**: Custom photo slideshow pulled directly from `~/Pictures`.

---

## 1. Install Dependencies (once)

You'll need `python3-tk` and `imagemagick` for the UI and image processing, and a few Python packages for system stats and QR code generation.

```bash
sudo apt update
sudo apt install python3-tk imagemagick
pip3 install psutil qrcode[pil] --break-system-packages
```

---

## 2. Quick Start

```bash
python3 ~/Dashy/desktop_dashboard.py
```

- **Drag and Move** the glowing Deadpool bubble or the **expanded dashboard panel** anywhere on the screen.
- **Click** the bubble to expand it into the full dashboard panel.
- **Click again** (or use the red "x") to collapse the dashboard back into the bubble.
- **Scan the QR Code** displayed on the panel with your phone's camera to instantly log in to your secure file-sharing server (Same WiFi required).

---

## 3. Auto-Start on Login

To make the Deadpool HUD launch automatically every time you log into your system:

```bash
python3 ~/Dashy/desktop_dashboard.py --setup
```

This creates a shortcut in `~/.config/autostart/`.

---

## 4. Customization (Edit `desktop_dashboard.py` config block)

| Setting | Default | Description |
|---|---|---|
| `PHOTO_DIR` | `~/Pictures` | Folder to load slideshow photos from |
| `SHARE_DIR` | `~/Desktop/Sys-Mob` | Folder to store uploaded/shared files |
| `SHARE_PORT` | `8844` | Port number used for the local file sharing server |
| `SLIDE_SECS` | `6` | Seconds between photo changes |
| `BUBBLE_SIZE` | `54` | The size of the circular Deadpool bubble |
| `ALPHA` | `0.95` | Window opacity/transparency |

---

## Remove Autostart

If you want to stop it from running at startup:

```bash
rm ~/.config/autostart/bubble-hud.desktop
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing psutil:` | Run `pip3 install psutil --break-system-packages` |
| `TclError: no display name` | Ensure you are running this in an X11/GUI environment |
| No photos shown | Add `.jpg`/`.png` images to `~/Pictures` and ensure `imagemagick` is installed |
| Devices cannot connect to the Share Server | Ensure your phone and PC are on the exact same WiFi network |
| Pair code rejected natively | Verify you are using the precise 6-digit code shown on the desktop panel |
