#
# bash
#

alias update="sudo dnf update -y && flatpak update -y"

#list
alias ls='ls --color=auto'
alias la='ls -a'
alias ll='ls -la'
alias l='ls'

alias vtop='vtop -t wizard'

#fix obvious typo's
alias cd..="cd .."
alias pdw="pwd"

## Colorize the grep command output for ease of use (good for log files)##
alias grep="grep --color=auto"

#readable output
alias df='df -h'

#free
alias free="free -mt"

#continue download
alias wget="wget -c"

#userlist
alias userlist="cut -d: -f1 /etc/passwd"

#merge new settings
alias merge="xrdb -merge ~/.Xresources"

#ps
alias psa="ps auxf"
alias psgrep="ps aux | grep -v grep | grep -i -e VSZ -e"

#improve png
alias fixpng="find . -type f -name "*.png" -exec convert {} -strip {} \;"

#add new fonts
alias fc="sudo fc-cache -fv"

alias clean="sudo systemd-tmpfiles --clean"

alias gpl="git pull"
alias gcl="git clone"
alias ga="git add"
alias gc="git commit -m"
alias gp="git push -u origin master"
alias gr="git rm"
alias grd="git rm -r"
alias gra="gitremote"
alias gcln="gitclone"

#hardware info --short
alias hw="hwinfo --short"

alias ~="cd ~ && source ~/.bashrc"

alias yt='youtube-dl --recode-video mp4'

#youtube-dl
alias yta-aac="youtube-dl --extract-audio --audio-format aac "
alias yta-best="youtube-dl --extract-audio --audio-format best "
alias yta-flac="youtube-dl --extract-audio --audio-format flac "
alias yta-m4a="youtube-dl --extract-audio --audio-format m4a "
alias yta-mp3="youtube-dl --extract-audio --audio-format mp3 "
alias yta-opus="youtube-dl --extract-audio --audio-format opus "
alias yta-vorbis="youtube-dl --extract-audio --audio-format vorbis "
alias yta-wav="youtube-dl --extract-audio --audio-format wav "

alias ytv-best="youtube-dl -f bestvideo+bestaudio "

alias rmd='rm -r'
alias srm='sudo rm'
alias srmd='sudo rm -r'
alias cpd='cp -R'
alias sucp='sudo cp'
alias scpd='sudo cp -R'

alias slin='sudo ln -s'
alias lin='ln -s'

#get the error messages from journalctl
alias jctl="journalctl -p 3 -xb"

#shutdown or reboot
alias ssn="sudo shutdown now"
alias sr="sudo reboot"
