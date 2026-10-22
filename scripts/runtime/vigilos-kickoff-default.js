// SPDX-License-Identifier: GPL-3.0-only
// Theme default for newly created launchers; preserve an explicitly chosen icon.
var vigilPreviousGroup = applet.currentConfigGroup;
applet.currentConfigGroup = ["General"];
var vigilIcon = applet.readConfig("icon");
var vigilDefaults = ["", "start-here", "start-here-kde", "distributor-logo", "plasma", "vigilos-start"];
if (!vigilIcon || vigilDefaults.indexOf(vigilIcon) >= 0) {
    applet.writeConfig("icon", "vigilos-logo");
    applet.reloadConfig();
}
applet.currentConfigGroup = vigilPreviousGroup;
