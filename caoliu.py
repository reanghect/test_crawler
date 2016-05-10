import requests
from bs4 import BeautifulSoup
import re
import shutil

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


def request(host, router=None, flag='url', **kwargs):
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
        if flag == 'url':
            req = requests.get(url, headers=headers, proxies=proxy, **kwargs)
        else:
            req = requests.get(url, headers=headers, proxies=proxy, stream=True, **kwargs)
        return req
    except ConnectionError as e:
        print(e)
        print("傻逼断网了")
        raise InterruptedError


class Album(object):
    def __init__(self, zip_id, intro):
        self.zip_id = zip_id
        self.intro = intro
    #   TODO USE children methods to navigate quickly
    @staticmethod
    def get_code_intro(tag):
        matching = re.search(code_rule, str(tag.contents))
        if re.search(filter_rule, str(tag.contents)) and matching:
            code = matching.group(1) + matching.group(2)
            intro = tag['href']
        return code, intro

    @staticmethod
    def score(tag):
        if tag.find(class_='score'):
            raw = tag.find(class_='score').contents
            if len(raw) != 0:
                score = float(re.search('\((.+?)\)', str(raw)).group(1))
        else:
            score = 0

    @staticmethod
    def star(tag):
        if tag.find('span', class_="star"):
            star = tag.find('span', class_="star").find(rel='tag').contents
        else:
            star = "unknown"
        return star
    @staticmethod
    def name(tag):
        if tag.find(class_="post-title text"):
            raw = tag.find(class_="post-title text").contents
            name = re.search('[A-Z]{3,5}-?[0-9]{3,5}\s(.+?)</a>', str(raw)).group(1)
        else:
            name = "unknown"
        return name

    @staticmethod
    def category(tag):
        cate = []
        if tag.find_all(rel='category tag'):
            raw = tag.find_all(rel='category tag')
            for cat in raw:
                cate.append(re.search('tag">(.+?)</a>', str(cat)).group(1))
        return cate

    def get_profile(self):
        profile_data = request(library_host, library_router, params={'keyword': self.zip_id})
        soup = BeautifulSoup(profile_data.text, 'lxml')
        if soup.find(class_="videos") is None:
            score = self.score(soup)


    #         clean_data[code] = {
    #             "category": cate, "name": name, "star": star, "score": score}
    #         image_data[code] = image_link
    #     elif soup.find(text="搜寻没有结果。"):
    #         result = "Could not find " + code + " in JAV"
    #         print(result)
    #         clean_data[code] = result
    #     else:
    #         result = "There are many videos for " + code + " in JAV"
    #         print(result)
    #         clean_data[code] = result
    #
    # def get_torrent(self, intro):




def fanhao(page):
    index_payload = {'fid': 15, 'page': page}
    req = request(caoliu_host, caoliu_index_router, params=index_payload, cookies=cookie)
    req.encoding = 'gbk'
    soup = BeautifulSoup(req.text, 'lxml')
    link = soup.find_all('a')
    code_base = set()
    intro_data = dict()
    for l in link:
        zip_id = Album.get_code(l)
        for code in zip_id:
            video = Album(code)
        map(Album.get_profile, zip_id)
        if re.search(filter_rule, str(l.contents)) and re.search(code_rule, str(l.contents)):
            code = re.search(code_rule, str(l.contents)).group()
            code_base.add(code)
            intro_router = l['href']
            intro_data[code] = intro_router
    return intro_data, code_base


def jav_profile(codebase):
    clean_data = dict()
    image_data = dict()
    for code in codebase:
        profile_data = request(library_host, library_router, params={'keyword': code})
        soup = BeautifulSoup(profile_data.text, 'lxml')
        if soup.find(class_="videos") is None:
            # Score of AV
            score = soup.find(class_="score").contents
            if len(score) == 0:
                score = 0
            else:
                score = float(re.search('\((.+?)\)', str(score)).group(1))
            # Image Link of AV
            image_link = soup.find(id="video_jacket_img")['src']
            # Star of AV
            star = soup.find('span', class_="star")
            if star is not None:
                star = re.search('rel="tag">(.+?)</a', str(star)).group(1)
            else:
                star = "UNKNOWN"
            # AV Name
            name = soup.find(class_="post-title text").contents
            name = re.search('[A-Z]{3,5}-?[0-9]{3,5}\s(.+?)</a>', str(name)).group(1)
            # Category Name
            category = soup.find_all(rel='category tag')
            cate = []
            for cat in category:
                cate.append(re.search('tag">(.+?)</a>', str(cat)).group(1))

            clean_data[code] = {
                "category": cate, "name": name, "star": star, "score": score}
            image_data[code] = image_link
        elif soup.find(text="搜寻没有结果。"):
            result = "Could not find " + code + " in JAV"
            print(result)
            clean_data[code] = result
        else:
            result = "There are many videos for " + code + " in JAV"
            print(result)
            clean_data[code] = result
    return clean_data, image_data


# def torrent(intro_data):
#     # TODO Download torrent and save data to database
#     intro = request(caoliu_host, data[code]["torrent"], cookies=cookie)
#     torrent_link = intro_data.find_all(href=True, text=True)
#     for download in torrent_link:
#         if re.search('(http://www\.rmdown\.com)/link', str(download.contents)) is not None:
#             # TODO where is the torrent
#             torrent_viidii = re.search('[\'(.+?)\']', str(download.contents)).group()
#     with open(code + '.text', 'w') as t:
#         t.write(str(data[code]))
#         if torrent_viidii is not None:
#             t.write("torrent_link: " + torrent_viidii)
#         t.close()


def image(image_data):
    for code in image_data.keys():
        image_raw = request(image_data[code], flag='file')
        image_name = code + '.jpg'
        if image_raw.status_code == 200:
            with open(image_name, 'wb') as j:
                image_raw.raw.decode_content = True
                shutil.copyfileobj(image_raw.raw, j)
            j.close()
        else:
            print("Could not download " + image_name)


# if __name__ == "__main__":
#     for i in range(1, 50):
#         torrent(fanhao(i))


