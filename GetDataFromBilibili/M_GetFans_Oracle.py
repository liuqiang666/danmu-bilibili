#-*- coding=utf-8 -*-
# 抓取B站用户的粉丝id，多进程并发版

"""
UID，用户名，粉丝数，粉丝UID
"""

import cx_Oracle as cxo
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from urllib.parse import urlencode
from requests.exceptions import RequestException
from json import JSONDecodeError
import requests
import json
import time
from multiprocessing import Pool

oracleHost = '127.0.0.1'
oracleUser = 'bilibili'
oraclePassword = '123456'
oracleDatabaseName = 'orcl'
oracleConn = oracleUser + '/' + oraclePassword + '@' + oracleHost + '/' + oracleDatabaseName
conn = cxo.connect(oracleConn)
cur = conn.cursor()

# 提取信息
def getInfo(soup):

    try:
        # 用户名
        username = str(soup.find_all(attrs={'id': 'h-name'})[0].contents[0])
        return username
    except Exception:
        print("get info error")


# 存入数据库
def saveData(uid, username, fansnumber, fansuserid):
    try:
        cur.execute("insert into bilibili_userfans(id ,userid, username, fansnumber, fansuserid)"
                    "values(userfans_seq.Nextval, '%d', '%s', '%f', '%s')"
                    % (uid, username, fansnumber, fansuserid))
        cur.execute("commit")
        print('插入数据库:', username)
    except Exception:
        print("save error")


# 得到最大的uid
def getMaxUid():
    cur.execute('select max(userid) from bilibili_userfans')
    return cur.fetchone()[0]


class GetFansUid(object):
    def __init__(self, mid):
        self._fans_ids = ""
        self._mid = mid

    def _get_page(self, page_number):
        data = {
            'mid': str(self._mid),
            'page': str(page_number),
            '_': '1496132105785'
        }
        pages = 0
        fansnumber = 0
        fans_ids = ""
        try:
            url = "http://space.bilibili.com/ajax/friend/GetFansList?" + urlencode(data)
            response = requests.get(url)
            if response.status_code != 200:
                return None
            html_cont = response.text
            try:
                data = json.loads(html_cont)
                if data and (data.get('status') is True):
                    if data and 'data' in data.keys():
                        if(page_number == 1):
                            pages = data.get('data').get('pages')
                            fansnumber = data.get('data').get('results')
                        for fans in data.get('data').get('list'):
                            fans_ids = str(fans.get('fid')) + ',' + fans_ids
                elif (data.get('data') == "粉丝列表中没有值"):
                    pages = 0
                    fansnumber = 0
            except JSONDecodeError:
                pass
            self._fans_ids = fans_ids + self._fans_ids
            return pages, fansnumber
        except RequestException:
            return self._get_page(page_number)

    def get_uids(self):
        fansnumber = 0
        try:
            pages, fansnumber = self._get_page(1)  # 获取总页数和粉丝数量
            if(fansnumber != 0):  # 粉丝数量不为0就开始爬取
                if(pages < 6):   # 不超过5页
                    for i in range(2, pages + 1):
                        self._get_page(i)
                else:
                    for i in range(2, 6):  #超过5页，暂且先爬取前五页
                        self._get_page(i)
        except Exception:
            print(" get uid error")
        finally:
            return self._fans_ids, fansnumber

def main(number):
    url = 'http://space.bilibili.com/' + str(number) + '/#!/'
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = (
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0"
    )
    dcap["phantomjs.page.settings.loadImages"] = False  # 不加载图片，加快速度
    driver = webdriver.PhantomJS(executable_path='G:\\Anaconda3\\phantomjs\\bin\\phantomjs.exe',
                                 desired_capabilities=dcap)
    try:
        driver.get(url)
        content = driver.page_source  # 获取网页内容
        driver.close()
        driver.quit()  # 及时关闭，否则会造成内存溢出
        soup = BeautifulSoup(content, 'lxml')
        username = getInfo(soup)  # 获取用户名
        uid = number  # number即为uid
        get_fans_uid = GetFansUid(number)
        fansuid, fansnumber = get_fans_uid.get_uids()  # 获取粉丝id和粉丝数量

        saveData(uid, username, fansnumber, fansuid)  # 插入数据库
    except Exception:
        pass
    finally:
        if driver:
            driver.quit()

if __name__=='__main__':
    time1 = time.time()

    start = getMaxUid()  # 抓取范围
    stop = start + 500
    print(start, stop)

    try:
        pool = Pool(processes=10)  # 设定并发进程的数量
        pool.map(main, (i for i in range(start+1, stop+1)))
    except Exception:
        pass

    time2 = time.time()
    print((time2 - time1) / 60, u"分钟")