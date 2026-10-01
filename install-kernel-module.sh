#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="https://github.com/0x7375646F/Linuwu-Sense.git"
REF="${LINUWU_SENSE_REF:-main}"
KERNEL_RELEASE="$(uname -r)"
FAN_ATTRIBUTE="/sys/devices/platform/acer-wmi/predator_sense/fan_speed"
PROFILE_ATTRIBUTE="/sys/devices/platform/acer-wmi/platform-profile/platform-profile-0/profile"

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this script as your normal user, without sudo. It invokes sudo only for privileged install steps." >&2
    exit 2
fi

if [ -e "$FAN_ATTRIBUTE" ] && [ -e "$PROFILE_ATTRIBUTE" ]; then
    echo "Linuwu-Sense profile interface is already present; skipping kernel-module replacement."
    exit 0
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This helper currently supports Kali, Debian, and Ubuntu (apt-based systems)." >&2
    exit 2
fi

echo "This installs the third-party Linuwu-Sense kernel module for $KERNEL_RELEASE."
echo "The upstream installer unloads and blacklists acer_wmi before loading Linuwu-Sense."
echo "Review the upstream project and confirm this laptop model is supported before continuing."
read -r -p "Continue with the kernel-module installation? [y/N] " answer
case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "Cancelled."; exit 1 ;;
esac

sudo apt-get update
sudo apt-get install -y git build-essential mokutil

if [ ! -f "/lib/modules/$KERNEL_RELEASE/build/Makefile" ]; then
    if ! sudo apt-get install -y "linux-headers-$KERNEL_RELEASE"; then
        echo "Could not install headers for $KERNEL_RELEASE from the configured apt repositories." >&2
        exit 1
    fi
fi

if [ ! -f "/lib/modules/$KERNEL_RELEASE/build/Makefile" ]; then
    echo "Matching kernel headers for $KERNEL_RELEASE are unavailable." >&2
    echo "Install headers matching the running kernel, reboot into that kernel, then retry." >&2
    exit 1
fi

if command -v mokutil >/dev/null 2>&1 && mokutil --sb-state 2>/dev/null | grep -qi 'SecureBoot enabled'; then
    echo "Secure Boot is enabled. This automated installer stops before changing drivers." >&2
    echo "Disable Secure Boot in firmware to use this option, or manually build/sign/enroll the module using the upstream module_signing_readme." >&2
    exit 1
fi

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/linuwu-sense-build.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

git clone --depth 1 --branch "$REF" "$REPOSITORY" "$WORKDIR/Linuwu-Sense"
make -C "$WORKDIR/Linuwu-Sense" install

if [ ! -e "$FAN_ATTRIBUTE" ] || [ ! -e "$PROFILE_ATTRIBUTE" ]; then
    echo "The module build finished, but the expected Predator profile interface was not found." >&2
    echo "Check this model's compatibility and the upstream module log before installing the GUI." >&2
    exit 1
fi

echo "Linuwu-Sense is installed and the profile interface is available."
