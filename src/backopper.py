import getpass
import logging.config
import os
import subprocess

import arrow
import click
import requests
from crontab import CronTab
from dotenv import load_dotenv

from .secrets import API_GET_URL, API_POST_URL, BACKUPS_LOCATION, ENVIRONMENT, ENV_FILE_LOCATION, HOSTNAMES, SRC_PATH
from .utils.utils import create_backups_folder, download_backup_file, get_latest_backup, remove_old_backups, send_mail


def backup(app):
    logger = logging.getLogger(__name__)

    # loads the .env file into memory to have access to the db credentials
    load_dotenv(ENV_FILE_LOCATION.format(app))

    backup_folder = BACKUPS_LOCATION.format(app)

    create_backups_folder(backup_folder)
    remove_old_backups(backup_folder)

    logger.info('#### Backup process for {} started ####'.format(app))
    logger.info('Attempting to make database dump')

    # attempt to run the mysqldump process and save the gzipped dump to the backups location
    ret = subprocess.run(
        'mysqldump --user="{}" --password="{}" {} | gzip > {}/{}.sql.gz'.format(
            os.environ.get('DB_USERNAME'),
            os.environ.get('DB_PASSWORD'),
            os.environ.get('DB_DATABASE'),
            backup_folder,
            arrow.now('Europe/Amsterdam').format('YYYYMMDDHHmmss')
        ),
        shell=True, stderr=True)

    # in case of error  (return code is different than 0),
    # send an email alerting of this
    # otherwise, post to gem that the backup has been done successfuly
    if ret.returncode != 0:
        logger.error('Dump failed. Reason: {}'.format(ret.stderr))
        send_mail(ret.stderr)
    else:
        logger.info('Dump completed successfully')
        response = requests.post(API_POST_URL, json={
            'secret': '0xCAFEBABE',
            'executed': arrow.now('Europe/Amsterdam').timestamp,
            'name': app
        })

        if response.status_code != 200:
            send_mail(response.text)
    logger.info('#### Backup process for {} ended ####'.format(app))


def cron():
    logger = logging.getLogger(__name__)

    logger.info('#### Cron started')
    response = requests.get(API_GET_URL.format(ENVIRONMENT)).json()

    # create cron object based on user's crontab
    cron_obj = CronTab(user=getpass.getuser())

    for item in response:
        name = item['name']
        frequency = item['frequency']

        allowed_frequencies = ['daily', 'weekly']

        # in case there's bogus frequency coming from the api, silently skip the interation and move on
        if frequency not in allowed_frequencies:
            logger.warning('Unallowed frequency came in from the API: {}, Might want to check this'.format(frequency))
            continue

        cron_command = "/bin/bash -c '{0}/backup.sh {1} {0}'".format(SRC_PATH, name)
        freq = ''

        if frequency in allowed_frequencies:
            # becomes something like "@daily" or "@yearly" or whatever
            freq = '@{}'.format(frequency)

        # magic to compare between old cron job for this app and the new one coming composed with whatever's coming
        # from the API.

        # the reason i chose to sorta compose a new cron job is because the lib i'm using, python-crontab, does not
        # allow for easy comparison of jobs. so on each iteration of this loop, i compose a temporary cron command
        # and compare it with whatever's in the crontab on this tag
        temp_cron_command = '{} {} # {}'.format(freq, cron_command, name)

        existing_job = list(cron_obj.find_comment(name))

        # safe to assume that each tag (app) will have only one entry in the crontab
        # since find_comment returns a generator (which is translated to a list), i select manually
        # the first element in the list if the size is bigger than 0 (meaning if there's actually any elements)
        if len(existing_job) != 0:
            existing_job = existing_job[0]

        logger.info('Attempting to create cronjob for {}'.format(name))
        # if existing job is different than the one coming from the API, then update it
        # but first remove the existing rule
        if str(existing_job) != temp_cron_command:

            # this if exists only in the case when there's no rule set yet
            # then existing_job would be an empty list and stuff will mess up
            if len(existing_job) != 0:
                cron_obj.remove(existing_job)

            # creates a new cron and sets the frequency to whatever came from the API
            job = cron_obj.new(command=cron_command, comment=name)
            job.setall(freq)

            logger.info('Created cronjob for {} with command: {}'.format(name, cron_command))

            job.enable()
        else:
            logger.info('Cron already exists for {}'.format(name))

    # write all the changes (if any at all)
    cron_obj.write()
    logger.info('#### Cron ended')


def download(app, environment):
    command = 'ls -t {}/*.gz | head -1'.format(BACKUPS_LOCATION.format(app))
    backup_file = get_latest_backup(command, HOSTNAMES[environment])

    download_backup_file(backup_file, HOSTNAMES[environment])

    if click.confirm('Do you want to import the dump into your database?'):
        import_db(backup_file)


def import_db(file_path):
    database = click.prompt('Enter database name')
    user = click.prompt('Enter username')
    password = click.prompt('Enter password', default='')
    host = click.prompt('Enter host', default='localhost')

    if host != 'localhost':
        import_command = 'mysql --user="{}" --password="{}" --host="{}" {}'.format(user, password, host, database)
    else:
        import_command = 'mysql --user="{}" --password="{}" {}'.format(user, password, database)

    # grab the file name from the file path
    # i.e. split the path by / and grab the last element
    file_name = file_path.split('/')[-1]
    full_file_path = '{}/{}'.format(os.environ.get('HOME'), file_name)

    ret = subprocess.run('gunzip < {} | {}'.format(full_file_path, import_command), shell=True)

    if ret.returncode != 0:
        click.secho('Error importing the db: {}'.format(ret.stderr), fg='red')
    else:
        click.secho('New dump imported successfully', fg='green')
        os.unlink(full_file_path)


@click.command()
@click.option('--action')
@click.option('--app')
@click.option('--environment')
def main(action, app, environment):
    logging.config.fileConfig('src/logging.conf')

    if action == 'backup':
        backup(app)
    elif action == 'cron':
        cron()
    elif action == 'download':
        download(app, environment)
