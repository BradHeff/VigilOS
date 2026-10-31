Name: vigil-ask
Version: 0.1.0
Release: 1%{?dist}
Summary: Quick questions from the VIGIL OS desktop, answered by Claude Code
License: LicenseRef-VIGIL-Personal-Build
BuildArch: noarch
BuildRequires: python3
Requires: python3
Requires: python3-pyside6
Requires: polkit
Requires: util-linux-core
Requires: xdg-utils
Requires: libnotify

%description
VIGIL Ask answers quick questions in a window shared by the Plasma and i3
editions. It uses Claude Code by Anthropic, which is installed only when the
user chooses to, from Anthropic's signed repository. That repository ships
turned off. Claude Code runs with no tools from an empty folder, so it answers
but cannot run commands or change files. Questions are processed in the cloud
under the user's Claude account.

%install
src=%{_sourcedir}/vigil-ask
install -Dpm0755 $src/vigil-ask %{buildroot}%{_bindir}/vigil-ask
install -d %{buildroot}%{_datadir}/vigil-ask
cp -a $src/vigil_ask $src/data %{buildroot}%{_datadir}/vigil-ask/
find %{buildroot}%{_datadir}/vigil-ask -name __pycache__ -prune -exec rm -rf {} +
/usr/bin/python3 -m compileall -q -s %{buildroot} -p / %{buildroot}%{_datadir}/vigil-ask/vigil_ask
install -Dpm0755 $src/system/install-claude-code %{buildroot}%{_libexecdir}/vigil-ask/install-claude-code
install -Dpm0644 $src/system/org.vigilos.Ask.desktop %{buildroot}%{_datadir}/applications/org.vigilos.Ask.desktop
install -Dpm0644 $src/system/vigil-ask-sendto.desktop %{buildroot}%{_datadir}/Thunar/sendto/org.vigilos.Ask.desktop
install -Dpm0644 $src/system/org.vigilos.ask.policy %{buildroot}%{_datadir}/polkit-1/actions/org.vigilos.ask.policy
install -Dpm0644 $src/system/vigil-ask.1 %{buildroot}%{_mandir}/man1/vigil-ask.1
install -Dpm0644 %{_sourcedir}/org.vigilos.Ask.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/org.vigilos.Ask.svg
install -Dpm0644 %{_sourcedir}/claude-code.repo %{buildroot}%{_sysconfdir}/yum.repos.d/claude-code.repo
install -Dpm0644 %{_sourcedir}/claude-code.asc %{buildroot}%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-claude-code
install -d %{buildroot}%{_sysconfdir}/vigil-ask

%files
%{_bindir}/vigil-ask
%{_datadir}/vigil-ask
%{_libexecdir}/vigil-ask
%{_datadir}/applications/org.vigilos.Ask.desktop
%dir %{_datadir}/Thunar
%dir %{_datadir}/Thunar/sendto
%{_datadir}/Thunar/sendto/org.vigilos.Ask.desktop
%{_datadir}/polkit-1/actions/org.vigilos.ask.policy
%{_datadir}/icons/hicolor/scalable/apps/org.vigilos.Ask.svg
%{_mandir}/man1/vigil-ask.1*
%dir %{_sysconfdir}/vigil-ask
%config(noreplace) %{_sysconfdir}/yum.repos.d/claude-code.repo
%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-claude-code
