#!/usr/bin/env bash

vigilos_require_builder() {
    if [[ "${VIGIL_BUILD_GUEST:-0}" != 1 || ! -f /etc/vigilos-disposable-builder ]]; then
        echo 'ERROR: Run only in the approved disposable builder VM.' >&2
        return 1
    fi
    if ! systemd-detect-virt --vm --quiet; then
        echo 'ERROR: A virtual machine is required; host execution is refused.' >&2
        return 1
    fi
}
