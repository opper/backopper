#!/usr/bin/env bash

BUCKET=$1

systemctl stop backopper
aws cp s3://$BUCKET/backopper /usr/local/bin/backopper
systemctl start backopper
