from .secrets import API_GET_URL, API_POST_URL, ENVIRONMENT, BACKUPS_LOCATION, ENV_FILE_LOCATION
from .utils.utils import remove_old_backups, send_mail
from requests import get, post
from dotenv import load_dotenv
import os
import click
import subprocess
import arrow


def backup(app):
    load_dotenv(ENV_FILE_LOCATION.format(app))

    backup_folder = BACKUPS_LOCATION.format(app)
    remove_old_backups(backup_folder)

    # attempt to run the mysqldump process and save the gzipped dump to the backups location
    ret = subprocess.run(
        'mysqldump -u{} -p{} {} | gzip > {}/{}.sql.gz'.format(
            os.environ.get('DB_USER'),
            os.environ.get('DB_PASS'),
            os.environ.get('DB_NAME'),
            backup_folder,
            arrow.now('Europe/Amsterdam').format('YYYYMMDDHHmmss')
        ),
        shell=True, stderr=True)

    # in case of error  (return code is different than 0),
    # send an email alerting of this
    # otherwise, post to gem that the backup has been done successfuly
    if ret.returncode != 0:
        send_mail(ret.stderr)
    else:
        response = post(API_POST_URL, json={
            'secret': '0xCAFEBABE',
            'executed': arrow.now('Europe/Amsterdam').timestamp,
            'name': app
        })

        if response.status_code != 200:
            send_mail(response.text)


def cron():
    response = get(API_GET_URL.format(ENVIRONMENT)).json()

    for item in response.items():
        name = item[0]
        frequency = item[1]

        full_cron_command = '{} /bin/sh -c \'{}/venv/bin/backopper --action=backup --app={}\''
        cron_frequency = ''

        if frequency == 'daily':
            cron_frequency = '0 0 * * *'
        elif frequency == 'weekly':
            cron_frequency = '0 0 * * 0'

        full_cron_command = full_cron_command.format(cron_frequency, os.getcwd(), name)

        print(full_cron_command)


@click.command()
@click.option('--action')
@click.option('--app')
def main(action, app):
    if action == 'backup':
        backup(app)
    elif action == 'cron':
        cron()
