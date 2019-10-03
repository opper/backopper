package main

import (
    "encoding/json"
    "fmt"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/credentials"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/s3"
    "github.com/bramvdbogaerde/go-scp"
    "github.com/jasonlvhit/gocron"
    "golang.org/x/crypto/ssh"
    "io/ioutil"
    "net/http"
    "os"
    "path/filepath"
    "sort"
)

func request(url string, method string, returnValue Response) {
    client := http.Client{}
    request, err := http.NewRequest(method, url, nil)

    if err != nil {
        fmt.Printf("error: %v\n", err)
    }

    // super secret authentication for the cloud admin :)
    request.Header.Set("X-Secret-Key", os.Getenv("SECRET_KEY"))

    response, _ := client.Do(request)

    defer response.Body.Close()

    body, err := ioutil.ReadAll(response.Body)
    if err != nil {
        fmt.Println(err.Error())
    }

    _ = json.Unmarshal(body, &returnValue)
}

func scheduleBackup(backup BackupResponse, scheduler *gocron.Scheduler) {
    job := scheduler.Every(1)

    switch backup.Frequency {
    case "daily":
        // TOOD: change this to actually daily freq as opposed to minute as it is now. only for testing purposes
        job = job.Minute()
    case "hourly":
        job = job.Hour()
    }

    job.Do(doBackup, backup)
}

func awsClient() *s3.S3 {
    sess := session.Must(session.NewSession(&aws.Config{
        // TODO: should probably make the region variable
        Region: aws.String("eu-central-1"),
        Credentials: credentials.NewStaticCredentials(
            os.Getenv("AWS_SECRET_KEY_ID"),
            os.Getenv("AWS_SECRET_ACCESS_KEY"),
            "",
        ),
    }))
    return s3.New(sess)
}

func scpClient(user string, host string) scp.Client {
    homeDir, _ := os.UserHomeDir()
    privateKey, _ := ioutil.ReadFile(fmt.Sprintf("%s/.ssh/id_rsa", homeDir))
    signer, _ := ssh.ParsePrivateKey(privateKey)

    sshAuth := []ssh.AuthMethod{
        ssh.PublicKeys(signer),
    }
    sshConfig := ssh.ClientConfig{
        User:            user,
        Auth:            sshAuth,
        HostKeyCallback: ssh.InsecureIgnoreHostKey(), // TODO: at some point should take a look at this
    }
    scpClient := scp.NewClient(fmt.Sprintf("%s:222", host), &sshConfig)

    return scpClient
}

func cleanTmpFolder() {
    tempMediaBackups, _ := filepath.Glob("/tmp/media*.tar.gz")

    for _, file := range tempMediaBackups {
        _ = os.Remove(file)
    }
}

func cleanOldBackups(backupsLocation string) {
    oldFiles, _ := ioutil.ReadDir(backupsLocation)

    sort.Slice(oldFiles, func(i, j int) bool {
        return oldFiles[i].ModTime().After(oldFiles[j].ModTime())
    })

    toDeleteFiles := oldFiles[5:]

    for _, file := range toDeleteFiles {
        _ = os.Remove(fmt.Sprintf("%s/%s", backupsLocation, file.Name()))
    }
}
