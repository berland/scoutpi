#!/bin/bash
set -euo pipefail

CPU_USAGE=$(awk -v FS=" " '
  /cpu / {
    usage=($2+$4)*100/($2+$4+$5)
    printf "%.2f", usage
  }' /proc/stat)

MEM_TOTAL=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
MEM_AVAILABLE=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
MEM_USED=$((MEM_TOTAL - MEM_AVAILABLE))
WIFI_SSID=$(iwgetid -r)
CPU_TEMP=$(awk '{print $1/1000}' /sys/class/thermal/thermal_zone0/temp)
THROTTLING_STATE=$(vcgencmd get_throttled | cut -f2 -d=)
IP_ADDRESS=$(hostname -I | awk '{print $1}')
SYSTEMCTL_FAILED=$(systemctl --failed --no-legend | tr '\n' '|')
PINGTIME=$(nmap -p 443 -Pn raaserv.no | grep -oP '\d+\.\d+(?=s latency)' | awk '{print $1*1000}')
WHO_LENGTH=$(who | wc -l)

read -r DISK_TOTAL_KB DISK_USED_KB < <(
  df -BK --output=size,used / | tail -n 1 | awk '{gsub(/K/,""); print $1, $2}'
)
UPTIME=$(awk '{print int($1/60)}' /proc/uptime)
LOAD=$(awk '{print $1}' /proc/loadavg)

source ~/.env
PUB="mosquitto_pub -h $MQTTS_HOST -p $MQTTS_PORT -u $MQTTS_USERNAME -P $MQTTS_PASSWORD"
BASE_TOPIC="$HOSTNAME"
$PUB -t "$BASE_TOPIC/cpu" -m "$CPU_USAGE"
$PUB -t "$BASE_TOPIC/cpu_temp" -m "$CPU_TEMP"
$PUB -t "$BASE_TOPIC/throttling_state" -m "$THROTTLING_STATE"
$PUB -t "$BASE_TOPIC/systemctl_failed" -m "$SYSTEMCTL_FAILED"
$PUB -t "$BASE_TOPIC/memory/used_kb" -m "$MEM_USED"
$PUB -t "$BASE_TOPIC/memory/total_kb" -m "$MEM_TOTAL"
$PUB -t "$BASE_TOPIC/load" -m "$LOAD"
$PUB -t "$BASE_TOPIC/uptime_minutes" -m "$UPTIME"
$PUB -t "$BASE_TOPIC/ssid" -m "$WIFI_SSID"
$PUB -t "$BASE_TOPIC/ping" -m "$PINGTIME"
$PUB -t "$BASE_TOPIC/ip" -m "$IP_ADDRESS"
$PUB -t "$BASE_TOPIC/who_length" -m "$WHO_LENGTH"
$PUB -t "$BASE_TOPIC/disk/root/used_kb" -m "$DISK_USED_KB"
$PUB -t "$BASE_TOPIC/disk/root/total_kb" -m "$DISK_TOTAL_KB"

