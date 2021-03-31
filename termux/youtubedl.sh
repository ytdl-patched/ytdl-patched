#!/system/bin/sh
# shellcheck disable=SC2034,SC2039

# Colors
# ----------------------------------------
BL='\e[01;90m' > /dev/null 2>&1; # Black
R='\e[01;91m' > /dev/null 2>&1; # Red
G='\e[01;92m' > /dev/null 2>&1; # Green
Y='\e[01;93m' > /dev/null 2>&1; # Yellow
B='\e[01;94m' > /dev/null 2>&1; # Blue
P='\e[01;95m' > /dev/null 2>&1; # Purple
C='\e[01;96m' > /dev/null 2>&1; # Cyan
W='\e[01;97m' > /dev/null 2>&1; # White
LG='\e[01;37m' > /dev/null 2>&1; # Light Gray
N='\e[0m' > /dev/null 2>&1; # Null
L='\033[7m' > /dev/null 2>&1; #Lines
X='\033[0m' > /dev/null 2>&1; #Closer
# ----------------------------------------

apt update -y
clear


# see https://ideone.com/OxtAVZ
echo -e "$R"'        _      _ _                    _       _              _ '"$N"
sleep 0.3
echo -e "$R"'       | |    | | |                  | |     | |            | |'"$N"
sleep 0.3
echo -e "$R"'  _   _| |_ __| | |______ _ __   __ _| |_ ___| |__   ___  __| |'"$N"
sleep 0.3
echo -e "$R"' | | | | __/ _` | |______| '\''_ \ / _` | __/ __| '\''_ \ / _ \/ _` |'"$N"
sleep 0.3
echo -e "$R"' | |_| | || (_| | |      | |_) | (_| | || (__| | | |  __/ (_| |'"$N"
sleep 0.3
echo -e "$R"'  \__, |\__\__,_|_|      | .__/ \__,_|\__\___|_| |_|\___|\__,_|'"$N"
sleep 0.3
echo -e "$R"'   __/ |                 | |                                   '"$N"
sleep 0.3
echo -e "$R"'  |___/                  |_|                                   '"$N"
sleep 0.3

sleep 1.5

echo -e "$Y" "$L""ytdl-patched Installer by"  "$R" "nao20010128nao" "$N"

echo -e "$Y" "$L""Please accept permission access..." "$N"
termux-setup-storage

echo -e "$Y" "$L""Installing packages..." "$N"
apt install -y python ffmpeg wget

echo -e "$Y" "$L" "Creating bin folder..." "$N"
mkdir ~/bin

echo -e "$Y" "$L""Installing ytdl-patched..." "$N" 
wget https://github.com/nao20010128nao/ytdl-patched/releases/download/1617160331/youtube-dl -O /data/data/com.termux/files/home/bin/ytdl-patched
chmod a+x /data/data/com.termux/files/home/bin/ytdl-patched
/data/data/com.termux/files/home/bin/ytdl-patched -U

echo -e "$Y" "$L""Setting up configs..." "$N"

echo -e "$Y" "$L" "Creating Youtube folder..." "$N"
mkdir /data/data/com.termux/files/home/storage/shared/Youtube

echo -e "$Y" "$L" "Creating youtube-dl config..." "$N"
mkdir -p ~/.config/youtube-dl

echo -e "$Y" "$L" "Getting config file..." "$N"
wget https://raw.githubusercontent.com/nao20010128nao/ytdl-patched/master/termux/config -P /data/data/com.termux/files/home/.config/youtube-dl

echo -e "$Y" "$L" "Getting files..." "$N"
wget https://raw.githubusercontent.com/nao20010128nao/ytdl-patched/master/termux/termux-url-opener -P /data/data/com.termux/files/home/bin

echo -e "$G""Installation finished..." "$N"

kill -1 $PPID
