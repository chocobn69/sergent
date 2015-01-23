#!/usr/bin/env python
# -*- coding: utf-8 -*-

# config de logging par defaut
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
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'null': {
            'level': 'ERROR',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'ERROR',
            'propagate': True
        },
    }
}