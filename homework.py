import gzip
import json
import re
import time
from io import BytesIO

import brotli
import requests
from lxml import etree
from seleniumwire import webdriver

'''
    该脚本使用selenium-wire库，selenium库，requests库，lxml库，gzip库，brotli库
    其中selenium-wire库用于拦截请求，requests库用于发送请求，lxml库用于解析html，gzip库用于解码gzip压缩的响应体，brotli库用于解码brotli压缩的响应体
    selenium-wire是selenium的一个扩展库，可以拦截请求，获取请求头，请求体，响应头，响应体等信息
    其依赖于blinker库，所以需要先安装blinker库
    且blinker的版本必须小于1.8.0，否则会报错
'''


def modify_request(request, referer):
    browser_referer = request.headers['Referer']
    if browser_referer == referer:
        print(f"截获的请求: {request.url}")


class myBrowser:
    def __init__(self, browser, path):
        self.token = None
        self.cookies = None
        self.browser = browser
        self.browser.get(path)
        self.url = self.browser.current_url
        self.UA = self.browser.execute_script("return navigator.userAgent")

    def login(self, username, password):
        self.browser.find_element('name', 'email').send_keys(username)
        self.browser.find_element('name', 'password').send_keys(password)
        self.browser.find_element('css selector', "div.column.is-6").click()
        self.cookies = self.browser.get_cookies()
        time.sleep(0.5)
        self.token = self.browser.execute_script('return localStorage.getItem("token")')
        print(f'-------------------登录成功-------------------')

    def gotoPage(self, by, value):
        # 设置隐式等待时间 防止找不到元素
        self.browser.implicitly_wait(10)
        try:
            self.browser.find_element(by, value).click()
        except Exception as e:
            print(e)
            print('Cannot find the element')
        # 刷新当前浏览器所在网址
        self.url = self.browser.current_url

    def get_answer(self, referer):
        time.sleep(3)
        global code, parsed_data
        self.browser.request_interceptor = lambda request: modify_request(request, referer)
        for request in self.browser.requests:
            if request.response and request.headers['Referer'] == referer:
                # print(f"URL: {request.url}")
                # print(f"Status Code: {request.response.status_code}")
                # print(f"Headers: {request.headers}")
                # print(f"Response Headers: {request.response.headers}")
                try:
                    decoded_body = decode_response_body(request.response)
                    # print(f"Decoded Body: {decoded_body}")
                    try:
                        parsed_data = json.loads(decoded_body)['data']['explanation_content']
                    except KeyError:
                        print('No explanation content found')
                        try:
                            parsed_data = json.loads(decoded_body)['data']['code']
                            print(f"Code: {parsed_data}")
                            return parsed_data
                        except KeyError:
                            print('No code found')
                            return
                    except json.JSONDecodeError:
                        print('Failed to parse response body as JSON')
                    try:
                        html = etree.HTML(parsed_data)
                        code = html.xpath("//pre/code/text()")[0]
                        print(f"Code: {code}")
                        return code
                    except IndexError:
                        print('No code found')
                except UnicodeDecodeError as e:
                    print(f"Failed to decode response body: {e}")

    def get_page_content(self):
        return self.browser.page_source


def write_to_file(filename, data):
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(data)


def send_answer(answer):
    headers = {'Authorization': f'Bearer {browser.token}', 'User-Agent': browser.UA}
    data = {'code': answer}
    print(f'data:{data}')

    # 解析url，合成PUT请求需要的url
    result = re.findall(r'www.python123.io/\S+#', browser.url)[0][17:]
    url = 'https://www.python123.io/api/v1/' + re.findall(r'\S+/problems', result)[0] + re.findall(r'/\d+#', result)[0][
                                                                                        :-1] + '/code'
    print('-------------------开始上传答案-------------------')
    print(f'url:{url}')
    # 开始发送PUT请求
    response = requests.put(data=json.dumps(data), url=url, headers=headers)
    print(f'response:{response.text}')
    if response.status_code == 200:
        print('-------------------答案上传成功-------------------')
    else:
        print('-------------------答案上传失败-------------------')


def finish_homework(browser, amount: int):
    for i in range(1, amount + 1):
        browser.gotoPage('xpath', f'//div[@class="contrib-blocks"]/div[{i}]')
        browser.browser.implicitly_wait(10)
        # 在这里设置请求拦截
        answer = browser.get_answer(re.findall(r'\S+#', browser.url)[0][:-1])
        # 通过requests向服务器发送答案
        if answer:
            time.sleep(0.5)
            # 将答案上传服务器
            send_answer(answer)
            # 将答案写入文件
            write_to_file('../answer.md', f'# 第{i}题：\n ```' + answer + ' \n```\n\n')
        if answer:
            print(f'---------------第{i}个作业完成-----------------')
        else:
            print(f'---------------第{i}个作业失败-----------------')

        # 防止卡bug
        time.sleep(1)
        browser.browser.back()


# 解码响应体 事实上python123使用gzip压缩
def decode_response_body(response):
    content_encoding = response.headers.get('Content-Encoding', '')
    body = response.body
    if 'gzip' in content_encoding:
        print("Response is gzip encoded")
        buf = BytesIO(body)
        with gzip.GzipFile(fileobj=buf) as f:
            return f.read().decode('utf-8')
    elif 'br' in content_encoding:
        print("Response is brotli encoded")
        return brotli.decompress(body).decode('utf-8')
    else:
        return body.decode('utf-8')


url = 'https://www.python123.io/index/login'

# 设置浏览器参数
options = webdriver.ChromeOptions()
browser = myBrowser(webdriver.Chrome(seleniumwire_options={}, options=options), url)

# 登录
browser.login('用户名', '密码')

# 进入作业页面
browser.gotoPage('css selector', 'img.image')
browser.gotoPage('css selector', 'svg.color-icon.mr-1.-ml-1')

# homework_number = int(input('请选择需要完成得作业：'))
homework_number = 2

# 通过xpath选择器找到相应作业 现在默认选择第二个作业 后期可以通过输入选择
browser.gotoPage('xpath',
                 "//div[@class='tasks-section tasks-homework']//div[@class='columns is-multiline']/div[@class='column "
                 f"is-4-desktop is-3-fullhd'][{homework_number}]")

cookie_dit = {}
for dic in browser.cookies:
    key = dic['name']
    value = dic['value']
    cookie_dit[key] = value
time.sleep(0.5)
# cookie_dit['token'] = browser.browser.execute_script('return localStorage.getItem("token")')

# 用xpath解析页面，获取题目数量
html = etree.HTML(browser.get_page_content())
# 获取题目数量
amount = int(html.xpath("//div[@class='contrib-blocks']/div[last()]/span[text()]")[0].text)
finish_homework(browser, amount)

# 关闭浏览器
browser.browser.quit()
