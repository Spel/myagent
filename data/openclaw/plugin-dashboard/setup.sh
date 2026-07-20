#!/bin/bash
# Setup: Register the company-brain dashboard as an OpenClaw gateway plugin.
# Run this ONCE from the pod terminal after deploying the new image.
#
# Usage:
#   bash /data/workspace/data/openclaw/plugin-dashboard/setup.sh
#
# After running, the dashboard is accessible at:
#   http://<gateway-host>/__openclaw__/plugin/company-brain-dashboard/

set -e

PLUGIN_SRC="/data/workspace/data/openclaw/plugin-dashboard"
PLUGIN_DEST="${OPENCLAW_HOME:-$HOME/.openclaw}/plugins/company-brain-dashboard"

echo "Installing Company Brain Dashboard plugin..."
echo "  src:  $PLUGIN_SRC"
echo "  dest: $PLUGIN_DEST"

mkdir -p "$(dirname "$PLUGIN_DEST")"

# Symlink so edits in the workspace are reflected immediately
if [ -L "$PLUGIN_DEST" ]; then
  echo "  removing existing symlink"
  rm "$PLUGIN_DEST"
fi

ln -sf "$PLUGIN_SRC" "$PLUGIN_DEST"
echo "  linked: $PLUGIN_DEST → $PLUGIN_SRC"

# Run initial build to embed current analysis data
echo ""
echo "Running initial dashboard build..."
python3 "$PLUGIN_SRC/build.py"

echo ""
echo "Done! Dashboard should appear in the OpenClaw admin panel."
echo "Direct URL: http://localhost:18789/__openclaw__/plugin/company-brain-dashboard/"
echo ""
echo "The dashboard auto-rebuilds on every brain-push.sh cycle (~10 min)."
