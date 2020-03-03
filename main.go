package main

import (
    "github.com/jasonlvhit/gocron"
    _ "github.com/joho/godotenv/autoload"
)

var DEBUG = false

func main() {
    // debug flag that gets set to true in dev.go when building with -tags dev *shrug*
    if DEBUG {
        gocron.Every(1).Minute().Do(mainCronHandler)
    } else {
        gocron.Every(1).Day().At("23:00").Do(mainCronHandler)
    }
    _, _ = gocron.NextRun()

    <-gocron.Start()
}
