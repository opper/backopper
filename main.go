package main

import (
    "github.com/jasonlvhit/gocron"

    // only needed for development as the envvars in prod will be provided by systemd
    _ "github.com/joho/godotenv/autoload"
)

func main() {
    gocron.Every(1).Day().At("23:00").Do(mainCronHandler)

    _, _ = gocron.NextRun()

    <-gocron.Start()
}
