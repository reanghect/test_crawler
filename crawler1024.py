import requests
from bs4 import BeautifulSoup
import re
import shutil
import data_source as db
import time
import os.path
import multiprocessing
import logging
import configparser

CONF_LOG = "logger.conf"
logging.config.fileConfig(CONF_LOG)
logger = logging.getLogger('crawler')


# LOG_FILE = 'AV_profIle.log'
# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)

# handler = logging.FileHandler(LOG_FILE)
# handler.setLevel(logging.DEBUG)
#
# formatter = logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
#
# logger.addHandler(handler)


code_rule = re.compile('([A-Z]{3,6})-?([0-9]{3})')
filter_rule = re.compile('(中字)|(中文)|(字幕)')


library_host = 'http://www.javlibrary.com'
library_router = '/cn/vl_searchbyid.php'
cookie = dict()
with open("cookie", 'r') as f:
    for line in f:
        cook_list = line.rstrip().split("\t")
        cookie[cook_list[0]] = cook_list[1]


def get_config(section, key):
    config = configparser.ConfigParser()
    config.read('static.conf')
    return config.get(section, key)


caoliu_host = get_config('WebURL', 'MainHost')
caoliu_index_router = get_config('WebURL', 'IndexRouter')


def request(host, router=None, flag='url', **kw):
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64)' \
                 ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36'
    proxy = {
        "http": "http://westin.usv3-h.xduotai.com:10962",
        "https": "http://westin.usv3-h.xduotai.com:10962"
    }
    headers = {'User-agent': user_agent}
    if router is None:
        url = host
    else:
        url = host + router

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

    def get_profile(self):
        try:
            profile_data = request(library_host, library_router, params={'keyword': self.zip_id})
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

    def get_intro(self):
        try:
            torrent_data = request(caoliu_host, self.intro, cookies=cookie)
            torrent_data.encoding = 'gbk'
            soup = BeautifulSoup(torrent_data.text, 'lxml')
            self.set_torrent(soup)
        except requests.ConnectionError as e:
            logger.error("Couldn't enter intro page and download torrent")
            logger.error(e)
            raise requests.ConnectionError


def image(album):
    if album.image is not None:
        try:
            image_raw = request(album.image, flag='file')
            image_name = album.zip_id + '__' + str(album.score) + '.jpg'
            if image_raw.status_code == 200 and os.path.exists(image_name) is False:
                with open(image_name, 'wb') as j:
                    image_raw.raw.decode_content = True
                    shutil.copyfileobj(image_raw.raw, j)
                j.close()
            else:
                logger.error("Could not download " + image_name)
        except requests.ConnectionError as e:
            logger.error("Couldn't access to image page due to NetError")
            raise requests.ConnectionError


def crawling(page):
    index_payload = {'fid': 15, 'page': page}


    try:
        req = request(caoliu_host, caoliu_index_router, params=index_payload, cookies=cookie)
    except requests.ConnectionError as e:
        time.sleep(50)
        logger.error(e)
        logger.error("Couldn't access to index page " + str(page))
        raise ConnectionError
    req.encoding = 'gbk'
    soup = BeautifulSoup(req.text, 'lxml')
    link = soup.find_all('a')
    for l in link:
        video = Album()
        video.init_zip_id(l)
        if video.check is True:
            try:
                video.get_profile()
                video.get_intro()
                image(video)
                db.Choice.create_or_get(zip_id=video.zip_id, name=video.name, star=' '.join(video.star),
                                        category=' '.join(video.category), score=video.score,
                                        image=video.image, torrent=video.torrent, remark=video.remark)
            except requests.ConnectionError as e:
                time.sleep(50)
                logger(e)
                continue


if __name__ == "__main__":
    pool = multiprocessing.Pool(processes=3)
    for page_number in range(1, 600):
        pool.apply_async(crawling, (page_number, ))
    logger.info('Ready to craw AV in 2 processes')
    pool.close()
    pool.join()
    logger.info('All AV loaded into database')
