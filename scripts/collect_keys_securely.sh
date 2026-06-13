#!/usr/bin/env bash
# Secure key collection — never prints secrets, only masked confirmation
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
BACKUP="$ROOT/.env.backup.$(date +%Y%m%d_%H%M%S)"

echo "=== WC2026 Secure Key Collection ==="
echo "Backing up .env → $BACKUP"
cp "$ENV_FILE" "$BACKUP"
echo "Backup done."
echo ""

_update_or_add() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Replace existing line (works on macOS)
    sed -i '' "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    echo "  → Updated $key in .env"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
    echo "  → Added $key to .env"
  fi
}

_confirm() {
  local key="$1" val="$2"
  local len=${#val}
  local first4="${val:0:4}"
  local last4="${val: -4}"
  echo "  ✓ $key: ${first4}...${last4} (${len} chars)"
}

_collect() {
  local key="$1" prompt="$2" val=""
  read -r -s -p "$prompt: " val
  echo ""
  if [[ -z "$val" ]]; then
    echo "  (skipped — keeping existing value)"
    return
  fi
  _update_or_add "$key" "$val"
  _confirm "$key" "$val"
}

# 1. New TheStatsAPI key
echo "--- 1/4: TheStatsAPI ---"
echo "Current key: $(grep '^THESTATSAPI_KEY=' $ENV_FILE | cut -d= -f2- | awk '{print substr($0,1,4)"..."substr($0,length-3,4)" ("length" chars)"}')"
_collect "THESTATSAPI_KEY" "Paste NEW THESTATSAPI_KEY (Enter to skip)"

echo ""
# 2. football-data.org key
echo "--- 2/4: football-data.org ---"
_collect "FOOTBALL_DATA_ORG_KEY" "Paste FOOTBALL_DATA_ORG_KEY (Enter to skip)"

echo ""
# 3. Highlightly base URL (not secret, but structured input)
echo "--- 3/4: Highlightly Base URL ---"
read -r -p "Paste HIGHLIGHTLY_BASE_URL (e.g. https://api.highlightly.net): " HBASE
if [[ -n "$HBASE" ]]; then
  _update_or_add "HIGHLIGHTLY_BASE_URL" "$HBASE"
  echo "  ✓ HIGHLIGHTLY_BASE_URL: $HBASE"
fi

echo ""
# 4. Highlightly doc URL / local doc path
echo "--- 4/4: Highlightly docs ---"
read -r -p "Paste HIGHLIGHTLY_DOC_URL or local doc path (Enter to skip): " HDOC
if [[ -n "$HDOC" ]]; then
  _update_or_add "HIGHLIGHTLY_DOC_URL" "$HDOC"
  echo "  ✓ HIGHLIGHTLY_DOC_URL: $HDOC"
fi

echo ""
echo "=== Done. Current .env keys (masked): ==="
grep -E "^[A-Z_]+=." "$ENV_FILE" | while IFS='=' read -r k v; do
  len=${#v}; f4="${v:0:4}"; l4="${v: -4}"
  echo "  $k = ${f4}...${l4} (${len} chars)"
done
echo ""
echo "Backup saved at: $BACKUP"
echo "Run extraction phases now."
