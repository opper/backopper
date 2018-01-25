#! /bin/bash
cd /opt/backups/backopper/current
source venv/bin/activate

backopper --action=backup --app=$1