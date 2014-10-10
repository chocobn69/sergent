#!/usr/bin/env python
import click
from click import UsageError
from ssh import SergentSsh, SergentSshException
import ConfigParser
import logging
import os
import sys


class SergentCliException(Exception):
    pass


class Cli(object):

    @staticmethod
    @click.command()
    @click.option('--tags', '-t', multiple=True, help='tags where you want to connect to (tagname=value) '
                                                      'separated by spaces')
    @click.option('--configfile', '-c', default=os.getenv('HOME') + '/.sergent', help='config file for sergent '
                                                                                   '(default ~/.sergent)')
    @click.option('--configsection', '-s', default='sergent', help='config section in config file for sergent'
                                                                   ' (default sergent)')
    @click.option('--debug/--no-debug', default=False, help='turn on debug (default False)')
    def go(tags, configfile, configsection, debug):

        # turn on debug mode (mainly for boto)
        if debug:
            logging.basicConfig(level=logging.DEBUG)

        # we need the config file
        try:
            config = ConfigParser.ConfigParser()
            config.readfp(open(configfile))

            aws_access_key_id = config.get(configsection, 'aws_access_key_id')
            if aws_access_key_id is None or len(aws_access_key_id) == 0:
                raise UsageError('aws_access_key_id not found in %s' % configfile)

            aws_secret_access_key = config.get(configsection, 'aws_secret_access_key')
            if aws_secret_access_key is None or len(aws_secret_access_key) == 0:
                raise UsageError('aws_secret_access_key not found in %s' % configfile)

            tag_ssh_user = config.get(configsection, 'tag_ssh_user')
            tag_ssh_port = config.get(configsection, 'tag_ssh_port')
            key_path = config.get(configsection, 'key_path')
            using_vpn = config.getboolean(configsection, 'using_vpn')
        except IOError:
            raise UsageError('%s config file not found' % configfile)
        except ConfigParser.NoSectionError:
            raise UsageError('section %s not found in config file %s' % (configsection, configfile))

        # now we can try to connect
        try:
            ssh = SergentSsh(aws_access_key_id,
                             aws_secret_access_key,
                             key_path=key_path,
                             using_vpn=using_vpn)
            instances = ssh.get_instances_by_tag(tags)
            # if we have more than one instance, we need to make a choice
            if len(instances) > 1:
                count_instance = 1
                click.echo('0) None, I will filter more')
                for instance in instances:
                    click.echo('%s) %s - %s' % (count_instance,
                                                instance.id,
                                                instance.private_ip_address))
                    count_instance += 1
                choosen_one = int(click.prompt('Please choose an instance', type=int))
                if choosen_one < 0 or choosen_one > len(instances):
                    raise UsageError('You have to choose a correct instance'
                                     ' between %s and %s' % (1, len(instances)))
            # if we have one instance only
            elif len(instances) == 1:
                choosen_one = 1
            # if we have no instance at all
            else:
                raise UsageError('Tag(s) %s not found' % (tags, ))

            if choosen_one == 0:
                sys.exit(0)

            instance_chosen = instances[choosen_one - 1]

            ssh_user = ssh.get_ssh_user(instance_chosen, tag_name=tag_ssh_user)
            ssh_port = ssh.get_ssh_user(instance_chosen, tag_name=tag_ssh_port)

            ssh_cmd = ssh.contruct_ssh_str(instance_chosen, ssh_user, ssh_port)

            logging.info('executing %s' % ssh_cmd)
            os.system(ssh_cmd)

        except SergentSshException as e:
            raise UsageError(e.message)