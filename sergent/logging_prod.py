#!/usr/bin/env python
# -*- coding: utf-8 -*-


# config de logging par defaut
class LogConfig(object):
    log_level = 'ERROR'
    dictconfig = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s:%(levelname)s:%(name)s:%(message)s:line %(lineno)d in %(module)s'
            },
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard'
            },
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'loggers': {
            'paramiko': {
                'handlers': ['default'],
                'propagate': True
            },
            'boto': {
                'handlers': ['default'],
                'propagate': True
            },
            '': {
                'handlers': ['default'],
                'propagate': True
            },
        }
    }