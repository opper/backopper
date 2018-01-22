from .secrets import API_GET_URL, API_POST_URL, ENVIRONMENT
from requests import get, post
from dotenv import load_dotenv
import os
import click
import subprocess
import arrow


def backup(app):
    env_file = '/srv/users/serverpilot/apps/{}/jenkins/shared'.format(app)
    load_dotenv(env_file)

    # ret = subprocess.call(
    #     'mysqldump -u{} -p{} {} | gzip > /opt/backups/{}/{}.sql.gz'.format(
    #         os.environ.get('DB_USER'),
    #         os.environ.get('DB_PASS'),
    #         os.environ.get('DB_NAME'),
    #         app,
    #         arrow.now('Europe/Amsterdam').format('YYYYMMDDHHmmss')
    #     ),
    #     shell=True)
    ret = 0

    if ret != 0:
        print('yo')
    else:
        response = post(API_POST_URL, json={
            'secret': '0xCAFEBABE',
            'executed': arrow.now('Europe/Amsterdam').timestamp,
            'name': app
        })

        print(response.text)


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
