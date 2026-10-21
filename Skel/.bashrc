# .bashrc

# If not running interactively, don't do anything.
[[ $- != *i* ]] && return

# Git prompt support is optional in a fresh account.
if [[ -r "$HOME/.git-prompt.bash" ]]; then
    . "$HOME/.git-prompt.bash"
fi

precmd() {
    if declare -F git_prompt_precmd >/dev/null; then
        git_prompt_precmd
    fi
}

export HISTCONTROL=ignoreboth:erasedups


set +f

SELECT(){
  if [ "$?" -eq 0 ]
    then
    echo ""
  else
    echo "[X] "
fi
}

COLOR_BLACK="\[$(tput setaf 0)\]"
COLOR_RED="\[$(tput setaf 1)\]"
COLOR_GREEN="\[$(tput setaf 2)\]"
COLOR_YELLOW="\[$(tput setaf 3)\]"
COLOR_BLUE="\[$(tput setaf 4)\]"
COLOR_PURPLE="\[$(tput setaf 5)\]"
COLOR_CYAN="\[$(tput setaf 6)\]"
COLOR_WHITE="\[$(tput setaf 7)\]"
COLOR_BLUE="\[$(tput setaf 8)\]"
COLOR_RESET="\[$(tput sgr0)\]"
COLOR_BOLD="\[$(tput bold)\]"


#PS1="${COLOR_RED}\$(SELECT)${COLOR_RESET}\\h ${COLOR_YELLOW}${COLOR_BOLD}::${COLOR_RESET} ${COLOR_GREEN}\\w ${COLOR_PURPLE}\$(precmd) ${COLOR_B}${COLOR_BOLD}>>${COLOR_RESET} "
PS1="${COLOR_RED}\$(SELECT)${COLOR_GREEN}\\w ${COLOR_PURPLE}\$(precmd)${COLOR_RESET}
${COLOR_GREEN}${COLOR_BOLD}::${COLOR_RESET} "

# Source global definitions
if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi
if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# User specific environment
# if ! [[ "$PATH" =~ "$HOME/.local/bin:$HOME/bin:" ]]; then
#    PATH="$HOME/.local/bin:$HOME/bin:$PATH"
# fi
if ! [[ "$PATH" =~ "$HOME/.local/bin:$HOME/bin:/snap/bin:" ]]; then
    PATH="$HOME/.local/bin:$HOME/bin:/snap/bin:$PATH"
fi

if ! [[ "$XDG_DATA_DIRS" =~ "/var/lib/snapd/desktop/" ]]; then
    XDG_DATA_DIRS="$XDG_DATA_DIRS:/var/lib/snapd/desktop/"
fi
export PATH
export XDG_DATA_DIRS
# Qt theming: KDE Plasma 6 (Qt6) sets the platform theme itself. Forcing qt5ct
# (not installed) breaks Qt6 application styling, so leave it unset.
# export QT_QPA_PLATFORMTHEME=qt5ct
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Uncomment the following line if you don't like systemctl's auto-paging feature:
# export SYSTEMD_PAGER=

#shopt
shopt -s checkwinsize
shopt -s autocd # change to named directory
shopt -s cdspell # autocorrects cd misspellings
shopt -s cmdhist # save multi-line commands in history as single line
shopt -s dotglob
shopt -s histappend # do not overwrite history
shopt -s expand_aliases # expand aliases

# User specific aliases and functions
if [ -d ~/.bashrc.d ]; then
    for rc in ~/.bashrc.d/*; do
        if [ -f "$rc" ]; then
            . "$rc"
        fi
    done
fi
[[ "${VIGIL_FETCH_ON_START:-0}" != 1 ]] || hfetch
export EDITOR=vim
export VISUAL=vim
unset rc
