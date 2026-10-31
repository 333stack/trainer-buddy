#!/usr/bin/env bash
# Builds dist/TrainerBuddy.exe: one file, no Python or anything else needed on the Windows PC.
# Runs Windows Python + PyInstaller under Wine in a private prefix (set up on first run, ~2 min).
# Then runs the exe's own --selftest. Usage: ./build-exe.sh
set -euo pipefail
cd "$(dirname "$0")"

PY_VERSION=3.13.17
PY_SHA256=5da012101ba2e17113a9a1cd901e9ce1441086f2b7ecb5de06ec94163899a190   # python.org installer
PYINSTALLER_VERSION=6.22.3
BUILD_HOME="${TRAINER_CHASER_BUILD_HOME:-$HOME/.cache/trainerchaser-winbuild}"
export WINEPREFIX="$BUILD_HOME/prefix" WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml="
PY='C:\py\python.exe'

if ! wine "$PY" -c "import tkinter, PyInstaller" >/dev/null 2>&1; then
    echo "Setting up the Windows build environment in $BUILD_HOME (first run only)..."
    mkdir -p "$BUILD_HOME"
    inst="$BUILD_HOME/python-$PY_VERSION-amd64.exe"
    [[ -f $inst ]] || curl -sSfL -o "$inst" "https://www.python.org/ftp/python/$PY_VERSION/python-$PY_VERSION-amd64.exe"
    echo "$PY_SHA256  $inst" | sha256sum -c --quiet
    wineboot -i >/dev/null 2>&1 || true
    wine "$inst" /quiet InstallAllUsers=0 'TargetDir=C:\py' Include_tcltk=1 Include_test=0 \
        Include_doc=0 Include_launcher=0 PrependPath=0 Shortcuts=0
    wine "$PY" -m pip install --quiet --disable-pip-version-check "pyinstaller==$PYINSTALLER_VERSION"
fi

rm -rf build dist
wine "$PY" -m PyInstaller --noconfirm --clean --onefile --windowed --name TrainerBuddy \
    --add-data "Z:$PWD/sprites;sprites" --distpath dist --workpath build --specpath build \
    trainer_buddy.pyw > build-exe.log 2>&1 || { tail -30 build-exe.log; exit 1; }
rm -rf build

# the exe's own self-test (windowed exe: result is the exit code + a log file)
wine dist/TrainerBuddy.exe --selftest || {
    echo "SELFTEST FAILED:"; cat "$WINEPREFIX/drive_c/users/$USER/AppData/Local/Temp/trainer-buddy-selftest.txt"; exit 1; }
sha256sum dist/TrainerBuddy.exe > dist/SHA256SUMS.txt
echo "Built dist/TrainerBuddy.exe ($(du -h dist/TrainerBuddy.exe | cut -f1)), selftest ok, PyInstaller $PYINSTALLER_VERSION, Python $PY_VERSION"
