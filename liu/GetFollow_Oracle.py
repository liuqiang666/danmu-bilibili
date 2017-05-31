#-*- coding=utf-8 -*-
# 抓取B站用户的关注id

"""
UID，用户名，关注数，关注用户UID
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

oracleHost = '127.0.0.1'
oracleUser = 'bilibili'
oraclePassword = '123456'
oracleDatabaseName = 'orcl'
oracleConn = oracleUser + '/' + oraclePassword + '@' + oracleHost + '/' + oracleDatabaseName
conn = cxo.connect(oracleConn)
cur = conn.cursor()

# 获取用户网页数据
def getSoup(start, stop):

    try:
        for number in range(start, stop+1):

            url = 'http://space.bilibili.com/'+str(number)+'/#!/'
            dcap = dict(DesiredCapabilities.PHANTOMJS)
            dcap["phantomjs.page.settings.userAgent"] = (
                "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0"
            )
            dcap["phantomjs.page.settings.loadImages"] = False  #不加载图片，加快速度
            driver = webdriver.PhantomJS(executable_path='D:\\Chrome\\phantomjs-2.1.1-windows\\phantomjs-2.1.1-windows\\bin\\phantomjs.exe',
                                         desired_capabilities=dcap)
            driver.get(url)
            content = driver.page_source  # 获取网页内容
            driver.close()
            driver.quit()  #及时关闭，否则会造成内存溢出
            soup = BeautifulSoup(content, 'lxml')
            username= getInfo(soup)  # 获取用户名
            uid = number  # number即为uid
            get_gz_uid = GetFollowUid(number)
            gzsuid, gznumber = get_gz_uid.get_uids()  # 获取关注id和关注数量

            saveData(uid, username, gznumber, gzsuid)  # 插入数据库
    except Exception:
        print("get page error")
        return getSoup(number+1, stop+1)


# 提取信息
def getInfo(soup):

    try:
        # 用户名
        username = str(soup.find_all(attrs={'id': 'h-name'})[0].contents[0])
        return username
    except Exception:
        print("get info error")


# 存入数据库
def saveData(uid, username, gznumber, gzsuserid):
    try:
        cur.execute("insert into bilibili_usergz(id ,userid, username, gznumber, gzsuserid)"
                    "values(usergz_seq.Nextval, '%d', '%s', '%f', '%s')"
                    % (uid, username, gznumber, gzsuserid))
        cur.execute("commit")
        print('插入数据库:', username)
    except Exception:
        print("save error")


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
            return self._get_page(page_number)

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
            print(" get uid error")
        finally:
            return self._follow_ids, follownumber


def main():
    try:
        start = getMaxUid()
        if start == None:
            start = 0
        stop = start + 100
        print(start, stop)
        getSoup(start+1, stop)
    finally:
        cur.close()
        conn.close()


if __name__=='__main__':
    main()

