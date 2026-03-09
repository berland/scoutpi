#!/bin/bash
# This script runs reverse SSH tunnel persistently

# SETTINGS (edit these)
REMOTE_USER=berland            # user on public server
REMOTE_IP=raaserv.no # public IP or DNS
REMOTE_PORT=22220            # port to open on remote for access
SERVER_PORT=2222             # port on remote to use for establishing tunnel
LOCAL_PORT=22                # port to expose from local host
SSH_KEY=/home/berland/.ssh/reverse_tunnel_key # private key for connection

# If local connection is available, it must be used, otherwise
# something with NAT'ing does not work
if timeout 2 bash -c "</dev/tcp/192.168.1.20/22" &> /dev/null; then
    REMOTE_IP=192.168.1.20
    SERVER_PORT=22
fi

# Reconnect indefinitely with some delay on failure, and no remote command
while true; do
  /usr/bin/ssh -o ServerAliveInterval=60 \
    -v \
    -o ServerAliveCountMax=3 \
    -p ${SERVER_PORT} \
    -o ExitOnForwardFailure=yes \
    -N -R ${REMOTE_PORT}:localhost:${LOCAL_PORT} \
    -i "${SSH_KEY}" \
    "${REMOTE_USER}@${REMOTE_IP}"
  sleep 10
done
