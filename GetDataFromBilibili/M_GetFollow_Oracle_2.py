#-*- coding=utf-8 -*-
# 抓取B站用户的关注id

"""
UID，用户名，关注数，关注用户UID
"""
import random

from bs4 import BeautifulSoup
from urllib.parse import urlencode
from requests.exceptions import RequestException
from multiprocessing import Pool
from json import JSONDecodeError
from urllib import request
import cx_Oracle as cxo
import requests
import json
import time
import urllib.parse

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
        # print("get info error")
        pass


# 存入数据库
def saveData(uid, username, gznumber, gzsuserid):
    try:
        cur.execute("insert into bilibili_usergz(id ,userid, username, gznumber, gzsuserid)"
                    "values(usergz_seq.Nextval, '%d', '%s', '%f', '%s')"
                    % (uid, username, gznumber, gzsuserid))
        cur.execute("commit")
        print(uid, username)
    except Exception:
        # print("save error")
        pass


# 得到最大的uid
def getMaxUid():
    cur.execute('select max(userid) from bilibili_usergz')
    return cur.fetchone()[0]


class GetFollowUid(object):
    def __init__(self, mid):
        self._follow_ids = ""
        self._mid = mid

    def _get_page(self, page_number):
        data = {
            'mid': str(self._mid),
            'page': str(page_number),
            '_': '1496211796946'
        }
        pages = 0
        follownumber = 0
        follow_ids = ""
        try:
            # url
            # http://space.bilibili.com/ajax/friend/GetAttentionList?mid=12266&page=1&_=1496211796946
            url = "http://space.bilibili.com/ajax/friend/GetAttentionList?" + urlencode(data)
            # print(url)
            # 请求网页
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
                            follownumber = data.get('data').get('results')
                        for follow in data.get('data').get('list'):
                            follow_ids = str(follow.get('fid')) + ',' + follow_ids
                elif (data.get('data') == "关注列表中没有值"):
                    pages = 0
                    follownumber = 0
            except JSONDecodeError:
                pass
            self._follow_ids = follow_ids + self._follow_ids
            # print(self._follow_ids)
            return pages, follownumber
        except RequestException:
            # return self._get_page(page_number)
            pass

    def get_uids(self):
        follownumber = 0
        try:
            pages, follownumber = self._get_page(1)# 获取总页数和关注数量
            if(follownumber != 0):# 关注数量不为0就开始爬取
                if(pages < 6): # 不超过5页
                    for i in range(2, pages + 1):
                        self._get_page(i)
                else:
                    for i in range(2, 6):#超过5页，暂且先爬取前五页
                        self._get_page(i)
        except Exception:
            # print(" get uid error")
            pass
        finally:
            return self._follow_ids, follownumber


def main(number):
    url = 'http://space.bilibili.com/'+str(number)+'/#!/'
    try:
        # response = request.urlopen(url)
        # # print(response.getcode())
        # html_cont = response.read()
        data = {}
        params = urllib.parse.urlencode(data).encode(encoding='UTF8')
        req = urllib.request.Request("%s?%s" % (url, params))
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64)",
            'Referer': 'http://www.bing.com/'
        }
        for i in headers:
            req.add_header(i, headers[i])
        response = urllib.request.urlopen(req)
        html_cont = response.read()

        soup = BeautifulSoup(html_cont, 'lxml', from_encoding='utf-8')
        username = soup.find("h1").get_text().strip()[:-6]  # 获取用户名
        uid = number  # number即为uid
        get_gz_uid = GetFollowUid(number)
        gzsuid, gznumber = get_gz_uid.get_uids()  # 获取关注id和关注数量

        saveData(uid, username, gznumber, gzsuid)  # 插入数据库

        # print(uid, username, gznumber, gzsuid)

        time.sleep(random.uniform(1, 5))  # 更据动态网页加载耗时，此处为随机时间
    except Exception:
        pass


if __name__ == '__main__':
    time1 = time.time()

    start = getMaxUid()  # 抓取范围
    if start == None:
        start = 1
    stop = start + 50000
    print(start, stop)

    try:
        pool = Pool(processes=10)  # 设定并发进程的数量
        pool.map(main, (i for i in range(start+1, stop+1)))
    except Exception:
        pass

    time2 = time.time()
    print((time2 - time1) / 60, u"分钟")

