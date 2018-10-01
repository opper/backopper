import arrow
import click
import getpass
import hashlib
import json
import logging.config
import os
import requests
import socket
import subprocess
from crontab import CronTab
from dotenv import load_dotenv

from .utils.utils import create_backups_folder, download_backup_file, get_latest_backup, post_to_backups_service, \
    post_to_s3, remove_old_backups, remove_tmp_files, send_mail

SERVERS = {
    'staging': '192.81.221.208',
    'acceptance': '188.166.13.154',
    'live': '188.166.77.230',
}

BACKUPS_LOCATION = '/opt/backups/{}'


def backup(app):
    logging.config.fileConfig('src/logging.conf')
    logger = logging.getLogger(__name__)

    # loads the .env file into memory to have access to the db credentials
    load_dotenv(os.environ.get('ENV_FILE_LOCATION').format(app))

    backup_folder = BACKUPS_LOCATION.format(app)

    create_backups_folder(backup_folder)
    remove_old_backups(backup_folder)

    logger.info('#### Backup process for {} started ####'.format(app))
    logger.info('Attempting to make database dump')

    # attempt to run the mysqldump process and save the gzipped dump to the backups location
    datetime_now = arrow.now('Europe/Amsterdam').format('YYYYMMDDHHmmss')
    dump_command = subprocess.run(
        'mysqldump --user="{}" --password="{}" {} | gzip > {}/{}.sql.gz'.format(
            os.environ.get('DB_USERNAME'),
            os.environ.get('DB_PASSWORD'),
            os.environ.get('DB_DATABASE'),
            backup_folder,
            datetime_now
        ),
        shell=True, stderr=True)

    potential_media_folder = os.environ.get('MEDIA_FOLDER_LOCATION').format(app)
    logger.info('Media folder {} for app {} exists {}'.format(
        potential_media_folder,
        app,
        os.path.exists(potential_media_folder))
    )
    media_backup = False
    if os.path.exists(potential_media_folder):
        # to avoid shenanigans with duplicated files
        app_hash = hashlib.md5('{}{}'.format(app.encode('utf-8'), datetime_now)).hexdigest()[:4]
        tar_file_name = 'media_{}_{}.tar.gz'.format(app_hash, datetime_now)
        temporary_tar_location = '/tmp/{}'.format(tar_file_name)
        subprocess.run(
            'tar -czf {} -C {} uploads'.format(
                temporary_tar_location,
                potential_media_folder
            ),
            shell=True,
            stderr=True,
        )
        media_backup = True

    # in case of error  (return code is different than 0),
    # send an email alerting of this
    # otherwise, post to cloud-admin that the backup has been done successfuly
    if dump_command.returncode != 0:
        logger.error('Database dump failed. Reason: {}'.format(dump_command.stderr))
        send_mail(subj=json.dumps({
            'hostname': socket.gethostname(),
            'app': app
        }), error=dump_command.stderr)
    else:
        logger.info('Database dump completed successfully')

    project = requests.get(
        url='{}/projects/name/{}'.format(os.environ.get('API_BASE_URL'), app),
        headers={
            'X-Secret-Key': os.environ.get('SECRET_KEY')
        }).json()
    s3_synced = False
    if dump_command.returncode == 0:
        s3_synced = post_to_s3('{}/{}.sql.gz'.format(backup_folder, datetime_now), app, datetime_now)

    logger.info('Media backup for {}: {}'.format(app, media_backup))
    if media_backup:
        post_to_backups_service(temporary_tar_location, app)

    response = requests.post(
        url=os.environ.get('API_POST_URL').format(project['id']),
        headers={
            'X-Secret-Key': os.environ.get('SECRET_KEY')
        },
        json={
            'exec_time': arrow.now('Europe/Amsterdam').timestamp,
            'status': 'success' if dump_command.returncode == 0 else 'failure',
            's3_synced': s3_synced,
        })

    if response.status_code != 200 and response.status_code != 201 and response.status_code != 404:
        send_mail(json.dumps({
            'hostname': socket.gethostname(),
            'app': app
        }), response.text)

    logger.info('#### Backup process for {} ended ####'.format(app))


def cron():
    logging.config.fileConfig('src/logging.conf')
    logger = logging.getLogger(__name__)

    logger.info('#### Cron started')
    response = requests.get(
        url=os.environ.get('API_GET_URL').format(os.environ.get('ENVIRONMENT')),
        headers={
            'X-Secret-Key': os.environ.get('SECRET_KEY')
        }
    ).json()

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

        cron_command = "/bin/bash -c '{0}/backup.sh {1} {0}'&".format(os.environ.get('SRC_PATH'), name)
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
    # command to sort the dumps by timestamp and fetch only the first one (aka the most recent one)
    command = 'ls -t {}/*.gz | head -1'.format(BACKUPS_LOCATION.format(app))

    backup_file = get_latest_backup(command, SERVERS[environment])

    download_backup_file(backup_file, SERVERS[environment])

    if click.confirm('Do you want to import the dump into your database?'):
        import_db(backup_file)


def import_db(file_path):
    database = click.prompt('Enter database name')
    user = click.prompt('Enter username')
    password = click.prompt('Enter password', default='')
    host = click.prompt('Enter host', default='localhost')

    replace = click.confirm('Do you want to replace something in the dump file?')

    if replace:
        old_needle = click.prompt('Enter string to search')
        new_needle = click.prompt('Enter string to replace')

    if host != 'localhost':
        import_command = 'mysql --user="{}" --password="{}" --host="{}" {}'.format(user, password, host, database)
    else:
        import_command = 'mysql --user="{}" --password="{}" {}'.format(user, password, database)

    # grab the file name from the file path
    # i.e. split the path by / and grab the last element
    file_name = file_path.split('/')[-1]
    full_file_path = '{}/{}'.format(os.environ.get('HOME'), file_name)

    if replace:
        ret = subprocess.run(
            'gunzip < {} | sed -e "s#{}#{}#g" | {}'.format(
                full_file_path,
                old_needle,
                new_needle,
                import_command
            ),
            shell=True)
    else:
        ret = subprocess.run('gunzip < {} | {}'.format(full_file_path, import_command), shell=True)

    if ret.returncode != 0:
        click.secho('Error importing the db: {}'.format(ret.stderr), fg='red')
    else:
        click.secho('New dump imported successfully', fg='green')
        os.unlink(full_file_path)


def clean():
    remove_tmp_files()


@click.command()
@click.option('--action')
@click.option('--app')
@click.option('--environment', type=click.Choice(['staging', 'acceptance', 'live']))
def main(action, app, environment):
    load_dotenv('.env')

    if action == 'backup':
        backup(app)
    elif action == 'cron':
        cron()
    elif action == 'download':
        download(app, environment)
    elif action == 'clean':
        clean()
