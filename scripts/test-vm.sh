#!/usr/bin/env bash
set -euo pipefail
umask 077
# Run only after explicit VM approval. No host devices, shares or credentials.
[[ "${VIGIL_EXECUTION_APPROVED:-0}" == 1 ]] || { echo 'ERROR: Execution approval is required.' >&2; exit 1; }
MODE="${1:-}"
NAME="${2:-}"
ISO="${3:-}"
[[ "$MODE" == live || "$MODE" == installed ]] || { echo 'Usage: test-vm.sh live|installed builder|vigil|baseline [iso]' >&2; exit 1; }
case "$NAME" in
    builder) RAM=6144; DISK_GIB=104 ;;
    vigil) RAM=6144; DISK_GIB=48 ;;
    baseline) RAM=6144; DISK_GIB=40 ;;
    *) echo 'ERROR: VM name must be builder, vigil or baseline.' >&2; exit 1 ;;
esac
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_ROOT="$(realpath -m "${VIGIL_TEST_ROOT:-$REPO_DIR/.build/test}")"
VM_ROOT="$LAB_ROOT/vm"
mkdir -p "$VM_ROOT"
# Only one VM is active: max 6 GiB RAM, max aggregate disk capacity 192 GiB.
exec 9>"$VM_ROOT/active.lock"
flock -n 9 || { echo 'ERROR: Another lab VM is active.' >&2; exit 1; }
DISK="$VM_ROOT/$NAME.qcow2"
VARS="$VM_ROOT/$NAME-OVMF_VARS.fd"
OWNERSHIP="$VM_ROOT/$NAME.disposable"
CODE=/usr/share/edk2/ovmf/OVMF_CODE.fd
VARS_SOURCE=/usr/share/edk2/ovmf/OVMF_VARS.fd
[[ -r "$CODE" && -r "$VARS_SOURCE" ]] || { echo 'ERROR: Split OVMF firmware is required.' >&2; exit 1; }
if [[ "$MODE" == live ]]; then
    ISO="$(realpath "$ISO")"
    [[ -f "$ISO" && "$ISO" == *.iso ]] || { echo 'ERROR: A regular ISO file is required.' >&2; exit 1; }
fi
if [[ ! -e "$DISK" ]]; then
    [[ "$MODE" == live && ! -e "$OWNERSHIP" && ! -e "$VARS" ]] || { echo 'ERROR: Inconsistent state; refusing to replace files.' >&2; exit 1; }
    qemu-img create -f qcow2 "$DISK" "${DISK_GIB}G"
    cp "$VARS_SOURCE" "$VARS"
    printf '%s\n' "$NAME:$DISK_GIB:$LAB_ROOT" > "$OWNERSHIP"
fi
[[ -f "$DISK" && ! -L "$DISK" && -f "$VARS" && ! -L "$VARS" && -f "$OWNERSHIP" ]] || { echo 'ERROR: VM state must consist of owned regular files.' >&2; exit 1; }
[[ "$(cat "$OWNERSHIP")" == "$NAME:$DISK_GIB:$LAB_ROOT" ]] || { echo 'ERROR: VM ownership mismatch.' >&2; exit 1; }
#4GiB is the explicit low-memory stress configuration; normal comparison uses6GiB.
RAM="${VIGIL_RAM_MIB:-$RAM}"
[[ "$RAM" == 4096 || "$RAM" == 6144 ]] || { echo 'ERROR: Lab RAM must be4GiB or6GiB.' >&2; exit 1; }
DISPLAY_MODE="${VIGIL_DISPLAY_MODE:-1280x800}"
case "$DISPLAY_MODE" in
    1024x768|1280x720|1280x800|1920x1080|2560x1440|1920x1200|3840x2160) ;;
    *) echo 'ERROR: Unsupported lab display mode.' >&2; exit 1 ;;
esac
DISPLAY_WIDTH="${DISPLAY_MODE%x*}"
DISPLAY_HEIGHT="${DISPLAY_MODE#*x}"
FIRMWARE="${VIGIL_FIRMWARE:-uefi}"
FW_ARGS=()
case "$FIRMWARE" in
    uefi) FW_ARGS=(-drive "if=pflash,format=raw,unit=0,readonly=on,file=$CODE" -drive "if=pflash,format=raw,unit=1,file=$VARS") ;;
    bios) ;;
    *) echo "ERROR: Firmware must be uefi or bios." >&2; exit 1 ;;
esac
MEDIA=()
[[ "$MODE" != live ]] || MEDIA=(-boot once=d,menu=on -drive "file=$ISO,media=cdrom,readonly=on,format=raw")
NETWORK=(-nic none)
if [[ "${VIGIL_ALLOW_NETWORK:-0}" == 1 ]]; then
    NETWORK=(-nic user,model=virtio-net-pci,ipv6=off)
fi
ACCEL=(-accel tcg,thread=multi -cpu max)
ACCEL_NAME=TCG
if [[ -r /dev/kvm && -w /dev/kvm ]]; then ACCEL=(-accel kvm -cpu host); ACCEL_NAME=KVM; fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE="$LAB_ROOT/evidence/$NAME-$STAMP"
mkdir -p "$EVIDENCE"
printf 'VM=%s\nMode=%s\nAcceleration=%s\nRAM_MiB=%s\nDisk_GiB=%s\nISO=%s\nFirmware=%s\nDisplay=%s\n' "$NAME" "$MODE" "$ACCEL_NAME" "$RAM" "$DISK_GIB" "$ISO" "$FIRMWARE" "$DISPLAY_MODE" > "$EVIDENCE/run.txt"
qemu-system-x86_64 \
    -name "vigil-lab-$NAME" -machine q35 "${ACCEL[@]}" -smp 4 -m "$RAM" \
    "${FW_ARGS[@]}" \
    -drive "file=$DISK,if=virtio,format=qcow2" "${MEDIA[@]}" "${NETWORK[@]}" \
    -device qemu-xhci -device usb-tablet -vga none -device "virtio-vga,xres=$DISPLAY_WIDTH,yres=$DISPLAY_HEIGHT" -display none -vnc "unix:$VM_ROOT/$NAME-vnc.sock" \
    -qmp "unix:$VM_ROOT/$NAME-qmp.sock,server=on,wait=off" \
    -chardev "socket,id=serial0,path=$VM_ROOT/$NAME-serial.sock,server=on,wait=off,logfile=$EVIDENCE/serial.log" -serial chardev:serial0 -monitor none \
    2>"$EVIDENCE/qemu.log"
