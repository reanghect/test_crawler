import requests
from bs4 import BeautifulSoup
import re
import shutil
import data_source as db
import threading
import time
import os.path

code_rule = re.compile('([A-Z]{3,6})-?([0-9]{3})')
filter_rule = re.compile('(中字)|(中文)|(字幕)')
caoliu_host = 'http://cl.1024.desi/'
caoliu_index_router = 'thread0806.php'
library_host = 'http://www.javlibrary.com'
library_router = '/cn/vl_searchbyid.php'
cookie = dict()
with open("cookie", 'r') as f:
    for line in f:
        cook_list = line.rstrip().split("\t")
        cookie[cook_list[0]] = cook_list[1]


def request(host, router=None, flag='url', **kw):
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64)' \
                 ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36'
    proxy = {
        "http": "http://westin.hkv3-h.xduotai.com:10962",
        "https": "http://westin.hkv3-h.xduotai.com:10962"
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
        print(e)
        print("傻逼断网了")
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
        if re.search(filter_rule, tag.get_text()) and matching:
            self.zip_id = matching.group(1) + matching.group(2)
            self.intro = tag['href']
            self.check = True

    def set_score(self, tag):
        if tag.find(class_='score'):
            raw = tag.find(class_='score').get_text()
            if raw:
                try:
                    self.score = float(re.search('\((.+?)\)', raw).group(1))
                except AttributeError:
                    print(self.zip_id)

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
                self.set_score(soup)
                self.set_star(soup)
                self.set_category(soup)
                self.set_image(soup)
                self.set_name(soup)
            elif soup.find(text="搜寻没有结果。"):
                result = "Could not find " + self.zip_id + " in JAV"
                print(result)
                self.remark = 'No results'
            else:
                result = "There are many videos for " + self.zip_id + " in JAV"
                print(result)
                self.remark = 'Too many results'
        except requests.ConnectionError as e:
            print("Couldn't access " + self.zip_id + " profile")
            print(e)
            raise requests.ConnectionError

    def get_intro(self):
        try:
            torrent_data = request(caoliu_host, self.intro, cookies=cookie)
            torrent_data.encoding = 'gbk'
            soup = BeautifulSoup(torrent_data.text, 'lxml')
            self.set_torrent(soup)
        except requests.ConnectionError as e:
            print("Couldn't enter intro page and download torrent")
            print(e)
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
                print("Could not download " + image_name)
        except requests.ConnectionError as e:
            print("Couldn't access to image page due to NetError")
            raise requests.ConnectionError


def crawling(page):
    for i in page:
        index_payload = {'fid': 15, 'page': i}
        try:
            req = request(caoliu_host, caoliu_index_router, params=index_payload, cookies=cookie)
        except requests.ConnectionError as e:
            time.sleep(10)
            print("Couldn't access to index page " + str(i))
            continue
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
                    video_record = db.Choice.create_or_get(zip_id=video.zip_id, name=video.name, star=' '.join(video.star),
                                                           category=' '.join(video.category), score=video.score,
                                                           image=video.image, torrent=video.torrent, remark=video.remark)
                except requests.ConnectionError as e:
                    time.sleep(10)
                    print("")
                    continue


def building_thread():
    threads = []
    arg1 = list(range(1, 31))
    arg2 = list(range(31, 51))
    arg3 = list(range(51, 71))

    t1 = threading.Thread(target=crawling, name='Thread_1', args=[arg1])
    threads.append(t1)
    t2 = threading.Thread(target=crawling, name='Thread_2', args=[arg2])
    threads.append(t2)
    t3 = threading.Thread(target=crawling, name='Thread_3', args=[arg3])
    threads.append(t3)
    return threads


if __name__ == "__main__":
    threads_begin = building_thread()
    for t in threads_begin:
        t.setDaemon(True)
        t.start()
    t.join()
