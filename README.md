# Bezel Launcher Ultimate

A lightweight, robust Python/Tkinter frontend designed for Windows arcade cabinets and retro gaming setups (such as decompiled/recompiled arcade ports). It automatically launches games, overlays custom transparent PNG bezels with click-through Win32 transparency, centers/borderless-scales the game window natively, and manages background helper apps (like x360ce or XOutput).

## Features
- **True Transparent Overlays**: Uses Win32 layered windows for flawless click-through and non-activating overlays.
- **Smart Process Tracking**: Powered by `psutil` to track child processes and multi-launcher setups reliably.
- **Auto-Centering & Borderless**: Automatically strips window borders and centers the game inside the bezel container.
- **Helper App Integration**: Automatically launches background mapping utilities (minimized/background) and terminates them on exit.
- **Standalone Generator**: Create a dedicated single-game script/executable directly from the UI.
- **Emergency Hotkeys**: Press `Ctrl + Alt + B` or `F4` to force-quit the bezel and game instantly.

## Requirements
- Windows 10 / 11
- Python 3.8+

## Installation & Usage
1. Clone or download this repository.
2. Install dependencies via command prompt:
   ```cmd
   pip install pillow psutil