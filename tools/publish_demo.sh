#!/usr/bin/env bash
# Publish the online demo (ui/ + example data only) to the public repo that serves GitHub Pages.
#   tools/publish_demo.sh [owner/repo]      default: Stevenenson/netcheck-demo
# Needs: gh (logged in), python with the repo's requirements. Publishes ONLY synthetic example networks.
set -euo pipefail
REPO="${1:-Stevenenson/netcheck-demo}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python "$ROOT/tools/export_ui_data.py" --out "$WORK/data.js"
cp "$ROOT/ui/index.html" "$ROOT/ui/app.js" "$ROOT/ui/styles.css" "$WORK/"
cp "$ROOT/docs/demo-README.md" "$WORK/README.md"
touch "$WORK/.nojekyll"

if ! gh repo view "$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" --public --description "netcheck demo: home network security, simply explained (example networks only)"
fi
cd "$WORK"
git init -q -b main
git add -A
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" \
  commit -q -m "Publish netcheck demo"
git push -q --force "https://github.com/$REPO.git" main
gh api -X POST "repos/$REPO/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 || true
echo "Demo: https://$(echo "${REPO%%/*}" | tr '[:upper:]' '[:lower:]').github.io/${REPO#*/}/"
