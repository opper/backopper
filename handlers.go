package main

import (
    "bytes"
    "crypto/md5"
    "fmt"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/service/s3"
    "github.com/jasonlvhit/gocron"
    "github.com/joho/godotenv"
    "io"
    "os"
    "os/exec"
    "time"
)

func mainCronHandler() {
    fmt.Println("Main cron handler started")

    url := fmt.Sprintf(os.Getenv("API_GET_URL"), os.Getenv("ENVIRONMENT"))

    var backups [] BackupResponse
    request(url, "GET", &backups)

    scheduler := gocron.NewScheduler()

    for _, backup := range backups {
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

    // this shouldn't cause any issues with in-progress dumps that haven't been scp'd to the media server
    // shouldn't
    cleanTmpFolder()

    _, _ = scheduler.NextRun()
    <-scheduler.Start()
}

func doBackup(project BackupResponse) {
    projectName := project.Name
    fmt.Println(fmt.Sprintf("Starting database backup for %s", projectName))
    err := godotenv.Overload(fmt.Sprintf(os.Getenv("ENV_FILE_LOCATION"), projectName))

    if err != nil {
        fmt.Printf("error loading .env for %s: %v", projectName, err)
        return
    }

    // Mon Jan 2 15:04:05 -0700 MST 2006
    dateTimeNow := time.Now().Format("20060102150405")
    backupsFolder := fmt.Sprintf(os.Getenv("BACKUPS_LOCATION"), projectName)
    backupFileName := fmt.Sprintf("%s/%s.sql.gz", backupsFolder, dateTimeNow)
    dumpCommand := ""

    switch project.DBEngine {
    case "mysql":
        dumpCommand = `mysqldump --password="%s" --user="%s" %s | gzip > %s`
    case "postgresql":
        // host is needed in the pg_dump command because if not specified, it'll attempt to log-in with peer auth
        dumpCommand = `PGPASSWORD="%s" pg_dump -h 127.0.0.1 --username="%s" -F c %s > %s`
    }

    comm := exec.Command(
        "bash",
        "-c",
        fmt.Sprintf(dumpCommand,
            os.Getenv("DB_PASSWORD"),
            os.Getenv("DB_USERNAME"),
            os.Getenv("DB_DATABASE"),
            backupFileName,
        ),
    )
    err = comm.Run()
    dumpDone := true

    if err != nil {
        dumpDone = false
        fmt.Printf("failed executing db dump for %s: %v", projectName, err)
    }

    if dumpDone {
        doS3Sync(backupFileName, projectName, dateTimeNow)
    }

    doMediaBackup(projectName)
}

func doS3Sync(backupFile string, projectName string, dateTimeNow string) {
    s3Client := awsClient()

    file, _ := os.Open(backupFile)
    defer file.Close()

    fileKey := fmt.Sprintf("%s/%s/backup_%s.sql.gz", projectName, os.Getenv("ENVIRONMENT"), dateTimeNow)

    fileInfo, _ := file.Stat()
    size := fileInfo.Size()
    buffer := make([]byte, size)

    _, _ = file.Read(buffer)

    _, _ = s3Client.PutObject(&s3.PutObjectInput{
        Bucket:        aws.String(os.Getenv("AWS_BUCKET_NAME")),
        Body:          bytes.NewReader(buffer),
        ContentLength: aws.Int64(size),
        Key:           aws.String(fileKey),
    })
}

func doMediaBackup(projectName string) {
    fmt.Printf("Starting media backup for %s\n", projectName)
    dateTimeNow := time.Now().Format("20060102150405")
    hash := md5.New()

    _, _ = io.WriteString(hash, projectName)
    _, _ = io.WriteString(hash, dateTimeNow)

    // makes a filename like media_012a_20060102150405.tar.gz.
    fileName := fmt.Sprintf("media_%x_%s.tar.gz", hash.Sum(nil)[:2], dateTimeNow)
    tempMediaLocation := fmt.Sprintf("/tmp/%s", fileName)
    mediaFolder := fmt.Sprintf(os.Getenv("MEDIA_FOLDER_LOCATION"), projectName)

    // for now only handles wp-style media folders (meaning that mediaFolder is likely something like
    // /var/www/proj/wp-content/uploads. should probs make it handle laravel's uploads also in the future.
    command := exec.Command(
        "tar",
        "-czf",
        tempMediaLocation,
        "-C",
        mediaFolder,
        "uploads",
    )

    err := command.Run()
    mediaBackupDone := true

    if err != nil {
        fmt.Printf("failed executing media backup for %s: %v", projectName, err)
        mediaBackupDone = false
    }

    if mediaBackupDone {
        // because the syncing of the media dump to the media server is done in a goroutine, there might be issues with
        // the cleaning of the old temp files from /tmp. it can happen that the process will attempt to remove a file
        // that's either in progress or not synced yet. will have to test see if this is indeed the case or not.
        go func() {
            doMediaServerSync(tempMediaLocation, projectName, fileName)
        }()
    }
}

func doMediaServerSync(mediaLocation string, projectName string, fileName string) {
    fmt.Printf("Starting media sync for %s\n", projectName)

    scpClient := scpClient(os.Getenv("BACKUPS_USER"), os.Getenv("BACKUPS_HOST"))

    err := scpClient.Connect()

    if err != nil {
        fmt.Printf("failed to connect to media server: %v", err)
        return
    }
    defer scpClient.Session.Close()

    file, _ := os.Open(mediaLocation)
    defer file.Close()

    fileInfo, _ := file.Stat()

    err = scpClient.Copy(file, fmt.Sprintf(os.Getenv("MEDIA_BACKUPS_FOLDER"), projectName, fileName), "0644", fileInfo.Size())

    if err != nil {
        fmt.Printf("failed to scp file to media server: %v", err)
        return
    }
}
