package main

type Response interface {}

type BackupResponse struct {
    Response

    Name string
    Frequency string
    DBEngine string `json:"db_engine"`
}
