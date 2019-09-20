package main

import (
    "github.com/jasonlvhit/gocron"
    _ "github.com/joho/godotenv/autoload"
)

func main() {
    gocron.Every(1).Minute().Do(mainCronHandler)

    _, _ = gocron.NextRun()

    <-gocron.Start()
}
