// SPDX-License-Identifier: GPL-3.0-only
var vigilPreviousGroup = containment.currentConfigGroup;
containment.wallpaperPlugin = "org.kde.image";
containment.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
containment.writeConfig("FillMode", 1);
containment.writeConfig("Color", "#1e1e1e");
containment.reloadConfig();
containment.currentConfigGroup = vigilPreviousGroup;
