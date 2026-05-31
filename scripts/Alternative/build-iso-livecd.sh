#!/bin/bash
set -euo pipefail

BUILD_DIR="/home/bheffernan/arxisos-build"
CACHE_DIR="/var/cache/live"
VERSION="1.2"
ARCH="x86_64"
ISO_NAME="ArxisOS-$VERSION-$ARCH.iso"
LOG_FILE="/tmp/arxisos-build.log"

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "=== Build FAILED (exit code: $exit_code) ==="
        echo "Check build log: $LOG_FILE"
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "=== Last 30 lines of log ==="
            tail -30 "$LOG_FILE"
        fi
    fi
    exit $exit_code
}

trap cleanup EXIT

echo "=== ArxisOS Build Script (livecd-creator) ==="
echo "Building ArxisOS $VERSION"
echo "Started: $(date)"
echo ""

# Create cache directory
sudo mkdir -p "$CACHE_DIR"

# Clean previous ISO
sudo rm -f "$BUILD_DIR/$ISO_NAME"

# Run livecd-creator
echo "Running livecd-creator..."
cd "$BUILD_DIR"
sudo rm -f "$LOG_FILE"
sudo bash -c "livecd-creator \
    --verbose \
    --config=\"$BUILD_DIR/kickstarts/arxisos-kde.ks\" \
    --fslabel=\"ArxisOS-$VERSION\" \
    --cache=\"$CACHE_DIR\" \
    2>&1 | tee \"$LOG_FILE\""

# Find and rename the ISO
CREATED_ISO=$(ls -1 ArxisOS-*.iso 2>/dev/null | head -1)
if [ -z "$CREATED_ISO" ]; then
    echo "ERROR: ISO file was not created!"
    exit 1
fi

if [ "$CREATED_ISO" != "$ISO_NAME" ]; then
    mv "$CREATED_ISO" "$ISO_NAME"
fi

ISO_SIZE=$(du -h "$ISO_NAME" | cut -f1)

echo ""
echo "=== Build Complete ==="
echo "Finished: $(date)"
echo "ISO location: $BUILD_DIR/$ISO_NAME"
echo "ISO size: $ISO_SIZE"
exit 0
