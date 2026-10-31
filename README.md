# Trainer Buddy – Pokémon Desktop Pet That Follows Your Mouse Cursor (Windows)

**Trainer Buddy** is a free, lightweight **desktop pet for Windows 10 and 11**: a retro pixel-art trainer (FireRed/LeafGreen style) walks after your **mouse cursor**, and a **Pokémon companion** walks right behind him. It sits on top of your desktop, never gets in the way of your clicks, and starts with Windows.

![Trainer Buddy: the trainer walks to the mouse cursor with Pikachu following behind](docs/screenshot.png)

**[⬇ Download TrainerBuddy.exe (latest release)](https://github.com/333stack/trainer-buddy/releases/latest)** – one file, no Python or installer needed.

## Features

- 🖱️ **Cursor follower** – the trainer chases your mouse pointer around the screen with authentic GBA walk animations.
- 🏃 **Sprinting** – when the pointer is far away he breaks into the real running animation, with a dust puff as he takes off.
- 🧭 **Natural pathing** – walks diagonals as clean L-shaped paths instead of zig-zagging, and stops just short of the cursor so it stays visible.
- ⚡ **11 Pokémon companions** – Pikachu, Flareon, Abra, Lucario, Mew, Snorlax, Unown, Jigglypuff, Voltorb, Gastly and Gengar.
- ⚙️ **Trainer Buddy Settings** – a small settings app to pick your companion; the running buddy switches **live**, no restart.
- 👻 **Click-through** – the sprites are transparent to the mouse, so you can work, browse and game normally.
- 🚀 **Starts with Windows** – optional, per-user, no admin rights required.
- 🪶 **Tiny and portable** – a single exe, or a single Python script using only the standard library (tkinter).

## Install (Windows exe – recommended)

1. Download `TrainerBuddy.exe` from the [Releases page](https://github.com/333stack/trainer-buddy/releases/latest).
2. Double-click it. Windows SmartScreen may say *"Windows protected your PC"* because the exe is not code-signed: click **More info → Run anyway**.
3. It asks **"Install Trainer Buddy?"**
   - **Yes** – copies itself to `%LOCALAPPDATA%\TrainerBuddy`, starts with Windows, adds Start menu entries (*Trainer Buddy*, *Trainer Buddy Settings*) and starts.
   - **No** – just runs it this once.

Verify the download with `SHA256SUMS.txt` from the release: `certutil -hashfile TrainerBuddy.exe SHA256`.

## How do I change the Pokémon?

Open **Start menu → Trainer Buddy Settings** (or run `TrainerBuddy.exe --settings`), pick a companion and save. The buddy on screen switches immediately.

## How do I stop or uninstall it?

| Action | Command |
|---|---|
| Choose companion | `TrainerBuddy.exe --settings` |
| Stop | `TrainerBuddy.exe --quit` (or end *TrainerBuddy.exe* in Task Manager) |
| Uninstall | `TrainerBuddy.exe --uninstall` – removes the files, startup entry and Start menu entries |
| Self-test | `TrainerBuddy.exe --selftest` |

## Run from source (Python)

Needs [Python 3 for Windows](https://www.python.org/downloads/windows/) with tcl/tk (on by default).

- **Install:** double-click `install.bat` (same as the exe's install: `%LOCALAPPDATA%\TrainerBuddy`, autostart, Start menu).
- **Run once:** `pyw trainer_buddy.pyw`
- **Settings:** `pyw trainer_buddy.pyw --settings`
- **Uninstall:** double-click `uninstall.bat`

### Tweaks

Edit the constants at the top of `trainer_buddy.pyw`, then restart it:

| Setting | What it does |
|---|---|
| `SCALE` | sprite size (2 = GBA pixels doubled) |
| `SPEED` | walking speed |
| `RUN_START` / `RUN_STOP` | sprint start / stop distance from the cursor |
| `DUST_PUFF` | `False` = no dust puff when sprinting |
| `L_PATH` | `False` = zig-zag pathing on diagonals |
| `KEEP_OFF` | how far from the pointer he stops |

## Building the exe

`./build-exe.sh` (Linux) builds `dist/TrainerBuddy.exe` with Windows Python 3.13 + PyInstaller under Wine in a private prefix, then runs the exe's own self-test.

## FAQ

**Is it safe?** Source code is in this repo; the exe is built from it with PyInstaller. It only writes to your user folder (`%APPDATA%\TrainerBuddy`, `%LOCALAPPDATA%\TrainerBuddy`), the per-user Run registry key and your Start menu. No network access.

**Does it work on Windows 10 / 11?** Yes, it targets both. macOS/Linux are not supported by this build.

**Does it slow down games?** It is a tiny 33 FPS overlay of two small sprites; click-through means it never steals input.

## Disclaimer

Trainer Buddy is an unofficial, non-commercial fan project. It is not affiliated with, endorsed or sponsored by Nintendo, Game Freak, Creatures Inc. or The Pokémon Company. Pokémon and all related names and sprites are trademarks and © of their respective owners. Sprites come from the [pret/pokefirered](https://github.com/pret/pokefirered) and [rh-hideout/pokeemerald-expansion](https://github.com/rh-hideout/pokeemerald-expansion) projects. Rights holders can open an issue and the assets will be removed.

<sub>Keywords: desktop pet, desktop buddy, mouse follower, cursor pet, Pokémon desktop pet, pixel art companion, Windows desktop toy, FireRed overworld sprites, shimeji-style pet.</sub>
