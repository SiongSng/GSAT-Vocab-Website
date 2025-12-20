#!/bin/bash

# Generate PWA icons from SVG sources
# Requires: rsvg-convert (from librsvg)
# macOS: brew install librsvg
# Ubuntu: apt-get install librsvg2-bin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC_DIR="$SCRIPT_DIR/../public"

cd "$PUBLIC_DIR"

echo "Generating PWA icons from SVG sources..."

# Regular PWA icons (with rounded background)
echo "  → pwa-192x192.png"
rsvg-convert -w 192 -h 192 pwa-icon.svg -o pwa-192x192.png

echo "  → pwa-512x512.png"
rsvg-convert -w 512 -h 512 pwa-icon.svg -o pwa-512x512.png

echo "  → pwa-1024x1024.png"
rsvg-convert -w 1024 -h 1024 pwa-icon.svg -o pwa-1024x1024.png

# Maskable icons (full bleed background for Android adaptive icons)
echo "  → pwa-maskable-192x192.png"
rsvg-convert -w 192 -h 192 pwa-maskable.svg -o pwa-maskable-192x192.png

echo "  → pwa-maskable-512x512.png"
rsvg-convert -w 512 -h 512 pwa-maskable.svg -o pwa-maskable-512x512.png

echo "  → pwa-maskable-1024x1024.png"
rsvg-convert -w 1024 -h 1024 pwa-maskable.svg -o pwa-maskable-1024x1024.png

# Apple touch icon
echo "  → apple-touch-icon.png"
rsvg-convert -w 180 -h 180 pwa-icon.svg -o apple-touch-icon.png

# Favicons from original favicon.svg
echo "  → favicon-32x32.png"
rsvg-convert -w 32 -h 32 favicon.svg -o favicon-32x32.png

echo "  → favicon-16x16.png"
rsvg-convert -w 16 -h 16 favicon.svg -o favicon-16x16.png

# Open Graph image
echo "  → og-image.png"
rsvg-convert -w 1200 -h 630 og-image.svg -o og-image.png

echo ""
echo "✓ All PWA icons generated successfully!"
