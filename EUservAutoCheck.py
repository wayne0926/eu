import os
import json
import time
import requests
from bs4 import BeautifulSoup

# 账号信息
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
# 代理设置
PROXIES = {
    "http": "http://127.0.0.1:80",
    "https": "http://127.0.0.1:80"
}


def login(username, password) -> (str, requests.session):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/83.0.4103.116 Safari/537.36",
        "origin": "https://www.euserv.com"
    }
    login_data = {
        "email": username,
        "password": password,
        "form_selected_language": "en",
        "Submit": "Login",
        "subaction": "login"
    }
    url = "https://support.euserv.com/index.iphp"
    session = requests.Session()
    f = session.post(url, headers=headers, data=login_data)
    f.raise_for_status()
    if f.text.find('Hello') == -1:
        return '-1', session
    # print(f.request.url)
    sess_id = f.request.url[f.request.url.index('=') + 1:len(f.request.url)]
    return sess_id, session


def get_servers(sess_id, session) -> {}:
    d = {}
    url = "https://support.euserv.com/index.iphp?sess_id=" + sess_id
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/83.0.4103.116 Safari/537.36",
        "origin": "https://www.euserv.com"
    }
    f = session.get(url=url, headers=headers)
    f.raise_for_status()
    soup = BeautifulSoup(f.text, 'html.parser')
    for tr in soup.select('#kc2_order_customer_orders_tab_content_1 .kc2_order_table.kc2_content_table tr'):
        server_id = tr.select('.td-z1-sp1-kc')
        if not len(server_id) == 1:
            continue
        flag = True if tr.select('.td-z1-sp2-kc .kc2_order_action_container')[
            0].get_text().find('Contract extension possible from') == -1 else False
        d[server_id[0].get_text()] = flag
    return d


def renew(sess_id, session, password, order_id) -> bool:
    url = "https://support.euserv.com/index.iphp"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/83.0.4103.116 Safari/537.36",
        "Host": "support.euserv.com",
        "origin": "https://support.euserv.com",
        "Referer": "https://support.euserv.com/index.iphp"
    }
    data = {
        "Submit": "Extend contract",
        "sess_id": sess_id,
        "ord_no": order_id,
        "subaction": "choose_order",
        "choose_order_subaction": "show_contract_details"
    }
    session.post(url, headers=headers, data=data)
    data = {
        "sess_id": sess_id,
        "subaction": "kc2_security_password_get_token",
        "prefix": "kc2_customer_contract_details_extend_contract_",
        "password": password
    }
    f = session.post(url, headers=headers, data=data)
    f.raise_for_status()
    if not json.loads(f.text)["rs"] == "success":
        return False
    token = json.loads(f.text)["token"]["value"]
    data = {
        "sess_id": sess_id,
        "ord_id": order_id,
        "subaction": "kc2_customer_contract_details_extend_contract_term",
        "token": token
    }
    session.post(url, headers=headers, data=data)
    time.sleep(5)
    return True


def check(sess_id, session):
    logToFile(filePath, "Checking.......")
    d = get_servers(sess_id, session)
    flag = True
    for key, val in d.items():
        if val:
            flag = False
            logToFile(filePath, "ServerID: %s Renew Failed!" % key)
    if flag:
        logToFile(filePath, "ALL Work Done! Enjoy")


def logToFile(filePath, *words) -> bool:
    with open(filePath, 'a+', encoding="utf8")as f:
        for word in words:
            print(word, file=f, end="")
        print(file=f)
        return True
    return False


if __name__ == "__main__":
    pwd = os.getcwd()
    filePath = os.path.join(pwd, "EUserLog.txt")
    logToFile(filePath, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    if not USERNAME or not PASSWORD:
        logToFile(filePath, "你没有添加任何账户")
        exit(1)
    user_list = USERNAME.split(',')
    passwd_list = PASSWORD.split(',')
    if len(user_list) != len(passwd_list):
        logToFile(filePath, "The number of usernames and passwords do not match!")
        exit(1)
    for i in range(len(user_list)):
        logToFile(filePath, '*' * 30)
        logToFile(filePath, "正在续费第 %d 个账号" % (i + 1))
        sessid, s = login(user_list[i], passwd_list[i])
        if sessid == '-1':
            logToFile(filePath, "第 %d 个账号登陆失败，请检查登录信息" % (i + 1))
            continue
        SERVERS = get_servers(sessid, s)
        logToFile(filePath, "检测到第 {} 个账号有 {} 台VPS，正在尝试续期".format(
            i + 1, len(SERVERS)))
        for k, v in SERVERS.items():
            if v:
                if not renew(sessid, s, passwd_list[i], k):
                    logToFile(filePath, "ServerID: %s Renew Error!" % k)
                else:
                    logToFile(
                        filePath, "ServerID: %s has been successfully renewed!" % k)
            else:
                logToFile(
                    filePath, "ServerID: %s does not need to be renewed" % k)
        time.sleep(15)
        check(sessid, s)
        time.sleep(5)
    logToFile(filePath, '*' * 30+"\n")
