#!/usr/bin/env bash
#
# validate.sh — Pre-build sanity checks for the ArxisOS source tree.
# Safe to run on the Fedora build host before ./scripts/build-iso.sh.
# Deeper checks (ksvalidator, shellcheck) activate when those tools are present.
#
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"
fail=0
ok()   { printf '\033[1;32m  PASS\033[0m %s\n' "$*"; }
bad()  { printf '\033[1;31m  FAIL\033[0m %s\n' "$*"; fail=1; }
note() { printf '\033[1;33m  SKIP\033[0m %s\n' "$*"; }

echo "== ArxisOS source validation =="

# 1. No CRLF / BOM in anything that runs or is parsed on Linux ----------------
echo "-- line endings (LF only) --"
crlf=0
while IFS= read -r -d '' f; do
  if grep -Iq . "$f" 2>/dev/null && grep -lq $'\r' "$f" 2>/dev/null; then
    bad "CRLF in $f"; crlf=1
  fi
done < <(find scripts kickstarts branding Skel -type f \
           \( -name '*.sh' -o -name '*.ks' -o -name '*.bash' -o -name '*.script' \
              -o -name '*.theme' -o -name '*.conf' -o -name '.bashrc' \) -print0 2>/dev/null)
[ "$crlf" -eq 0 ] && ok "no CRLF in scripts/kickstarts/themes"

# 2. Shebang + syntax on every shell script ----------------------------------
echo "-- shell scripts --"
while IFS= read -r -d '' s; do
  head -c3 "$s" | grep -q $'\xef\xbb\xbf' && { bad "$s has a UTF-8 BOM"; continue; }
  head -c2 "$s" | grep -q '#!' || { bad "$s missing shebang"; continue; }
  bash -n "$s" && ok "$s" || bad "$s syntax error"
done < <(find scripts -name '*.sh' -print0 2>/dev/null)

# 3. shellcheck (optional) ----------------------------------------------------
if command -v shellcheck >/dev/null 2>&1; then
  echo "-- shellcheck (warnings) --"
  find scripts -name '*.sh' -print0 | xargs -0 shellcheck -S error \
    && ok "shellcheck: no errors" || bad "shellcheck reported errors"
else
  note "shellcheck not installed"
fi

# 4. Required files present ----------------------------------------------------
echo "-- required files --"
for f in blueprints/arxisos-kde.toml kickstarts/arxisos-kde.ks \
         scripts/build-iso.sh scripts/build-and-brand.sh \
         scripts/apply-composer-branding.sh scripts/cleanup-mounts.sh \
         branding/plymouth/arxisos/arxisos.plymouth \
         branding/plymouth/arxisos/arxisos.script \
         branding/grub/arxisos/theme.txt \
         branding/grub/arxisos/background.png \
         branding/sddm/arxisos/Main.qml \
         branding/sddm/arxisos/metadata.desktop \
         branding/wallpapers/ArxisOS/metadata.json \
         branding/wallpapers/default.png \
         branding/logos/arxisos-logo.png \
         branding/logos/arxisos-watermark-128.png; do
  [ -s "$f" ] && ok "$f" || bad "$f missing or empty"
done

# 5. Identity consistency: no stray Fedora identity, codename is Loopback -----
echo "-- distro identity --"
if grep -RIl 'NAME="ArxisOS"' scripts kickstarts >/dev/null 2>&1; then
  ok "os-release sets NAME=ArxisOS"
else
  bad "os-release ArxisOS NAME not found"
fi
if grep -RIn 'usr/lib/os-release' scripts/apply-composer-branding.sh kickstarts/arxisos-kde.ks >/dev/null 2>&1; then
  ok "/usr/lib/os-release is overwritten (no Fedora leak)"
else
  bad "/usr/lib/os-release not overwritten — Fedora identity will leak"
fi
if grep -RIn 'VERSION_CODENAME=loopback' scripts kickstarts >/dev/null 2>&1; then
  ok "codename = loopback"
else
  bad "codename not set to loopback"
fi

# 6. Aurorae decoration name matches the installed theme ----------------------
echo "-- theming references --"
if grep -RIl 'PurPurDay-Aurorae-6' Skel branding/plasma-themes >/dev/null 2>&1; then
  bad "stale Aurorae name 'PurPurDay-Aurorae-6' (installed theme is PurPurDayBlur-Aurorae-6)"
else
  ok "Aurorae decoration name is consistent (PurPurDayBlur-Aurorae-6)"
fi

# 7. kickstart validation (if pykickstart present) ----------------------------
echo "-- kickstart --"
if command -v ksvalidator >/dev/null 2>&1; then
  ksvalidator kickstarts/arxisos-kde.ks && ok "kickstart valid" || bad "kickstart invalid"
else
  note "pykickstart (ksvalidator) not installed"
fi

echo
[ "$fail" -eq 0 ] && { echo -e "\033[1;32mAll checks passed.\033[0m"; exit 0; } \
                   || { echo -e "\033[1;31mValidation failed — see FAIL lines above.\033[0m"; exit 1; }
