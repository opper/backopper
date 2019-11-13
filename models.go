package main

type Response interface {}

type BackupResponse struct {
    Response

    Name string
    Frequency string
    DBEngine string `json:"db_engine"`
    Id string
}

type NotifyCloudAdmin struct {
    ExecTime int64 `json:"exec_time"`
    Status string `json:"status"`
    S3Synced bool `json:"s3_synced"`
}
