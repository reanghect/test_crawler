import requests
from bs4 import BeautifulSoup
import shutil
import data_source as db
import time
import os.path
import multiprocessing
import logging
import Album
from crawlerHelper import request, get_config


caoliu_host = get_config('WebURL', 'MainHost')
caoliu_index_router = get_config('WebURL', 'IndexRouter')
library_host = get_config('WebURL', 'LibraryHost')
library_router = get_config('WebURL', 'LibraryRouter')

cookie = dict()
with open("cookie", 'r') as f:
    for line in f:
        cook_list = line.rstrip().split("\t")
        cookie[cook_list[0]] = cook_list[1]

logger = logging.getLogger('crawler.Album')


def image(album):
    if album.image is not None:
        try:
            image_raw = request('http:' + album.image, flag='file')
            image_name = album.zip_id + '.jpg'
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
    index_payload = {'fid': 26, 'page': page}

    try:
        record_add = caoliu_host + caoliu_index_router
        req = request(record_add, params=index_payload, cookies=cookie)
    except requests.ConnectionError as e:
        time.sleep(50)
        logger.error(e)
        logger.error("Couldn't access to index page " + str(page))
        return
    req.encoding = 'gbk'
    soup = BeautifulSoup(req.text, 'lxml')
    link = soup.find_all('a')
    for l in link:
        video = Album.Album()
        video.init_zip_id(l)
        if video.check is True:
            try:
                video.get_profile(library_host+library_router)
                video.get_intro(caoliu_host, cookie)
                image(video)
                db.Choice.create_or_get(zip_id=video.zip_id, name=video.name, star=' '.join(video.star),
                                        category=' '.join(video.category), score=video.score,
                                        image=video.image, torrent=video.torrent, remark=video.remark)
            except Exception as e:
                time.sleep(50)
                logger(e)
                continue


if __name__ == "__main__":
    # pool = multiprocessing.Pool(processes=3)
    # for page_number in range(1, 600):
    #     pool.apply_async(crawling, (page_number, ))
    logger.info('Ready to craw AV in 2 processes')
    # pool.close()
    # pool.join()
    for page_number in range(1, 600):
        crawling(page_number)
    logger.info('All AV loaded into database')
