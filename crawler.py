#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import logging
import configparser


CONF_LOG = "logger.conf"
logging.config.fileConfig(CONF_LOG)
logger = logging.getLogger('crawler')


def get_config(section, key):
    config = configparser.ConfigParser()
    config.read('static.conf')
    return config.get(section, key)


def main():
    logger.info("Crawler started successfully")
    pass


if __name__ == '__main__':
    main()
