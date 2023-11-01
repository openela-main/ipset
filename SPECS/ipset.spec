# service legacy actions
%define legacy_actions %{_libexecdir}/initscripts/legacy-actions

Name:             ipset
Version:          7.1
Release:          1%{?dist}
Summary:          Manage Linux IP sets

License:          GPLv2
URL:              http://ipset.netfilter.org/
Source0:          http://ipset.netfilter.org/%{name}-%{version}.tar.bz2
Source1:          %{name}.service
Source2:          %{name}.start-stop
Source3:          %{name}-config
Source4:          %{name}.save-legacy

BuildRequires:    libmnl-devel

# An explicit requirement is needed here, to avoid cases where a user would
# explicitly update only one of the two (e.g 'yum update ipset')
Requires:         %{name}-libs%{?_isa} = %{version}-%{release}

%description
IP sets are a framework inside the Linux kernel since version 2.4.x, which can
be administered by the ipset utility. Depending on the type, currently an IP
set may store IP addresses, (TCP/UDP) port numbers or IP addresses with MAC
addresses in a way, which ensures lightning speed when matching an entry
against a set.

If you want to:
 - store multiple IP addresses or port numbers and match against the collection
   by iptables at one swoop;
 - dynamically update iptables rules against IP addresses or ports without
   performance penalty;
 - express complex IP address and ports based rulesets with one single iptables
   rule and benefit from the speed of IP sets
then ipset may be the proper tool for you.


%package libs
Summary:       Shared library providing the IP sets functionality

%description libs
This package contains the libraries which provide the IP sets funcionality.


%package devel
Summary:       Development files for %{name}
Requires:      %{name}-libs%{?_isa} == %{version}-%{release}

%description devel
This package contains the files required to develop software using the %{name}
libraries.


%package service
Summary:          %{name} service for %{name}s
Requires:         %{name} = %{version}-%{release}
BuildRequires:    systemd
Requires:         iptables-services
Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd
BuildArch:        noarch

%description service
This package provides the service %{name} that is split
out of the base package since it is not active by default.


%prep
%setup -q


%build
%configure --enable-static=no --with-kmod=no

# Just to make absolutely sure we are not building the bundled kernel module
# I have to do it after the configure run unfortunately
rm -fr kernel

# Prevent libtool from defining rpath
sed -i 's|^hardcode_libdir_flag_spec=.*|hardcode_libdir_flag_spec=""|g' libtool
sed -i 's|^runpath_var=LD_RUN_PATH|runpath_var=DIE_RPATH_DIE|g' libtool

make %{?_smp_mflags}


%install
make install DESTDIR=%{buildroot}
find %{buildroot} -name '*.la' -exec rm -f '{}' \;

# install systemd unit file
install -d -m 755 %{buildroot}/%{_unitdir}
install -c -m 644 %{SOURCE1} %{buildroot}/%{_unitdir}

# install supporting script
install -d -m 755 %{buildroot}%{_libexecdir}/%{name}
install -c -m 755 %{SOURCE2} %{buildroot}%{_libexecdir}/%{name}

# install ipset-config
install -d -m 755 %{buildroot}%{_sysconfdir}/sysconfig
install -c -m 600 %{SOURCE3} %{buildroot}%{_sysconfdir}/sysconfig/%{name}-config

# install legacy actions for service command
install -d %{buildroot}/%{legacy_actions}/ipset
install -c -m 755 %{SOURCE4} %{buildroot}/%{legacy_actions}/ipset/save

# Create directory for configuration
mkdir -p %{buildroot}%{_sysconfdir}/%{name}


%preun
if [[ $1 -eq 0 && -n $(lsmod | grep "^xt_set ") ]]; then
    rmmod xt_set 2>/dev/null
    [[ $? -ne 0 ]] && echo Current iptables configuration requires ipsets && exit 1
fi


%post libs -p /sbin/ldconfig

%postun libs -p /sbin/ldconfig


%post service
%systemd_post %{name}.service

%preun service
if [[ $1 -eq 0 && -n $(lsmod | grep "^xt_set ") ]]; then
    rmmod xt_set 2>/dev/null
    [[ $? -ne 0 ]] && echo Current iptables configuration requires ipsets && exit 1
fi
%systemd_preun %{name}.service

%postun service
%systemd_postun_with_restart %{name}.service

%triggerin service -- ipset-service < 6.38-1.el7
# Before 6.38-1, ipset.start-stop keeps a backup of previously saved sets, but
# doesn't touch the /etc/sysconfig/ipset.d/.saved flag. Remove the backup on
# upgrade, so that we use the current version of saved sets
rm -f /etc/sysconfig/ipset.save || :
exit 0

%triggerun service -- ipset-service < 6.38-1.el7
# Up to 6.29-1, ipset.start-stop uses a single data file
for f in /etc/sysconfig/ipset.d/*; do
    [ "${f}" = "/etc/sysconfig/ipset.d/*" ] && break
    cat ${f} >> /etc/sysconfig/ipset || :
done
exit 0

%files
%doc COPYING ChangeLog
%doc %{_mandir}/man8/%{name}.8.gz
%{_sbindir}/%{name}

%files libs
%doc COPYING
%{_libdir}/lib%{name}.so.13*
%doc %{_mandir}/man3/lib%{name}.3.gz

%files devel
%{_includedir}/lib%{name}
%{_libdir}/lib%{name}.so
%{_libdir}/pkgconfig/lib%{name}.pc

%files service
%{_unitdir}/%{name}.service
%dir %{_libexecdir}/%{name}
%config(noreplace) %attr(0600,root,root) %{_sysconfdir}/sysconfig/ipset-config
%ghost %config(noreplace) %attr(0600,root,root) %{_sysconfdir}/sysconfig/ipset
%attr(0755,root,root) %{_libexecdir}/%{name}/%{name}.start-stop
%dir %{legacy_actions}/ipset
%{legacy_actions}/ipset/save


%changelog
* Sun May 26 2019 Stefano Brivio <sbrivio@redhat.com> - 7.1-1
- Rebase to 7.1 (RHBZ#1649090):
  - Add compatibility support for strscpy()
  - Correct the manpage about the sort option
  - Add missing functions to libipset.map
  - configure.ac: Fix build regression on RHEL/CentOS/SL (Serhey Popovych)
  - Implement sorting for hash types in the ipset tool
  - Fix to list/save into file specified by option (reported by Isaac Good)
  - Introduction of new commands and protocol version 7, updated kernel include files
  - Add compatibility support for async in pernet_operations
  - Use more robust awk patterns to check for backward compatibility
  - Prepare the ipset tool to handle multiple protocol version
  - Fix warning message handlin
  - Correct to test null valued entry in hash:net6,port,net6 test
  - Library reworked to support embedding ipset completely
  - Add compatibility to support kvcalloc()
  - Validate string type attributes in attr2data() (Stefano Brivio)
  - manpage: Add comment about matching on destination MAC address (Stefano Brivio)
    (RHBZ#1649079)
  - Add compatibility to support is_zero_ether_addr()
  - Fix use-after-free in ipset_parse_name_compat() (Stefano Brivio) (RHBZ#1649085)
  - Fix leak in build_argv() on line parsing error (Stefano Brivio) (RHBZ#1649085)
  - Simplify return statement in ipset_mnl_query() (Stefano Brivio) (RHBZ#1649085)
  - tests/check_klog.sh: Try dmesg too, don't let shell terminate script (Stefano Brivio) 
- Fixes:
  - Fix all shellcheck warnings in init script (RHBZ#1649085)
  - Make error reporting consistent, introduce different severities (RHBZ#1683711)
  - While restoring, on invalid entries, remove them and retry (RHBZ#1683713)
  - Fix covscan SC2166 warning in init script (RHBZ#1649085)

* Tue Nov 13 2018 Stefano Brivio <sbrivio@redhat.com> - 6.38-3
- Fix loading of sets with dependencies on other sets (RHBZ#1647096), and
  hardcode 6.38-1.el7 for ipset-service upgrade and downgrade triggers, so that
  we don't run into issues with z-stream updates

* Mon Oct 08 2018 Stefano Brivio <sbrivio@redhat.com> - 6.38-2
- Drop ipset-devel dependency on kernel-devel (RHBZ#163175)

* Tue Aug 14 2018 Stefano Brivio <sbrivio@redhat.com> - 6.38-1
- Update to 6.38, source from RHEL7 6.38-2 (RHBZ#1615967)

* Mon Feb 12 2018 Eric Garver <egarver@redhat.com> - 6.35-3
- Patch for missing header file (RHBZ#1543596)

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 6.35-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Mon Jan 08 2018 Nicolas Chauvet <kwizart@gmail.com> - 6.35-1
- Update to 6.35

* Mon Jul 31 2017 Nicolas Chauvet <kwizart@gmail.com> - 6.32-1
- Update to 6.32

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 6.29-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Apr 07 2017 Nicolas Chauvet <kwizart@gmail.com> - 6.29-3
- Userspace needs kernel-headers - rhbz#1420864

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 6.29-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Apr 18 2016 Thomas Woerner <twoerner@redhat.com> - 6.29-1
- New upstream version 6.29 (RHBZ#1317208)
  - Suppress unnecessary stderr in command loop for resize and list
  - Correction in comment test
  - Support chroot buildroots (reported by Jan Engelhardt)
  - Fix "configure" breakage due to pkg-config related changes
    (reported by Jan Engelhardt)
  - Support older pkg-config packages
  - Add bash completion to the install routine (Mart Frauenlob)
  - Fix misleading error message with comment extension
  - Test added to check 0.0.0.0/0,iface to be matched in hash:net,iface type
  - Fix link with libtool >= 2.4.4 (Olivier Blin)

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 6.27-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Nov 10 2015 Thomas Woerner <twoerner@redhat.com> - 6.27-1
- New upstream version 6.27 (RHBZ#1145913)

* Sat Oct 10 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 6.26-1
- Upstream 6.26 (RHBZ#1145913)

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.22-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Sep 18 2014 Mathieu Bridon <bochecha@fedoraproject.org> - 6.22-1
- New upstream release.

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.21.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.21.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue Mar 11 2014 Mathieu Bridon <bochecha@fedoraproject.org> - 6.21.1-2
- Remove runtime requirement on the kernel.
  https://lists.fedoraproject.org/pipermail/devel/2014-March/196565.html

* Tue Oct 29 2013 Mathieu Bridon <bochecha@fedoraproject.org> - 6.20.1-1
- New upstream release.

* Tue Aug 27 2013 Quentin Armitage <quentin@armitage.org.uk> 6.19-2
- Add service pkg - adds save and reload functionality on shutdown/startup
- Add requires dependency of ipset on matching ipset-libs

* Thu Aug 15 2013 Mathieu Bridon <bochecha@fedoraproject.org> - 6.19-1
- New upstream release.

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.16.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.16.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Wed Sep 26 2012 Mathieu Bridon <bochecha@fedoraproject.org> - 6.16.1-1
- New upstream release.
- Fix a requirement.

* Wed Sep 26 2012 Mathieu Bridon <bochecha@fedoraproject.org> - 6.14-1
- New upstream release.
- Fix scriptlets, ldconfig is needed for the libs subpackage, not the main one.

* Mon Jul 30 2012 Mathieu Bridon <bochecha@fedoraproject.org> - 6.13-1
- New upstream release.
- Split out the library in its own subpackage.

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.11-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Feb 06 2012 Mathieu Bridon <bochecha@fedoraproject.org> - 6.11-1
- New upstream release.
- Removed our patch, it has been integrated upstream. As such, we also don't
  need to re-run autoreconf any more.

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 6.9.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Sep 16 2011 Mathieu Bridon <bochecha@fedoraproject.org> - 6.9.1-2
- Some fixes based on Pierre-Yves' review feedback.

* Wed Sep 14 2011 Mathieu Bridon <bochecha@fedoraproject.org> - 6.9.1-1
- Initial packaging.
