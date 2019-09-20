package main

import (
    "encoding/json"
    "fmt"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/credentials"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/s3"
    "github.com/bramvdbogaerde/go-scp"
    "github.com/bramvdbogaerde/go-scp/auth"
    "golang.org/x/crypto/ssh/knownhosts"
    "io/ioutil"
    "net/http"
    "os"
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

    // TODO: not entirely sure if this is actually needed or not
    hostsSomething, err := knownhosts.New(fmt.Sprintf("%s/.ssh/known_hosts", homeDir))

    if err != nil {
        fmt.Sprintf("%v\n", err)
    }

    sshConfig, _ := auth.PrivateKey(user, fmt.Sprintf("%s/.ssh/id_rsa", homeDir), hostsSomething)
    scpClient := scp.NewClient(fmt.Sprintf("%s:222", host), &sshConfig)

    return scpClient
}
