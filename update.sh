#!/bin/bash

cd $1
source venv/bin/activate

git pull
pip install backopper --upgrade --force-reinstall