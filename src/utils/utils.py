from glob import glob
from os.path import getmtime
from os import unlink
from src.secrets import MAILGUN_SMTP_LOGIN, MAILGUN_SMTP_PASSWORD, MAILGUN_SMTP_URL, RECIPIENT_EMAILS
from email.mime.text import MIMEText
from smtplib import SMTP


def remove_old_backups(location):
    # fetch all files from this location
    # and sort them by their creation date
    files = glob('{}/*'.format(location))
    files.sort(key=getmtime)

    to_be_deleted = files[5::]

    for file in to_be_deleted:
        try:
            unlink(file)
        except OSError:
            return False

    return True


def send_mail(error):
    msg = MIMEText(error)

    msg['Subject'] = 'Backup failed'
    msg['From'] = 'Backup process <t@opper.nl>'
    msg['To'] = ','.join(RECIPIENT_EMAILS)

    s = SMTP(MAILGUN_SMTP_URL, 587)

    s.login(MAILGUN_SMTP_LOGIN, MAILGUN_SMTP_PASSWORD)
    s.sendmail(msg['From'], RECIPIENT_EMAILS, msg.as_string())
    s.quit()
