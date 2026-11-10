Name: vigil-ask
Version: 0.4.0
Release: 1%{?dist}
Summary: Quick questions from the VIGIL OS desktop, answered by VIGIL GLM
License: LicenseRef-VIGIL-Personal-Build
BuildArch: noarch
BuildRequires: python3
Requires: python3
Requires: python3-pyside6
Requires: python3-gobject-base
Requires: xdg-utils
Requires: libnotify
Recommends: (wl-clipboard if plasma-workspace)

%description
VIGIL Ask answers quick questions in a window shared by the Plasma and i3
editions. Questions go to VIGIL GLM under the user's own VIGIL GLM account,
signed in from the window, and use that account's credits. VIGIL Ask asks
without web search or other tools, so it answers but cannot run commands or
change files.

%install
src=%{_sourcedir}/vigil-ask
install -Dpm0755 $src/vigil-ask %{buildroot}%{_bindir}/vigil-ask
install -d %{buildroot}%{_datadir}/vigil-ask
cp -a $src/vigil_ask $src/data %{buildroot}%{_datadir}/vigil-ask/
find %{buildroot}%{_datadir}/vigil-ask -name __pycache__ -prune -exec rm -rf {} +
/usr/bin/python3 -m compileall -q -s %{buildroot} -p / %{buildroot}%{_datadir}/vigil-ask/vigil_ask
install -Dpm0644 $src/system/org.vigilos.Ask.desktop %{buildroot}%{_datadir}/applications/org.vigilos.Ask.desktop
install -Dpm0644 $src/system/vigil-ask-sendto.desktop %{buildroot}%{_datadir}/Thunar/sendto/org.vigilos.Ask.desktop
install -Dpm0644 $src/system/vigil-ask-dolphin.desktop %{buildroot}%{_datadir}/kio/servicemenus/org.vigilos.Ask.desktop
install -Dpm0644 $src/system/vigil-ask-krunner.desktop %{buildroot}%{_datadir}/krunner/dbusplugins/org.vigilos.Ask.desktop
install -Dpm0644 $src/system/org.vigilos.Ask.KRunner.service %{buildroot}%{_datadir}/dbus-1/services/org.vigilos.Ask.KRunner.service
install -Dpm0644 $src/system/vigil-ask.1 %{buildroot}%{_mandir}/man1/vigil-ask.1
install -Dpm0644 %{_sourcedir}/org.vigilos.Ask.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/org.vigilos.Ask.svg
install -d %{buildroot}%{_sysconfdir}/vigil-ask

%files
%{_bindir}/vigil-ask
%{_datadir}/vigil-ask
%{_datadir}/applications/org.vigilos.Ask.desktop
%dir %{_datadir}/Thunar
%dir %{_datadir}/Thunar/sendto
%{_datadir}/Thunar/sendto/org.vigilos.Ask.desktop
%dir %{_datadir}/kio
%dir %{_datadir}/kio/servicemenus
%{_datadir}/kio/servicemenus/org.vigilos.Ask.desktop
%dir %{_datadir}/krunner
%dir %{_datadir}/krunner/dbusplugins
%{_datadir}/krunner/dbusplugins/org.vigilos.Ask.desktop
%{_datadir}/dbus-1/services/org.vigilos.Ask.KRunner.service
%{_datadir}/icons/hicolor/scalable/apps/org.vigilos.Ask.svg
%{_mandir}/man1/vigil-ask.1*
%dir %{_sysconfdir}/vigil-ask
