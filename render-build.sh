#!/usr/bin/env bash
# Exit immediately if a command fails
set -o errexit

echo "===> Installing Python dependencies..."
pip install -r requirements.txt

STORAGE_DIR=/opt/render/project/.render

if [ ! -f "/chrome/opt/google/chrome/google-chrome" ]; then
  echo "===> Downloading Google Chrome for Render..."
  mkdir -p "/chrome"
  cd "/chrome"
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb .
  rm -f google-chrome-stable_current_amd64.deb
  echo "===> Google Chrome installed successfully in /chrome"
else
  echo "===> Using cached Google Chrome from /chrome"
fi

# Download Khmer fonts to user fonts folder so PDF renders Khmer script perfectly
FONT_DIR="C:\Users\ROG/.fonts"
mkdir -p ""
if [ ! -f "/KantumruyPro-Regular.ttf" ]; then
  echo "===> Downloading Khmer Fonts..."
  wget -q -O "/KantumruyPro-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/kantumruypro/KantumruyPro%5Bwght%5D.ttf" || true
  fc-cache -f "" || true
fi

echo "===> Build completed successfully!"
