#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "[1/4] Installing system packages..."
sudo pacman -S --needed --noconfirm \
    python-evdev \
    python-yaml \
    alsa-utils \
    libnotify \
    espeak-ng

echo "[2/4] Adding $USER to 'input' group (requires logout/login)..."
sudo usermod -aG input "$USER"

echo "[3/4] Creating Python venv (with system site-packages for evdev + yaml)..."
python3 -m venv --system-site-packages "$VENV_DIR"

echo "[4/4] Installing faster-whisper into venv..."
"$VENV_DIR/bin/pip" install faster-whisper

echo ""
echo "Setup complete!"
echo ""
echo "IMPORTANT: Log out and back in so the 'input' group takes effect."
echo "Until then, test with: sudo python3 crowia.py --debug"
echo ""
echo "After re-login, run: python3 $PROJECT_DIR/crowia.py"
echo ""
echo "Test commands:"
echo "  python3 crowia.py --list-devices    # show keyboard devices"
echo "  python3 crowia.py --debug           # run with verbose logging"
echo "  tail -f /tmp/crowia/crowia.log      # watch logs"
