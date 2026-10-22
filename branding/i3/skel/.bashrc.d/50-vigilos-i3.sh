case $- in *i*) ;; *) return ;; esac
HISTCONTROL=ignoreboth:erasedups
HISTSIZE=1000
HISTFILESIZE=2000
shopt -s histappend checkwinsize
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH" ;; esac
case ":$PATH:" in *":$HOME/bin:"*) ;; *) PATH="$HOME/bin:$PATH" ;; esac
export PATH
if [[ -r "$HOME/.git-prompt.bash" ]] && command -v git >/dev/null; then
    source "$HOME/.git-prompt.bash"
fi
declare -F git_prompt_precmd >/dev/null || git_prompt_precmd() { :; }
mkcd() { [[ $# == 1 ]] && mkdir -p -- "$1" && cd -- "$1"; }
extract() {
    [[ $# == 1 && -f $1 ]] || { printf 'Usage: extract FILE\n' >&2; return 1; }
    case "$1" in
        *.tar.bz2|*.tar.gz|*.tar.xz|*.tar.zst|*.tbz2|*.tgz|*.tar) tar -xf "$1" ;;
        *.zip) unzip "$1" ;;
        *.gz) gunzip -- "$1" ;;
        *.bz2) bunzip2 -- "$1" ;;
        *.7z) 7z x "$1" ;;
        *) printf 'Unsupported archive: %s\n' "$1" >&2; return 1 ;;
    esac
}
alias ls='ls --color=auto'
alias ll='ls -alF'
PS1='\[\e[32m\]\w \[\e[35m\]$(git_prompt_precmd 2>/dev/null)\[\e[0m\]\n\[\e[1;32m\]::\[\e[0m\] '
