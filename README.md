## Backopper

Backopper is a small tool created in python to assist with the creation of backups for all the projects we got going on. 
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
        "frequency": "daily"
    },
    {
        "name": "project_2",
        "frequency": "weekly"
    }
]
```

There's 2 main things for each application that come in this response: 

- The name of the application (which should match the name of the folder (if it's a serverpilot app) on disk 
(like /srv/users/serverpilot/apps/project_1))
- The frequency of the backups

After fetching the list of apps for a specific environment, the script reads the list of root's cronjobs and adds an 
entry for each application depending on the frequency fetched from the endpoint. An example cron would look like this

`@daily /bin/bash -c '/opt/backups/backopper/backup.sh project_1 /opt/backups/backopper' # project_1`

Explanation bit by bit:

- `@daily` is a shorthand syntax that evaluates to `0 0 * * *` and means that the cronjob will be executed every day at 12 AM.
- `/bin/bash -c '/opt/backups/backopper/backup.sh project_1 /opt/backups/backopper'` is the actual command that runs 
the backup process. It basically executes the file `/opt/backups/backopper/backup.sh` using bash and adds 2 parameters 
to it:
    - First is the name of the application (first part where the name of the app from the API is important)
    - Second is the root folder for the backopper tool. This is needed because backup.sh (and all the other bash 
    scripts inside the backopper tool) run inside a virtual environment that is activated on each run.
- `# project_1` is a tag for the cronjob to help avoid duplicates when creating new jobs.

#### Creating the actual backup

When the `backup.sh` script is run, it does a couple things:

- First, it looks for the `.env` file inside that app's root folder (hence the importance of the name of the app 
matching its location on disk).
- Once it found it, it evaluates that `.env` file so that the script has access to all the database credentials.
- After that, it composes a `mysqldump` command based on those parameters. An example of that would look like so: 
`mysqldump --user="$USER" --password="$PASSWORD" $DB_NAME | gzip > $BACKUPS_LOCATION/$UNIX_TIMESTAMP.sql.gz`. So, in the 
end, a new file that will have the name of the unix timestamp at the time of creating the backup will be created under 
`/opt/backups/$APP`. I know that having the password in 'plain text' while executing the backup is not secure but this is 
the best solution without overengineering everything.

