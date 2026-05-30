#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# ArxisOS — boot the built ISO in a UEFI QEMU/KVM VM for testing.
# Secure Boot is OFF (plain OVMF_CODE.fd) per the first-run guidance.
# Usage: ./scripts/test-vm.sh [path-to-iso]
#   defaults to ./ArxisOS-1.0-x86_64.iso
# ------------------------------------------------------------

ISO="${1:-$(dirname "$0")/../ArxisOS-1.0-x86_64.iso}"
[[ -f "$ISO" ]] || { echo "ERROR: ISO not found: $ISO" >&2; exit 1; }

command -v qemu-system-x86_64 >/dev/null \
  || { echo "ERROR: qemu-system-x86_64 missing (sudo dnf install qemu-system-x86)" >&2; exit 1; }

# Locate OVMF firmware (non-secureboot CODE + VARS template).
CODE=""
for c in \
  /usr/share/edk2/ovmf/OVMF_CODE.fd \
  /usr/share/OVMF/OVMF_CODE.fd \
  /usr/share/edk2/ovmf/OVMF_CODE_4M.fd; do
  [[ -f "$c" ]] && { CODE="$c"; break; }
done
VARS_SRC=""
for v in \
  /usr/share/edk2/ovmf/OVMF_VARS.fd \
  /usr/share/OVMF/OVMF_VARS.fd \
  /usr/share/edk2/ovmf/OVMF_VARS_4M.fd; do
  [[ -f "$v" ]] && { VARS_SRC="$v"; break; }
done

KVM=()
[[ -e /dev/kvm ]] && KVM=(-enable-kvm -cpu host)

echo "ISO : $ISO"
echo "KVM : ${KVM[*]:-(none — software emulation, slow)}"

if [[ -n "$CODE" && -n "$VARS_SRC" ]]; then
  # Modern split firmware: needs a writable per-VM VARS copy via pflash.
  VARS="$(mktemp --suffix=-arxisos-OVMF_VARS.fd)"
  trap 'rm -f "$VARS"' EXIT
  cp "$VARS_SRC" "$VARS"
  echo "UEFI: $CODE (+ writable vars)"
  exec qemu-system-x86_64 \
    -m 4096 -smp 4 "${KVM[@]}" \
    -machine q35 \
    -drive if=pflash,format=raw,unit=0,readonly=on,file="$CODE" \
    -drive if=pflash,format=raw,unit=1,file="$VARS" \
    -cdrom "$ISO" \
    -vga virtio -display gtk
else
  echo "WARNING: OVMF firmware not found — falling back to legacy BIOS boot." >&2
  echo "         (install edk2-ovmf to test the real UEFI/GRUB path)" >&2
  exec qemu-system-x86_64 \
    -m 4096 -smp 4 "${KVM[@]}" \
    -cdrom "$ISO" \
    -vga virtio -display gtk
fi
