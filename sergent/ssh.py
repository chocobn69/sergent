#!/usr/bin/env python

from boto import ec2
from boto.exception import NoAuthHandlerFound
import os


class SergentSshException(Exception):
    pass


class SergentSsh(object):
    _region = 'us-east-1'
    _using_vpn = False
    _key_path = '.ssh/'
    _aws_access_key_id = None
    _aws_secret_access_key = None

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 region='us-east-1',
                 using_vpn=False,
                 key_path=os.getenv('HOME') + '/.ssh/'):
        """
        :param region: region used
        :param using_vpn: boolean determinig if we want to use private (True) or public (False) ip
        :param key_path: path whis contains ssh key
        """
        if region is not None:
            self._region = region

        if using_vpn is not None:
            self._using_vpn = using_vpn

        if key_path is not None:
            self._key_path = os.path.expanduser(key_path)

        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key

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
            return instance.tags[tag_name]
        raise SergentSshException('tag %s not found for instance %s' % (tag_name, instance.id, ))

    @staticmethod
    def get_key_name(instance):
        """

        :param instance: instance we want key_name
        :return: key_name
        """
        return instance.key_name

    def contruct_ssh_str(self, instance, ssh_user, ssh_port):
        key_name = SergentSsh.get_key_name(instance)
        if self._using_vpn is True:
            ssh_ip = instance.private_ip_address
        else:
            ssh_ip = instance.ip_address

        # checks if key exists
        if not os.path.isfile('%s/%s' % (self._key_path, key_name)):
            # amazon gives us a key with .pem extension, let's check if it exists
            key_name += '.pem'
            if not os.path.isfile('%s/%s' % (self._key_path, key_name)):
                # if not, we raise !
                raise SergentSshException('key %s/%s not found' % (self._key_path, key_name))

        return 'ssh -i %s/%s %s@%s -p %s' % (self._key_path, key_name, ssh_user, ssh_ip, ssh_port)