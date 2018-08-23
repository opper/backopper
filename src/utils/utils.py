import sys

import boto3
import os
import scp
from boto3.exceptions import S3UploadFailedError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from glob import glob
from os import environ, makedirs, unlink
from os.path import getmtime, isdir
from scp import SCPException
from smtplib import SMTP
import logging

from src.models.client import Client


def remove_old_backups(location):
    # fetch all files from this location
    # and sort them by their creation date
    files = glob('{}/*'.format(location))
    files.sort(key=getmtime)

    to_be_deleted = files[:-5:]

    for file in to_be_deleted:
        try:
            unlink(file)
        except OSError:
            return False

    return True


def send_mail(subj, error):
    msg = MIMEMultipart('alternative')

    msg['Subject'] = 'Backup failed - {}'.format(subj)
    msg['From'] = 'Backup process <t@opper.nl>'
    msg['To'] = environ.get('RECIPIENT_EMAILS')

    msg.attach(MIMEText(error, 'html'))

    s = SMTP(environ.get('MAILGUN_SMTP_URL'), 587)

    s.login(environ.get('MAILGUN_SMTP_LOGIN'), environ.get('MAILGUN_SMTP_PASSWORD'))
    s.sendmail(msg['From'], environ.get('RECIPIENT_EMAILS'), msg.as_string())

    s.quit()


def create_backups_folder(folder):
    if isdir(folder) is False:
        makedirs(folder)


def get_latest_backup(command, host):
    ssh_client = Client.get_instance(host, 'serverpilot')

    ssh_client.load_system_host_keys()
    (stdin, stdout, stderr) = ssh_client.exec_command(command)

    output = stdout.readlines()
    err = stderr.readlines()

    if len(err) != 0:
        for line in err:
            print(line, end='')

        ssh_client.close()
        exit(-2)

    if len(output) != 0:
        output = output[0]

    # stdout has an automagic newline character appended to it which is unnecessary
    return output.replace('\n', '')


def download_backup_file(file, host):
    ssh_client = Client.get_instance(host, 'serverpilot')

    # SCPCLient takes a paramiko transport as an argument
    scp_client = scp.SCPClient(ssh_client.get_transport(), progress=progress)

    try:
        scp_client.get(file, environ.get('HOME'))
    except SCPException as scpe:
        print('Error fetching the file: {}'.format(str(scpe)))

        exit(-3)

    scp_client.close()


# Define progress callback that prints the current percentage completed for the file
def progress(filename, size, sent):
    perc = float(sent) / float(size) * 100
    sys.stdout.write('progress: {:.2f}%\r'.format(perc))
    if perc == 100:
        print('')


def post_to_s3(path_to_dump, app_name, datetime):
    # disable debug stuff being uploaded to s3
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logger = logging.getLogger('backopper')
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_SECRET_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    response = s3.list_buckets()

    buckets = [bucket['Name'] for bucket in response['Buckets']]
    backups_bucket = None

    for bucket in buckets:
        if bucket == os.environ.get('AWS_BUCKET_NAME'):
            backups_bucket = bucket

    if backups_bucket is None:
        print('Could not find bucket to upload dump to. Available buckets: {}'.format(buckets))

        exit(-4)

    # file name = $project_name/$environment/backup_$datetime.gz
    file_name = '{}/{}/backup_{}.gz'.format(app_name, os.environ.get('ENVIRONMENT'), datetime)

    try:
        s3.upload_file(path_to_dump, backups_bucket, file_name)
    except S3UploadFailedError as e:
        logger.info('Error syncing to s3: {}. For app: {}'.format(str(e), app_name))

        return False

    return True


def post_to_backups_service(local_file, app_name):
    logger = logging.getLogger('backopper')
    logging.getLogger('paramiko').setLevel(logging.WARNING)

    ssh_client = Client.get_instance(os.environ.get('BACKUPS_HOST'), os.environ.get('BACKUPS_USER'))

    scp_client = scp.SCPClient(ssh_client.get_transport(), progress=None)

    try:
        ssh_client.exec_command('mkdir -p /opt/media/{}/{}'.format(app_name, os.environ.get('ENVIRONMENT')))

        scp_client.put(local_file, os.environ.get('MEDIA_BACKUPS_FOLDER').format(
            app_name,
            os.environ.get('ENVIRONMENT')
        ))
    except SCPException as scpe:
        logger.info('Error putting file: {}. For app: {}'.format(str(scpe), app_name))

        return False

    scp_client.close()


def remove_tmp_files():
    files = glob('{}/media_*'.format('/tmp'))
    files.sort(key=getmtime)

    for file in files:
        try:
            unlink(file)
        except OSError:
            return False

    return True
