# builds package for local dev
dev:
	go build -tags dev .

# builds package for linux
build:
	ENVIRONMENT=production GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" . && upx -9 backopper

.PHONY: update
update:
	systemctl stop backopper
	aws s3 cp s3://$(BUCKET)/backopper /usr/local/bin/backopper
	chmod +x /usr/local/bin/backopper
	systemctl start backopper
