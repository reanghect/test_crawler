#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import logging.config
import configparser
import requests

CONF_LOG = "logger.conf"
logging.config.fileConfig(CONF_LOG)
logger = logging.getLogger('crawler')


def get_config(section, key):
    config = configparser.ConfigParser()
    config.read('static.conf')
    return config.get(section, key)


def request(url, flag='url', is_proxy=False, **kw):

    if get_config("Proxy", "isProxy") == '0':
        if is_proxy:
            http_proxy = get_config("Proxy", "http")
            https_proxy = get_config("Proxy", "https")
            proxy = {
                "http": http_proxy,
                "https": https_proxy
            }
        else:
            proxy = None
    else:
        proxy = None

    user_agent = get_config("Proxy", "userAgent")
    headers = {'User-agent': user_agent}

    try:
        s = requests.Session()
        if flag == 'url':
            req = s.get(url, headers=headers, proxies=proxy, **kw)
        else:
            req = s.get(url, headers=headers, proxies=proxy, stream=True, **kw)
        return req
    except requests.ConnectionError as e:
        logger.error(e)
        logger.error("PROXY ERROR")
        raise requests.ConnectionError
