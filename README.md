## Backopper

Backopper is a small tool created in go to assist with the creation of backups for all the projects we got going on. 
Basically, it runs every x amount of time for each app and it creates the backups somewhere on disk 
(normally in /opt/backups/$APP). It also syncs the backups to a bucket in S3 and posts an archive of media files to a 
backup server.

### In-depth explanation

There's 2 main functionalities to this tool: fetching a list of apps and creating the actual backups.

#### Fetching the list of apps

This is done via an API request to the a certain application. A response for this request would look like this:

```json
[
    {
        "name": "project_1",
        "frequency": "daily",
        "db_engine": "mysql",
        "project_type": "wordpress"
    },
    {
        "name": "project_2",
        "frequency": "weekly",
        "db_engine": "postgres",
        "project_type": "laravel"
    }
]
```

There's 2 main things for each application that come in this response: 

- The name of the application (which should match the name of the folder (if it's a serverpilot app) on disk 
(like /srv/users/serverpilot/apps/project_1))
- The frequency of the backups

It is based on [jasonlvhit/gocron](https://github.com/jasonlvhit/gocron) meaning that it will not create actual entries
in the crontab but it will schedule the jobs necessary itself. Makes things a bit cleaner (though a bit harder to debug)

#### Creating the actual backup

When the actual backup handler is run, several things happen:

- First, it looks for the `.env` file inside that app's root folder (hence the importance of the name of the app 
matching its location on disk).
- Once it found it, it evaluates that `.env` file so that the script has access to all the database credentials.
- After that, it composes a `mysqldump` or `pg_dump` command based on those parameters. An example of that would look like so: 
`mysqldump --user="$USER" --password="$PASSWORD" $DB_NAME | gzip > $BACKUPS_LOCATION/$UNIX_TIMESTAMP.sql.gz`. So, in the 
end, a new file that will have the name of the unix timestamp at the time of creating the backup will be created under 
`/opt/backups/$APP`. I know that having the password in 'plain text' while executing the backup is not secure but this is 
the best solution without overengineering everything.
- If the database dump is successful, it syncs a copy to an S3 bucket with a key like so:
`$PROJECT_NAME/$ENVIRONMENT/backup_$TIMESTAMP.sql.gz` if it's a MySQL dump or 
`$PROJECT_NAME/$ENVIRONMENT/backup_$TIMESTAMP.tar` if it's a PostgreSQL dump.
- Regardless if the database dump is successful or not, it will attempt to create a media backup (generally things like
pictures that users upload, documents, etc). It is quite straightforward in the sense that it will simply run tar in the following format: `tar -czf $TEMPORARY_MEDIA_LOCATION -C $MEDIA_FOLDER $FOLDER_TO_BACK_UP`. A temporary location is used because
the media backup can be quite heavy and it is not stored on the server itself (more on that later). The `-C` flag is used
to change the directory location to wherever the media folder is located, but not the actual folder to back up itself, 
that is `$FOLDER_TO_BACK_UP`. It is a bit complex in the sense that it changes dirs to the parent folder to back up and 
then it performs the tar command but this is the most reliable way I could find of making it work.
- If the media dump is successful, it is then sent via `scp` to the media server. A command like the following will be executed: `scp -P$PORT $TEMPORARY_MEDIA_LOCATION $USER@$HOST:$MEDIA_BACKUPS_PATH`.
