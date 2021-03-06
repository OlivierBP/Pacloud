#!/usr/bin/python

import configparser

config = configparser.ConfigParser()
config.read('/etc/pacloud/pacloud.conf')

DB_DIR = config['database']['DB_DIR']
SERVER_URL = config['server']['SERVER_URL']
DB_URL = config['server']['DB_URL']
USE = config['user']['USE']
