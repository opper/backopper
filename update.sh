#!/usr/bin/env bash

BUCKET=$1

systemctl stop backopper
aws s3 cp s3://$BUCKET/backopper /usr/local/bin/backopper
chmod +x /usr/local/bin/backopper
systemctl start backopper
