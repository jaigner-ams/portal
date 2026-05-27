#!/usr/bin/env bash
#
# deploy.sh — build assets locally, push, then deploy to all portal servers.
#
# The servers have no Node/npm, so the compiled Tailwind CSS must be built
# here and shipped through git. This script does that, then on each server:
#   git pull -> pip install (venv) -> migrate -> collectstatic -> chown ->
#   reload the portal mod_wsgi daemon.
#
# Usage:
#   ./deploy.sh                 # full deploy (build + push + deploy both servers)
#   ./deploy.sh --no-build      # skip local CSS build/commit/push, just deploy HEAD
#   SERVERS="ams1" ./deploy.sh  # deploy a single server
#
# Optional Cloudflare cache purge (avoids the stale-404 problem on CSS):
#   export CF_API_TOKEN=...     # token with Zone > Cache Purge
#   export CF_ZONE_ID=...       # zone id for amsfusion.com
#
set -euo pipefail

# ---- config -----------------------------------------------------------------
SERVERS="${SERVERS:-ams1 ams2}"      # ssh host aliases (defined in ~/.ssh/config)
BRANCH="${BRANCH:-main}"
REPO_DIR="/var/www/portal"           # path to the checkout on each server
SITE_URL="https://portal.amsfusion.com"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- pretty output ----------------------------------------------------------
if [[ -t 1 ]]; then BOLD=$'\033[1m'; GREEN=$'\033[32m'; RED=$'\033[31m'; YEL=$'\033[33m'; NC=$'\033[0m'
else BOLD=; GREEN=; RED=; YEL=; NC=; fi
info()  { echo "${BOLD}==>${NC} $*"; }
ok()    { echo "${GREEN}  ✓${NC} $*"; }
warn()  { echo "${YEL}  ! ${NC}$*"; }
die()   { echo "${RED}  ✗ $*${NC}" >&2; exit 1; }

# Load local deploy secrets (Cloudflare creds, etc.) if present — never committed.
if [[ -f "$LOCAL_DIR/.deploy.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$LOCAL_DIR/.deploy.env"; set +a
fi

BUILD=1
[[ "${1:-}" == "--no-build" ]] && BUILD=0

# ---- phase 1: build + push (local) ------------------------------------------
if [[ "$BUILD" == "1" ]]; then
  info "Building Tailwind CSS locally"
  ( cd "$LOCAL_DIR/theme" && npm run build >/dev/null ) || die "Tailwind build failed"
  ok "CSS built"

  cd "$LOCAL_DIR"
  # Commit the rebuilt assets if (and only if) they changed.
  if ! git diff --quiet -- core/static restorations/static; then
    info "Compiled assets changed — committing"
    git add core/static restorations/static
    git commit -q -m "chore: rebuild static assets for deploy"
    ok "assets committed"
  else
    ok "no asset changes to commit"
  fi

  # Refuse to deploy with unrelated uncommitted changes — we deploy what's in git.
  if ! git diff --quiet || ! git diff --cached --quiet; then
    die "Working tree has uncommitted changes. Commit or stash them, then re-run."
  fi

  info "Pushing $BRANCH to origin"
  git push -q origin "$BRANCH"
  ok "pushed $(git rev-parse --short HEAD)"
else
  warn "--no-build: skipping local build/commit/push; deploying current origin/$BRANCH"
fi

# ---- phase 2: deploy (each server) ------------------------------------------
FAILED=()
for host in $SERVERS; do
  info "Deploying to ${BOLD}$host${NC}"
  if ssh -o ConnectTimeout=10 "$host" "REPO_DIR='$REPO_DIR' BRANCH='$BRANCH' bash -s" <<'REMOTE'
    set -euo pipefail
    cd "$REPO_DIR"

    # git runs as root against a tree that may be owned by www-data; trust it.
    git config --global --get-all safe.directory | grep -qx "$REPO_DIR" \
      || git config --global --add safe.directory "$REPO_DIR"

    echo "  - git pull --ff-only origin $BRANCH"
    git pull --ff-only origin "$BRANCH"

    echo "  - pip install -r requirements.txt"
    venv/bin/pip install -q -r requirements.txt

    echo "  - migrate"
    venv/bin/python manage.py migrate --noinput

    echo "  - collectstatic"
    venv/bin/python manage.py collectstatic --noinput >/dev/null

    echo "  - chown static/ media/ -> www-data"
    chown -R www-data:www-data "$REPO_DIR/static" "$REPO_DIR/media" 2>/dev/null || true

    echo "  - reload portal wsgi daemon (touch wsgi.py)"
    touch "$REPO_DIR/portal/wsgi.py"

    echo "  - HEAD now $(git rev-parse --short HEAD)"
REMOTE
  then
    ok "$host done"
  else
    warn "$host FAILED"
    FAILED+=("$host")
  fi
done

# ---- optional: purge Cloudflare so the new CSS isn't masked by a cached 404 --
if [[ -n "${CF_API_TOKEN:-}" && -n "${CF_ZONE_ID:-}" ]]; then
  info "Purging Cloudflare cache for static assets"
  curl -fsS -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/purge_cache" \
    -H "Authorization: Bearer $CF_API_TOKEN" \
    -H "Content-Type: application/json" \
    --data "{\"files\":[\"$SITE_URL/static/core/css/styles.css\"]}" >/dev/null \
    && ok "Cloudflare purged" || warn "Cloudflare purge failed (purge manually)"
else
  warn "CF_API_TOKEN/CF_ZONE_ID not set — skipping cache purge."
  warn "If CSS looks stale, purge Cloudflare for $SITE_URL/static/core/css/styles.css"
fi

# ---- verify origin -----------------------------------------------------------
info "Verifying origin serves the CSS (cache-busted)"
code=$(curl -s -k -o /dev/null -w '%{http_code}' "$SITE_URL/static/core/css/styles.css?cb=$(date +%s)")
[[ "$code" == "200" ]] && ok "origin returns 200" || warn "origin returned $code (expected 200)"

# ---- summary -----------------------------------------------------------------
echo
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo "${GREEN}${BOLD}Deploy complete.${NC}"
else
  die "Deploy finished with failures: ${FAILED[*]}"
fi
