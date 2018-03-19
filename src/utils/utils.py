import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from glob import glob
from os import environ, makedirs, unlink
from os.path import getmtime, isdir
from smtplib import SMTP

import scp
from scp import SCPException

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


def send_mail(error):
    msg = MIMEMultipart('alternative')

    msg['Subject'] = 'Backup failed'
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
    ssh_client = Client.get_instance(host)

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
    ssh_client = Client.get_instance(host)

    # SCPCLient takes a paramiko transport as an argument
    scp_client = scp.SCPClient(ssh_client.get_transport(), progress=progress)

    try:
        scp_client.get(file, environ.get('HOME'))
    except SCPException as scpe:
        print('Error fetching the file: {}'.format(scpe))

        exit(-3)

    scp_client.close()


# Define progress callback that prints the current percentage completed for the file
def progress(filename, size, sent):
    perc = float(sent) / float(size) * 100
    sys.stdout.write('progress: {:.2f}%\r'.format(perc))
    if perc == 100:
        print('')
