// SPDX-License-Identifier: GPL-3.0-only
// Native look-and-feel setup hook: apply only when a desktop is created.
// Plasma assigns activity-specific containment IDs on first boot, so a fixed
// skeleton containment cannot supply defaults for the actual desktop.
var vigilPreviousGroup = containment.currentConfigGroup;
containment.wallpaperPlugin = "org.kde.image";
containment.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
containment.writeConfig("FillMode", 1);
containment.writeConfig("Color", "#1e1e1e");
containment.reloadConfig();
containment.currentConfigGroup = vigilPreviousGroup;
