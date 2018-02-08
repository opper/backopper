#!/bin/bash

cd $1
source venv/bin/activate

pip install backopper --upgrade --force-reinstall