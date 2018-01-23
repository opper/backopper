### Backopper

Backopper is a small utility that makes database backups based on a given frequency.

#### In-depth explanation

The way that this works is the following. In gem, we specify a backup frequency for each project (be it daily or weekly 
or whatever). The backopper utility runs every 5 minutes and fetches the frequency of all the projects based on the
environment it's in. 

In each run, it creates a cronjob based on whatever frequency it polled and it calls itself again but with the flag
`--action=backup` and the name of the app. An example cron entry would look like so:

`0 0 * * * /bin/sh -c '/venv/bin/backopper --action=backup --app=Hagelswag'`

On each run of the backup action, the script does the following. Based on the app name, it loads the contents of the
.env file in the jenkins shared directory (that is where the credentials are stored). After loading the credentials,
it cleans up the backups folder so that only the last 5 backups are kept. After the cleanup, it attempts to make a 
backup based on those credentials and save a gzipped file into the backups directory. If this fails, it sends an email 
alerting of the failure. If everything went well, it will post to gem with the name of the app and the time the backup 
has been executed.