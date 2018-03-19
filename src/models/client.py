import os

import paramiko


# singleton pattern so that the SSH connection to list the last backup and download said backup is not done more than
# once (i.e. each command has their own connection)
class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(*args, **kwargs)
            return cls.__instance


class Client(object):
    __metaclass__ = SingletonType
    client = None

    @classmethod
    def get_instance(cls, host, port=None):
        if port is None:
            port = 222  # default ssh port for us

        client = paramiko.SSHClient()
        client.load_system_host_keys('{}/.ssh/known_hosts'.format(os.environ.get('HOME')))
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username='serverpilot')
        cls.client = client

        return client
