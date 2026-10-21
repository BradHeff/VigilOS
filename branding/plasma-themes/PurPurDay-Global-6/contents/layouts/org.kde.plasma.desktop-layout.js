// VIGIL OS Default Desktop Layout
// Panel positioned at top with standard KDE Plasma widgets

var panel = new Panel
panel.location = "top"
panel.height = 2 * gridUnit
panel.floating = true
panel.alignment = "center"
panel.hiding = "none"
panel.lengthMode = "fill"

// Application launcher (Kickoff) with VIGIL OS icon
var kickoff = panel.addWidget("org.kde.plasma.kickoff")
kickoff.currentConfigGroup = ["Shortcuts"]
kickoff.writeConfig("global", "Alt+F1")
kickoff.currentConfigGroup = ["General"]
kickoff.writeConfig("icon", "vigilos-start")
kickoff.writeConfig("favoritesPortedToKAstats", true)
kickoff.writeConfig("systemFavorites", "suspend,hibernate,reboot,shutdown")

// Virtual desktop pager
panel.addWidget("org.kde.plasma.pager")

// Task manager (shows running applications)
var taskManager = panel.addWidget("org.kde.plasma.taskmanager")
taskManager.currentConfigGroup = ["General"]
taskManager.writeConfig("launchers", "")

// Spacer to push system tray to the right
panel.addWidget("org.kde.plasma.panelspacer")

// System tray (network, volume, etc.)
panel.addWidget("org.kde.plasma.systemtray")

// Digital clock
var clock = panel.addWidget("org.kde.plasma.digitalclock")
clock.currentConfigGroup = ["Appearance"]
clock.writeConfig("showDate", true)
clock.writeConfig("dateFormat", "shortDate")

// Show desktop button
panel.addWidget("org.kde.plasma.showdesktop")
