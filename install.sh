#!/bin/bash
set -e
D="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -gt 1 ]; then
    echo "Usage: $0 [--with-kernel-module]" >&2
    exit 2
fi
case "${1:-}" in
    "") ;;
    --with-kernel-module) "$D/install-kernel-module.sh" ;;
    *)
        echo "Usage: $0 [--with-kernel-module]" >&2
        exit 2
        ;;
esac
sudo mkdir -p /opt/predsenselinux
sudo cp "$D/predsenselinux.py" "$D/predsenselinux-launch.sh" /opt/predsenselinux/
sudo chmod +x /opt/predsenselinux/predsenselinux.py /opt/predsenselinux/predsenselinux-launch.sh
sudo cp "$D/predsenselinux.desktop" /usr/share/applications/
sudo install -d -o root -g root -m 0755 /usr/local/lib/predsenselinux-profile-helper
sudo install -o root -g root -m 0755 "$D/predsenselinux_profile_helper.py" /usr/local/lib/predsenselinux-profile-helper/predsenselinux_profile_helper.py
GROUP_GID="$(getent group linuwu_sense | cut -d: -f3)"
if [ -z "$GROUP_GID" ]; then
    sudo groupadd --system linuwu_sense
    GROUP_GID="$(getent group linuwu_sense | cut -d: -f3)"
fi
TARGET_USER="${SUDO_USER:-$(id -un)}"
sudo usermod -aG linuwu_sense "$TARGET_USER"
printf 'LINUWU_GROUP_GID=%s\n' "$GROUP_GID" | sudo tee /etc/default/predsenselinux-profile-helper >/dev/null
sudo chown root:root /etc/default/predsenselinux-profile-helper
sudo chmod 0644 /etc/default/predsenselinux-profile-helper
sudo install -o root -g root -m 0644 "$D/predsenselinux-profile-helper.service" /etc/systemd/system/predsenselinux-profile-helper.service
sudo systemctl daemon-reload
sudo systemctl enable --now predsenselinux-profile-helper.service
echo "Installed. Open 'PredSenseLinux' from the application menu."
