#!/usr/bin/env bash

_VIGIL_FIELDS="$(python3 "$(dirname "${BASH_SOURCE[0]}")/version.py" --fields)" || return 1
mapfile -t _VIGIL_RELEASE <<< "$_VIGIL_FIELDS"
VIGIL_VERSION="${_VIGIL_RELEASE[0]}"
VIGIL_CODENAME="${_VIGIL_RELEASE[1]}"
VIGIL_CODENAME_ID="${_VIGIL_RELEASE[2]}"
VIGIL_BUILD_ID="${_VIGIL_RELEASE[3]}"
unset _VIGIL_FIELDS _VIGIL_RELEASE
