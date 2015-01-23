#!/usr/bin/env python

from boto import ec2, s3
from boto.exception import NoAuthHandlerFound, S3ResponseError
import os
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko import RSAKey
from StringIO import StringIO
import logging

try:
    # on regarde si on a un fichier logging_dev.py qui est hors versionning
    from logging_dev import dictconfig
except ImportError:
    from logging_prod import dictconfig

logging.config.dictConfig(dictconfig)
logger = logging.getLogger(__name__)


class SergentSshException(Exception):
    pass


class SergentSsh(object):
    _region = 'us-east-1'
    _using_vpn = False
    _aws_access_key_id = None
    _aws_secret_access_key = None
    _key_file = None

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 region='us-east-1',
                 using_vpn=False,
                 key_path=os.getenv('HOME') + '/.ssh/',
                 s3_key_bucket=None,
                 s3_key_name=None):
        """
        :param region: region used
        :param using_vpn: boolean determinig if we want to use private (True) or public (False) ip
        :param key_path: path which contains ssh key (can be s3 key)
        """
        if region is not None:
            self._region = region

        if using_vpn is not None:
            self._using_vpn = using_vpn

        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key

        if key_path is not None:
            self._key_file = StringIO()
            self._key_file.open(os.path.expanduser(key_path))

        if s3_key_bucket is not None and s3_key_name is not None:
            self._s3_bucket = s3_key_bucket
            self._s3_name = s3_key_name
            self.get_s3_key()

        if self._key_file is None:
            raise SergentSshException('you have to use a key file or key hosted on s3')

        if key_path is not None and s3_key_bucket is not None and s3_key_name is not None:
            raise SergentSshException('you have to choose between file key and s3 key')

    @staticmethod
    def tags_to_dict(tags, delimiter='='):
        """

        :param tags: tags string
        :param delimiter:
        :return: dict key:value
        """
        tags_dict = {}
        for t in tags:
            if delimiter in t:
                splitted_tag = t.split(delimiter)
                if len(splitted_tag) != 2:
                    raise SergentSshException('invalid tag format %s : must be tag_name=tag_value' % t)
                tags_dict['tag:' + splitted_tag[0]] = splitted_tag[1]
            else:
                tags_dict['tag-key'] = t

        return tags_dict

    def get_s3_key(self):
        """
        get ssh key in s3 bucket with specific name, load it in StringIO file
        :return:
        """
        try:
            c = s3.connect_to_region(self._region,
                                     aws_access_key_id=self._aws_access_key_id,
                                     aws_secret_access_key=self._aws_secret_access_key)
            bucket = c.get_bucket(self._s3_bucket)
            key = bucket.get_key(self._s3_name)
            self._key_file = StringIO()
            self._key_file.write(key.get_contents_as_string())
            self._key_file.seek(0)
            key.close()
        except NoAuthHandlerFound:
            raise SergentSshException('Boto said that you should check your credentials')
        except S3ResponseError as e:
            logger.exception(e)
            raise SergentSshException('bucket %s or key %s not found' % (self._s3_bucket, self._s3_name))

    def get_instances_by_tag(self, tags):
        """
        :param tags:list of tags you to connect to (tagname=value)
        :return: instance list
        """

        try:
            c = ec2.connect_to_region(self._region,
                                      aws_access_key_id=self._aws_access_key_id,
                                      aws_secret_access_key=self._aws_secret_access_key)

            #select instance by list of tags (OR used)
            reservations = c.get_all_reservations(filters=SergentSsh.tags_to_dict(tags))
            instances = list()

            for r in reservations:
                # for each instance launched by this reservation
                for instance in r.instances:
                    # we need only running instances
                    if instance.state.lower() == 'running':
                        instances.append(instance)

            return instances
        except NoAuthHandlerFound:
            raise SergentSshException('Boto said that you should check your credentials')

    @staticmethod
    def get_ssh_user(instance, tag_name='ssh-user'):
        """

        :param instance: instance we want ssh_user
        :param tag_name: the tag which contains ssh user informations
        :return: ssh user str
        :raise SergentSshException: if tag not found
        """
        if tag_name in instance.tags:
            return instance.tags[tag_name]
        raise SergentSshException('tag %s not found for instance %s' % (tag_name, instance.id, ))

    @staticmethod
    def get_ssh_port(instance, tag_name='ssh-port'):
        """

        :param instance: instance we want ssh_port
        :param tag_name: the tag which contains ssh port informations
        :return: ssh port str
        :raise SergentSshException: if tag not found
        """
        if tag_name in instance.tags:
            return int(instance.tags[tag_name])
        raise SergentSshException('tag %s not found for instance %s' % (tag_name, instance.id, ))

    @staticmethod
    def get_key_name(instance):
        """

        :param instance: instance we want key_name
        :return: key_name
        """
        return instance.key_name

    def connect(self, instance, tag_ssh_user, tag_ssh_port, cmd):
        """
        execute a command on instance with ssh and return if cmd param is not None
        connect to ssh if cmd is None
        :param instance:
        :param tag_ssh_user:
        :param tag_ssh_port:
        :param cmd: execute this command if not None
        :return:
        """
        ssh_user = SergentSsh.get_ssh_user(instance, tag_ssh_user)
        ssh_port = SergentSsh.get_ssh_port(instance, tag_ssh_port)

        if self._using_vpn is True:
            ssh_ip = instance.private_ip_address
        else:
            ssh_ip = instance.ip_address

        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())

        logger.debug('connecting to %s with port %s and user %s', ssh_ip, ssh_port, ssh_user)

        mykey = RSAKey.from_private_key(self._key_file)

        client.connect(hostname=ssh_ip, port=ssh_port, username=ssh_user, pkey=mykey)

        if cmd is None:
            client.invoke_shell()
        else:
            stdin, stdout, stderr = client.exec_command(command=cmd)

        print stdout.read()
        print stderr.read()