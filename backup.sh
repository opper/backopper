#! /bin/bash
cd $2
source venv/bin/activate

backopper --action=backup --app=$1