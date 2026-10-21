# Product-only post-install setup. Anaconda runs this inside the installed target.
%post --erroronfail --log=/var/log/vigilos-installer-post.log
/usr/local/libexec/vigilos-configure-installed-boot
%end
