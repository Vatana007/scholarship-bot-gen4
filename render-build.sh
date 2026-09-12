#!/usr/bin/env bash
set -e

echo "===> Installing Python dependencies..."
pip install -r requirements.txt

PROJECT_DIR="$(pwd)"
CHROME_DIR="$PROJECT_DIR/.chrome"

if [ ! -f "$CHROME_DIR/opt/google/chrome/google-chrome" ]; then
  echo "===> Downloading Google Chrome for Render..."
  mkdir -p "$CHROME_DIR"
  cd "$CHROME_DIR"
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb .
  rm -f google-chrome-stable_current_amd64.deb
  cd "$PROJECT_DIR"
  echo "===> Google Chrome installed successfully!"
else
  echo "===> Using cached Google Chrome."
  fi

FONT_DIR="$HOME/.fonts"
mkdir -p "$FONT_DIR"
if [ ! -f "$FONT_DIR/KantumruyPro-Regular.ttf" ]; then
  echo "===> Downloading Khmer Fonts..."
  wget -q -O "$FONT_DIR/KantumruyPro-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/kantumruypro/KantumruyPro%5Bwght%5D.ttf" || true
  fc-cache -f "$FONT_DIR" || true
fi

echo "===> Build completed successfully!"
