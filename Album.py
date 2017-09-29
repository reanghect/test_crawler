#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import re
import logging
import requests
from crawlerHelper import get_config, request
from bs4 import BeautifulSoup

logger = logging.getLogger('crawler.Album')
code_rule = re.compile('([A-Z]{3,6})-?([0-9]{3})')
filter_rule = re.compile('(中字)|(中文)|(字幕)')


class Album(object):
    def __init__(self):
        self.check = False
        self.zip_id = 'Null'
        self.intro = 'Null router'
        self.score = float(0)
        self.category = []
        self.name = 'Null'
        self.star = []
        self.image = None
        self.torrent = None
        self.remark = None

    def init_zip_id(self, tag):
        matching = re.search(code_rule, tag.get_text())
        if matching:
            zip_id = matching.group(1) + matching.group(2)
            logger.info('getting av ' + zip_id)
            if re.search(filter_rule, tag.get_text()):
                logger.info('Checking AV ' + zip_id + ' satisfied')
                self.zip_id = zip_id
                self.intro = tag['href']
                self.check = True

    def set_score(self, tag):
        if tag.find(class_='score'):
            raw = tag.find(class_='score').get_text()
            if raw:
                try:
                    self.score = float(re.search('\((.+?)\)', raw).group(1))
                except AttributeError:
                    logger.error(self.zip_id)

    def set_star(self, tag):
        if tag.find_all('span', class_="star"):
            raw = tag.find_all('span', class_="star")
            for r in raw:
                self.star.append(r.get_text())

    def set_name(self, tag):
        if tag.find(class_="post-title text"):
            raw = tag.find(class_="post-title text").get_text()
            self.name = re.search('[A-Z]{3,5}-?[0-9]{3,5}\s(.+)', raw).group(1)

    def set_category(self, tag):
        if tag.find_all(rel='category tag'):
            raw = tag.find_all(rel='category tag')
            for r in raw:
                self.category.append(r.get_text())

    def set_image(self, tag):
        if tag.find(id="video_jacket_img"):
            self.image = tag.find(id="video_jacket_img")['src']

    def set_torrent(self, tag):
        raw = tag.find_all(href=True, text=True)
        if raw:
            for r in raw:
                if re.search('(http://www\.rmdown\.com)/link', r.get_text()):
                    self.torrent = r.get_text()

    def get_profile(self, library_host):
        try:
            profile_data = request(library_host, params={'keyword': self.zip_id})
            soup = BeautifulSoup(profile_data.text, 'lxml')
            if soup.find(class_="videos") is None:
                logger.info('Found AV Profile of ' + self.zip_id)
                self.set_score(soup)
                self.set_star(soup)
                self.set_category(soup)
                self.set_image(soup)
                self.set_name(soup)
            elif soup.find(text="搜寻没有结果。"):
                result = "Could not find " + self.zip_id + " in JAV"
                logger.error(result)
                self.remark = 'No results'
            else:
                result = "There are many videos for " + self.zip_id + " in JAV"
                logger.error(result)
                self.remark = 'Too many results'
        except requests.ConnectionError as e:
            logger.error("Couldn't access " + self.zip_id + " profile")
            logger.error(e)
            raise requests.ConnectionError

    def get_intro(self, caoliu_host, cookie):
        try:
            torrent_data = request(caoliu_host, self.intro, cookies=cookie)
            torrent_data.encoding = 'gbk'
            soup = BeautifulSoup(torrent_data.text, 'lxml')
            self.set_torrent(soup)
        except requests.ConnectionError as e:
            logger.error("Couldn't enter intro page and download torrent")
            logger.error(e)
            raise requests.ConnectionError