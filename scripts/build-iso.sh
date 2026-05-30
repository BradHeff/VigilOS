#!/bin/bash
set -euo pipefail

BUILD_DIR="/home/bheffernan/arxisos-build"
BLUEPRINT="arxisos-kde"
IMAGE_TYPE="workstation-live-installer"
# Derive version from blueprint to keep messaging in sync
VERSION=$(grep -m1 '^version' "$BUILD_DIR/blueprints/arxisos-kde.toml" 2>/dev/null | sed -E 's/.*"([^"]*)".*/\1/')
VERSION="${VERSION:-1.0}"

echo "=== ArxisOS Build Script (osbuild-composer) ==="
echo "Building ArxisOS $VERSION"
echo "Started: $(date)"
echo ""

# Ensure osbuild-composer is running
if ! systemctl is-active --quiet osbuild-composer.socket; then
    echo "Starting osbuild-composer..."
    sudo systemctl start osbuild-composer.socket
fi

# Push latest blueprint
echo "Pushing blueprint..."
sudo composer-cli blueprints push "$BUILD_DIR/blueprints/arxisos-kde.toml"

# Start compose
echo "Starting compose..."
COMPOSE_OUTPUT=$(sudo composer-cli compose start "$BLUEPRINT" "$IMAGE_TYPE" 2>&1)
echo "$COMPOSE_OUTPUT"

# Extract compose ID
COMPOSE_ID=$(echo "$COMPOSE_OUTPUT" | grep -oP 'Compose \K[a-f0-9-]+')

if [ -z "$COMPOSE_ID" ]; then
    echo "ERROR: Failed to start compose"
    exit 1
fi

echo ""
echo "Compose ID: $COMPOSE_ID"
echo ""
echo "Monitor progress with:"
echo "  sudo composer-cli compose status"
echo "  sudo composer-cli compose log $COMPOSE_ID"
echo ""
echo "When complete, download with:"
echo "  sudo composer-cli compose image $COMPOSE_ID"
echo ""

# Optionally wait for completion
if [ "${1:-}" = "--wait" ]; then
    echo "Waiting for compose to complete..."
    # Match the FINISHED/FAILED keyword anywhere on the compose's status line.
    # composer-cli's column layout varies between weldr-client versions, so a
    # positional `awk '{print $2}'` is fragile and silently never matches —
    # which previously left this loop spinning forever on a finished compose.
    missing=0
    while true; do
        STATUS_LINE=$(sudo composer-cli compose status 2>/dev/null | grep "$COMPOSE_ID" || true)
        if [ -z "$STATUS_LINE" ]; then
            # Status query failed or compose vanished; tolerate transient blips,
            # but don't spin forever if it's genuinely gone.
            missing=$((missing + 1))
            if [ "$missing" -ge 10 ]; then
                echo ""
                echo "ERROR: compose $COMPOSE_ID not found after repeated status checks." >&2
                exit 1
            fi
            sleep 30
            continue
        fi
        missing=0
        if echo "$STATUS_LINE" | grep -qw FINISHED; then
            echo ""
            echo "=== Build Complete ==="
            echo "Downloading ISO..."
            cd "$BUILD_DIR"
            sudo composer-cli compose image "$COMPOSE_ID"
            ISO_FILE=$(ls -1t *.iso 2>/dev/null | head -1)
            if [ -n "$ISO_FILE" ]; then
                echo "ISO: $BUILD_DIR/$ISO_FILE"
                echo "Size: $(du -h "$ISO_FILE" | cut -f1)"
            fi
            exit 0
        elif echo "$STATUS_LINE" | grep -qw FAILED; then
            echo ""
            echo "=== Build FAILED ==="
            sudo composer-cli compose log "$COMPOSE_ID" | tail -50
            exit 1
        else
            echo -n "."
            sleep 30
        fi
    done
fi

echo "Build queued. Use --wait flag to wait for completion."
exit 0
