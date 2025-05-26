import shutil
import tempfile
from sys import prefix

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import json
import csv
import os
from datetime import datetime


class DuanShuCrawler_vzan:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)  # 设置为False可以看到浏览器操作
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.liveroom_list_url = "https://live-liveapi.vzan.com/api/v1/topic/get_topicdatas"
        self.liveroom_url_prefix = "https://inter.dayilive.com/live/page/"
        self.topic_url_prefix = "https://live-play.vzan.com/api/topic/topic_config?isPcBrowser=true&topicId="

        self.liveroomlist_batchsize = 100
        self.liveroom_details_batchsize = 500
        self.timeout = 10

        import tempfile
        import platform

        # 获取系统临时文件夹路径
        if platform.system() == 'Windows':
            # Windows: C:\Users\<username>\AppData\Local\Temp\duanshu_crawler
            self.temp_dir = os.path.join(tempfile.gettempdir(), 'vzan_crawler')
        else:
            # Linux: /tmp/duanshu_crawler
            self.temp_dir = os.path.join(tempfile.gettempdir(), 'vzan_crawler')

        # 所有文件都放在临时文件夹下
        self.liveroom_list_savefile = os.path.join(self.temp_dir, "liveroomlist_vzan.csv")
        self.liveroom_details_savefile = os.path.join(self.temp_dir, "liveroom_elements_vzan.csv")
        self.liveroom_watchers_savefile_prefix = "liveroom_watchers_vzan"
        self.liveroom_watchers_savedir = os.path.join(self.temp_dir, "watchers_vzan")

        #用于记录每次爬取时获取的新增直播间id， 第一次爬取将获取所有的直播间id
        self.liveroom_list_savefile_inc = os.path.join(self.temp_dir, "liveroomlist_inc_vzan.csv")
        self.liveroom_details_savefile_inc = os.path.join(self.temp_dir, "liveroomlist_elements_inc_vzan.csv")

        self.failed_liveroomlist_url = os.path.join(self.temp_dir, 'failed_liveroomlist_urls_vzan.txt')
        self.failed_liveroomdetails_url = os.path.join(self.temp_dir, 'failed_liveroomdetails_urls_vzan.txt')
        self.failed_liveroom_watchers_url = os.path.join(self.temp_dir, 'failed_watchers_urls_vzan.txt')

        # 初始化logger为None
        # 设置日志
        self.logger = None
        self.log_file = None

        self.create_storage()
        self.setup_logging()


    def create_storage(self):
        # 设置临时文件夹
        # 创建临时文件夹
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            print(f"创建临时文件夹: {self.temp_dir}")

        if not os.path.exists(self.liveroom_watchers_savedir):
            os.makedirs(self.liveroom_watchers_savedir)
            print(f"创建watchers文件夹: {self.liveroom_watchers_savedir}")

    def setup_logging(self):
        """配置日志系统，使用系统临时文件夹存储日志"""
        import logging
        from datetime import datetime
        import os

        # 生成日志文件名
        log_filename = f'vzan_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        log_file = os.path.join(self.temp_dir, log_filename)

        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()  # 同时输出到控制台
            ]
        )
        self.logger = logging.getLogger(__name__)
        #print(f"日志文件路径: {log_file}")

        # 保存日志文件路径，方便后续查看
        self.log_file = log_file

    def get_liveroom_list(self, authorization_token, page=1, psize=10, state=-2, keytype=1, keyword="", tag=0,
                              livescene=-1, typeid=-1, types=-1, chanid=0, isOnShelf=-1, isHQOut=0, isGHHQOut=0,
                              starttime="", endtime=""):
        """
        直接调用API获取直播间列表数据

        Args:
            authorization_token (str): JWT token
            page (int): 页码，默认1
            psize (int): 每页数量，默认10
            state (int): 状态，-2表示全部，默认-2
            keytype (int): 关键词类型，默认1
            keyword (str): 搜索关键词，默认空
            tag (int): 标签，默认0
            livescene (int): 直播场景，默认-1
            typeid (int): 类型ID，默认-1
            types (int): 类型，默认-1
            chanid (int): 频道ID，默认0
            isOnShelf (int): 是否上架，默认-1
            isHQOut (int): 是否高清，默认0
            isGHHQOut (int): 是否更高清，默认0
            starttime (str): 开始时间，默认空
            endtime (str): 结束时间，默认空

        Returns:
            dict: API响应数据
        """
        try:
            import requests
            import json

            self.logger.info(f"正在获取第{page}页数据...")

            # 准备请求头
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9',
                'admin-token': 'undefined',
                'appcode': 'agent_setting',
                'authorization': f'Bearer {authorization_token}',
                'content-type': 'application/json;charset=UTF-8',
                'generalizeshopid': '0',
                'lid': '11749549',
                'origin': 'https://live.vzan.com',
                'referer': 'https://live.vzan.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'zbid': '11749549'
            }

            # 准备请求数据
            data = {
                "keyword": keyword,
                "keytype": keytype,
                "state": state,
                "psize": psize,
                "tag": tag,
                "page": page,
                "livescene": livescene,
                "typeid": typeid,
                "types": types,
                "chanid": chanid,
                "isOnShelf": isOnShelf,
                "isHQOut": isHQOut,
                "isGHHQOut": isGHHQOut,
                "starttime": starttime,
                "endtime": endtime
            }

            # 发送请求
            url = self.liveroom_list_url
            response = requests.post(url, headers=headers, json=data, timeout=self.timeout)

            # 检查响应状态
            if response.status_code == 200:
                self.logger.info(f"成功获取第{page}页数据")
                return response.json()
            else:
                self.logger.error(f"请求失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"获取数据时出错: {str(e)}")
            return None



    def login(self, username, password):
        """登录短书"""
        try:
            self.logger.info("正在登录短书...")
            self.page.goto(self.liveroom_list_url)

            # 等待页面完全加载
            self.page.wait_for_load_state('networkidle')
            time.sleep(3)  # 等待页面完全加载

            # 等待登录表单加载
            self.logger.info("等待登录表单加载...")

            # 首先等待并点击"账号登录"按钮
            try:
                # 等待账号登录按钮出现
                self.logger.info("等待账号登录按钮出现...")

                # 使用JavaScript检查页面元素
                self.logger.info("检查页面元素...")
                page_content = self.page.content()
                self.logger.info(f"页面内容: {page_content[:500]}")  # 只打印前500个字符

                # 等待页面加载完成
                self.page.wait_for_load_state('domcontentloaded')
                time.sleep(2)

                # 尝试使用JavaScript点击账号登录按钮
                self.logger.info("尝试使用JavaScript点击账号登录按钮...")
                clicked = self.page.evaluate('''() => {
                     // 尝试多种方式查找账号登录按钮
                     const selectors = [
                         '.login-type-switch',
                         '.login-type',
                         '[data-type="account"]',
                         'span:contains("账号登录")',
                         'div:contains("账号登录")'
                     ];

                     for (const selector of selectors) {
                         const elements = document.querySelectorAll(selector);
                         for (const el of elements) {
                             if (el.textContent.includes('账号登录')) {
                                 el.click();
                                 return true;
                             }
                         }
                     }

                     // 如果上面的方法都失败，尝试遍历所有元素
                     const allElements = document.querySelectorAll('*');
                     for (const el of allElements) {
                         if (el.textContent && el.textContent.includes('账号登录')) {
                             el.click();
                             return true;
                         }
                     }

                     return false;
                 }''')

                if clicked:
                    self.logger.info("成功使用JavaScript点击账号登录按钮")
                else:
                    self.logger.error("无法找到账号登录按钮")
                    return False

                # 等待账号密码输入框出现
                self.logger.info("等待账号密码输入框出现...")
                time.sleep(2)  # 等待输入框出现

                # 使用JavaScript检查输入框是否存在
                input_exists = self.page.evaluate('''() => {
                     const textInput = document.querySelector('input[type="text"]');
                     const passwordInput = document.querySelector('input[type="password"]');
                     return textInput && passwordInput;
                 }''')

                if not input_exists:
                    self.logger.error("无法找到输入框")
                    return False

            except Exception as e:
                self.logger.error(f"切换到账号登录模式失败: {str(e)}")
                return False

            # 输入用户名和密码
            self.logger.info("正在输入用户名和密码...")
            try:
                # 使用JavaScript输入用户名和密码
                self.page.evaluate(f'''(username, password) => {{
                     const textInput = document.querySelector('input[type="text"]');
                     const passwordInput = document.querySelector('input[type="password"]');

                     if (textInput && passwordInput) {{
                         textInput.value = username;
                         passwordInput.value = password;

                         // 触发input事件
                         textInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                         passwordInput.dispatchEvent(new Event('input', {{ bubbles: true }}));

                         return true;
                     }}
                     return false;
                 }}''', username, password)

                time.sleep(1)  # 等待输入完成

            except Exception as e:
                self.logger.error(f"输入用户名密码失败: {str(e)}")
                return False

            # 点击登录按钮
            self.logger.info("点击登录按钮...")
            try:
                # 使用JavaScript点击登录按钮
                login_clicked = self.page.evaluate('''() => {
                     const selectors = [
                         'button[type="submit"]',
                         '.login-btn',
                         'button:contains("登录")',
                         '[class*="login-btn"]'
                     ];

                     for (const selector of selectors) {
                         const elements = document.querySelectorAll(selector);
                         for (const el of elements) {
                             if (el.textContent.includes('登录')) {
                                 el.click();
                                 return true;
                             }
                         }
                     }

                     return false;
                 }''')

                if not login_clicked:
                    self.logger.error("无法点击登录按钮")
                    return False

                self.logger.info("成功点击登录按钮")

            except Exception as e:
                self.logger.error(f"点击登录按钮失败: {str(e)}")
                return False

            # 等待登录成功
            try:
                self.logger.info("等待登录成功...")
                # 使用JavaScript检查登录状态
                for _ in range(10):  # 最多等待10秒
                    is_logged_in = self.page.evaluate('''() => {
                         return document.querySelector('.user-avatar') !== null ||
                                document.querySelector('.user-info') !== null ||
                                document.querySelector('.avatar') !== null;
                     }''')

                    if is_logged_in:
                        self.logger.info("登录成功！")
                        return True

                    time.sleep(1)

                self.logger.error("登录超时")
                return False

            except Exception as e:
                self.logger.error(f"等待登录成功超时: {str(e)}")
                return False

        except Exception as e:
            self.logger.error(f"登录过程出错: {str(e)}")
            return False

    def extract_enc_tpid(self, response_data):
        """
        从API响应数据中提取enc_tpid值

        Args:
            response_data (str/dict): API响应数据，可以是JSON字符串或字典

        Returns:
            str: enc_tpid值，如果提取失败则返回空字符串
        """
        try:
            self.logger.info("开始提取enc_tpid...")

            # 检查输入是否为None
            if response_data is None:
                self.logger.error("输入数据为None")
                return ""

            # 如果输入是字符串，尝试解析JSON
            if isinstance(response_data, str):
                try:
                    import json
                    response_data = json.loads(response_data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON解析失败: {str(e)}")
                    return ""
                except Exception as e:
                    self.logger.error(f"解析JSON时发生未知错误: {str(e)}")
                    return ""

            # 检查响应数据格式
            if not isinstance(response_data, dict):
                self.logger.error(f"响应数据格式不正确，不是字典类型，实际类型为: {type(response_data)}")
                return ""

            # 检查dataObj字段
            if 'dataObj' not in response_data:
                self.logger.error("响应数据中缺少dataObj字段")
                return ""

            # 获取dataObj
            data_obj = response_data['dataObj']

            # 检查dataObj是否为None
            if data_obj is None:
                self.logger.error("dataObj字段为None")
                return ""

            # 检查dataObj类型
            if not isinstance(data_obj, dict):
                self.logger.error(f"dataObj格式不正确，不是字典类型，实际类型为: {type(data_obj)}")
                return ""

            # 检查enc_tpid字段
            if 'enc_tpid' not in data_obj:
                self.logger.error("dataObj中缺少enc_tpid字段")
                return ""

            # 获取enc_tpid值
            enc_tpid = data_obj.get('enc_tpid')

            # 检查enc_tpid值是否为空
            if enc_tpid is None:
                self.logger.warning("enc_tpid值为None")
                return ""

            # 确保enc_tpid是字符串类型
            if not isinstance(enc_tpid, str):
                try:
                    enc_tpid = str(enc_tpid)
                except Exception as e:
                    self.logger.error(f"转换enc_tpid为字符串失败: {str(e)}")
                    return ""

            # 检查enc_tpid是否为空字符串
            if not enc_tpid.strip():
                self.logger.warning("enc_tpid值为空字符串")
                return ""

            self.logger.info(f"成功提取enc_tpid: {enc_tpid}")
            return enc_tpid

        except Exception as e:
            self.logger.error(f"提取enc_tpid时出错: {str(e)}")
            # 打印更详细的错误信息
            import traceback
            self.logger.error("详细错误信息:")
            self.logger.error(traceback.format_exc())
            return ""

    def extract_play_url(self, response_data):
        """
        从API响应数据中提取play_url值
        play_url的重要性更强，对其检查更多，对cover_url只做基本检查，如果出错，赋值为空

        Args:
            response_data (str/dict): API响应数据，可以是JSON字符串或字典

        Returns:
            str: play_url值，如果提取失败则返回空字符串
        """
        try:
            self.logger.info("开始提取play_url和cover_url...")

            # 检查输入是否为None
            if response_data is None:
                self.logger.error("输入数据为None")
                return "",""

            # 如果输入是字符串，尝试解析JSON
            if isinstance(response_data, str):
                try:
                    import json
                    response_data = json.loads(response_data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON解析失败: {str(e)}")
                    return "",""
                except Exception as e:
                    self.logger.error(f"解析JSON时发生未知错误: {str(e)}")
                    return "",""

            # 检查响应数据格式
            if not isinstance(response_data, dict):
                self.logger.error(f"响应数据格式不正确，不是字典类型，实际类型为: {type(response_data)}")
                return "",""

            # 检查dataObj字段
            if 'dataObj' not in response_data:
                self.logger.error("响应数据中缺少dataObj字段")
                return "",""

            # 获取dataObj
            data_obj = response_data['dataObj']

            # 检查dataObj是否为None
            if data_obj is None:
                self.logger.error("dataObj字段为None")
                return "",""

            # 检查dataObj类型
            if not isinstance(data_obj, dict):
                self.logger.error(f"dataObj格式不正确，不是字典类型，实际类型为: {type(data_obj)}")
                return "",""

            # 检查playUrl字段
            if 'playUrl' not in data_obj:
                self.logger.error("dataObj中缺少playUrl字段")
                return "",""

            # 获取playUrl值
            play_url = data_obj.get('playUrl')

            # 检查playUrl值是否为空
            if play_url is None:
                self.logger.warning("playUrl值为None")
                return "",""


            # 确保play_url是字符串类型
            if not isinstance(play_url, str):
                try:
                    play_url = str(play_url)
                except Exception as e:
                    self.logger.error(f"转换playUrl为字符串失败: {str(e)}")
                    return "",""

            # 检查play_url是否为空字符串
            if not play_url.strip():
                self.logger.warning("playUrl值为空字符串")
                return "",""


            # 验证URL格式
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(play_url)
                if not all([parsed_url.scheme, parsed_url.netloc]):
                    self.logger.error("playUrl格式不正确")
                    return "",""
            except Exception as e:
                self.logger.error(f"验证URL格式时出错: {str(e)}")
                return "",""

            self.logger.info(f"成功提取playUrl: {play_url}")

            cover_url = data_obj.get('cover')

            if cover_url is None or not cover_url.strip() or not isinstance(play_url, str):
                cover_url = ""

            return (play_url, cover_url)

        except Exception as e:
            self.logger.error(f"提取playUrl时出错: {str(e)}")
            # 打印更详细的错误信息
            import traceback
            self.logger.error("详细错误信息:")
            self.logger.error(traceback.format_exc())
            return "",""

    def extract_liveroomlist_data(self, response_data):
        """
        从API响应数据中提取直播数据，包括topic配置和视频配置

        Args:
            response_data (dict): API响应数据

        Returns:
            tuple: (extracted_data, failed_data)
                - extracted_data: 成功提取的数据列表
                - failed_data: 提取失败的数据列表
        """
        try:
            self.logger.info("开始提取直播数据...")

            # 检查响应数据格式
            if not isinstance(response_data, dict):
                self.logger.error("响应数据格式不正确")
                return [], []

            if 'dataObj' not in response_data:
                self.logger.error("响应数据中缺少dataObj字段")
                return [], []

            data_obj = response_data['dataObj']

            # 获取总数
            total_count = data_obj.get('count', 0)
            self.logger.info(f"总数据量: {total_count}")

            # 获取列表数据
            live_list = data_obj.get('list', [])
            if not live_list:
                self.logger.warning("未找到直播列表数据")
                return [], []

            # 提取指定字段
            extracted_data = []
            failed_data = []
            for item in live_list:
                try:
                    live_info = {
                        'count': total_count,
                        'id': item.get('id', ''),
                        'title': item.get('title', ''),
                        'status': item.get('status', ''),
                        'isOnShelf': item.get('isOnShelf', False),
                        'addtime': item.get('addtime', ''),
                        'starttime': item.get('starttime', ''),
                        'zbId': item.get('zbId', ''),
                        'liveType': item.get('liveType', ''),
                        'viewCount': item.get('viewcts', 0),
                    }
                    live_info['liveroom_url'] = self.liveroom_url_prefix + str(live_info['id'])

                    # 获取topic配置
                    topic_url = self.topic_url_prefix + str(live_info['id'])
                    try:
                        response = requests.get(topic_url, timeout=self.timeout)
                        response.raise_for_status()
                    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                        self.logger.error(f"获取topic配置失败，直播间ID: {live_info['id']}, 错误: {str(e)}")
                        live_info['enc_tpid'] = ""
                        live_info['video_url'] = ""
                        live_info["cover_url"] = ""
                        live_info['error_reason'] = f"获取topic配置失败: {str(e)}"
                        failed_data.append(live_info)
                        continue

                    if response.text is None:
                        self.logger.error(f"获取topic配置响应为空，直播间ID: {live_info['id']}")
                        live_info['enc_tpid'] = ""
                        live_info['video_url'] = ""
                        live_info["cover_url"] = ""
                        live_info['error_reason'] = "获取topic配置响应为空"
                        failed_data.append(live_info)
                        continue

                    # 提取enc_tpid
                    enc_tpid = self.extract_enc_tpid(response.text)
                    if not enc_tpid:
                        self.logger.error(f"提取enc_tpid失败，直播间ID: {live_info['id']}")
                        live_info['enc_tpid'] = ""
                        live_info['video_url'] = ""
                        live_info["cover_url"] = ""
                        live_info['error_reason'] = "提取enc_tpid失败"
                        failed_data.append(live_info)
                        continue

                    live_info['enc_tpid'] = enc_tpid

                    # 获取视频配置
                    video_url = f"https://live-play.vzan.com/api/topic/video_config?tpId={enc_tpid}&domain=inter.dayilive.com&agentId="
                    try:
                        response = requests.get(video_url, timeout=self.timeout)
                        response.raise_for_status()
                    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                        self.logger.error(f"获取视频配置失败，直播间ID: {live_info['id']}, 错误: {str(e)}")
                        live_info['video_url'] = ""
                        live_info["cover_url"] = ""
                        live_info['error_reason'] = f"获取视频配置失败: {str(e)}"
                        failed_data.append(live_info)
                        continue

                    if response.text is None:
                        self.logger.error(f"获取视频配置响应为空，直播间ID: {live_info['id']}")
                        live_info['video_url'] = ""
                        live_info["cover_url"] = ""
                        live_info['error_reason'] = "获取视频配置响应为空"
                        failed_data.append(live_info)
                        continue

                    # 提取play_url
                    (play_url, cover_url) = self.extract_play_url(response.text)
                    if not play_url:
                        self.logger.error(f"提取play_url失败，直播间ID: {live_info['id']}")
                        live_info['video_url'] = ""
                        live_info['cover_url'] = ""
                        live_info['error_reason'] = "提取play_url失败"
                        failed_data.append(live_info)
                        continue

                    live_info['video_url'] = play_url
                    live_info['cover_url'] = cover_url
                    live_info['error_reason'] = ""  # 成功的数据没有错误原因
                    extracted_data.append(live_info)

                except Exception as e:
                    self.logger.error(f"处理直播间数据时出错，直播间ID: {item.get('id', 'unknown')}, 错误: {str(e)}")
                    if 'live_info' in locals():
                        live_info['error_reason'] = f"处理数据时出错: {str(e)}"
                        failed_data.append(live_info)
                    continue

            self.logger.info(f"成功提取 {len(extracted_data)} 条直播数据，失败 {len(failed_data)} 条")
            return extracted_data, failed_data

        except Exception as e:
            self.logger.error(f"提取直播数据时出错: {str(e)}")
            return [], []

    def save_liveroomlist_to_csv(self, live_data, filename=None, mode='w'):
        """
        将直播数据保存到CSV文件

        Args:
            live_data (list): 直播数据列表
            filename (str): 文件名，如果为None则使用默认文件名
            mode (str): 写入模式，'w'为覆盖，'a'为追加

        Returns:
            str: 保存的文件路径，如果保存失败则返回None
        """
        try:
            if not filename:
                filename = self.liveroom_list_savefile

            self.logger.info(f"开始保存数据到文件: {filename}")

            # 定义CSV文件的表头
            headers = [
                '直播间ID',
                '标题',
                '直播间url',
                '创建时间',
                '开始时间',
                '结束时间',
                '直播类型',
                '直播状态',
                '播放url',
                '封面图片',
                '观看次数',
                'zbID',
                "enc_tpid",
                '直播间总数'
            ]

            # 检查文件是否存在
            file_exists = os.path.exists(filename)

            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, mode, newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)

                # 如果是新文件或覆盖模式，写入表头
                if not file_exists or mode == 'w':
                    writer.writeheader()
                    self.logger.info("写入CSV表头")

                # 写入数据
                for item in live_data:
                    try:
                        row = {
                            '直播间ID': item.get('id', ''),
                            '标题': item.get('title', ''),
                            '直播间url': item.get('liveroom_url', ''),
                            '创建时间': item.get('addtime', ''),
                            '开始时间': item.get('starttime', ''),
                            '结束时间': "",
                            '直播类型': item.get('liveType', ''),  # =0表示为开始，=1表示正在直播，=2表示已结束
                            '直播状态': item.get('status', ''),
                            "播放url": item.get('video_url', ''),
                            "封面图片": item.get('cover_url', ''),
                            "观看次数": item.get('view_cts', 0),
                            'zbID': item.get('zbId', ''),
                            'enc_tpid': item.get('enc_tpid', ''),
                            '直播间总数': item.get('count', 0)

                        }
                        writer.writerow(row)
                    except Exception as e:
                        self.logger.error(f"写入单条数据时出错: {str(e)}")
                        continue

            self.logger.info(f"成功保存 {len(live_data)} 条数据到文件: {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"保存CSV文件时出错: {str(e)}")
            return None


    def wait_for_page_load(self, url, timeout=10000):
        """
        等待页面加载并获取内容

        Args:
            url (str): 要访问的URL
            timeout (int): 超时时间（毫秒）

        Returns:
            tuple: (html_content, success)
                - html_content: 页面内容
                - success: 是否成功加载
        """
        try:
            self.logger.info(f"正在访问页面: {url}")

            # 访问页面
            self.page.goto(url, wait_until='domcontentloaded')

            # 等待pre标签出现
            try:
                self.page.wait_for_selector('pre', timeout=timeout)
                #print("成功找到pre标签")
            except Exception as e:
                #print(f"等待pre标签超时: {str(e)}")
                try:
                    self.page.wait_for_load_state('networkidle', timeout=5000)
                    #print("网络请求已完成")
                except Exception as e:
                    self.logger.info(f"等待网络请求完成超时: {str(e)}")

            # 额外等待确保数据加载完成
            time.sleep(2)

            # 获取页面内容
            html_content = self.page.content()

            # 检查是否包含数据
            if 'pre' not in html_content:
                self.logger.info("页面未包含数据")
                return None, False

            return html_content, True

        except Exception as e:
            self.logger.info(f"加载页面时出错: {str(e)}")
            return None, False

    def extract_liveroom_ids_from_csv(self,csv_file):
        """
        从CSV文件中提取内容ID

        Args:
            csv_file (str): CSV文件路径

        Returns:
            list: 内容ID列表
        """
        try:
            content_ids = []

            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                # 使用csv模块读取，指定分隔符为制表符
                reader = csv.reader(f, delimiter=',')

                # 跳过标题行
                next(reader)

                for row in reader:
                    if len(row) >= 2:  # 确保至少有2列数据
                        content_id = row[1]  # 第二列是内容ID
                        content_ids.append(content_id)

            self.logger.info(f"成功提取 {len(content_ids)} 个内容ID")
            return content_ids

        except Exception as e:
            self.logger.info(f"提取内容ID时出错: {str(e)}")
            return []

    def parse_all_liveroomlist_data(self, config):
        """
        解析直播间列表数据，支持分页和增量爬取

        Args:
            config (dict): 配置信息，包含用户名和密码
        """
        try:
            self.logger.info("开始获取直播间列表数据...")

            # 获取已爬取的直播间ID
            existing_ids = self.extract_liveroom_ids_from_csv(self.liveroom_list_savefile)
            is_first_crawl = not existing_ids

            if is_first_crawl:
                self.logger.info("未找到已爬取的直播间ID，将进行首次爬取")
                existing_ids = set()
            else:
                self.logger.info(f"找到 {len(existing_ids)} 个已爬取的直播间ID，将进行增量爬取")
                existing_ids = set(existing_ids)

            # 获取第一页数据来确定总数
            token = config['token']
            # 直接调用API获取第一页数据
            first_page_data = self.get_liveroom_list(
                authorization_token=token,
                page=1,
                psize=10
            )

            # 检查API响应
            if not first_page_data:
                self.logger.error("获取第一页数据失败：API返回为空")
                return

            if not isinstance(first_page_data, dict):
                self.logger.error(f"获取第一页数据失败：API返回格式错误，期望dict类型，实际为{type(first_page_data)}")
                return

            if 'dataObj' not in first_page_data:
                self.logger.error("获取第一页数据失败：API响应中缺少dataObj字段")
                return

            # 获取总数
            total_count = first_page_data['dataObj'].get('count', 0)
            if total_count == 0:
                self.logger.warning("API返回的直播间总数为0")
                return

            self.logger.info(f"总共有 {total_count} 个直播间")

            # 计算总页数
            page_size = 10
            total_pages = (total_count + page_size - 1) // page_size

            # 用于存储所有数据
            all_live_data = []
            all_failed_data = []  # 存储所有失败的数据
            new_live_data = []  # 用于存储新增的直播间数据
            failed_pages = []

            # 创建增量文件
            try:
                self.save_liveroomlist_to_csv(
                    [],
                    filename=self.liveroom_list_savefile_inc,
                    mode='w'
                )
                self.logger.info(f"创建增量文件: {self.liveroom_list_savefile_inc}")
            except Exception as e:
                self.logger.error(f"创建增量文件失败: {str(e)}")
                return

            # 遍历所有页面
            for page in range(1, 3):
                try:
                    self.logger.info(f"正在获取第 {page}/{total_pages} 页数据...")

                    # 直接调用API获取当前页数据
                    page_data = self.get_liveroom_list(
                        authorization_token=token,
                        page=page,
                        psize=page_size
                    )

                    # 检查API响应
                    if not page_data:
                        self.logger.error(f"获取第 {page} 页数据失败：API返回为空")
                        failed_pages.append(page)
                        continue

                    if not isinstance(page_data, dict):
                        self.logger.error(
                            f"获取第 {page} 页数据失败：API返回格式错误，期望dict类型，实际为{type(page_data)}")
                        failed_pages.append(page)
                        continue

                    if 'dataObj' not in page_data:
                        self.logger.error(f"获取第 {page} 页数据失败：API响应中缺少dataObj字段")
                        failed_pages.append(page)
                        continue

                    # 提取数据
                    live_data, failed_data = self.extract_liveroomlist_data(page_data)
                    if not live_data and not failed_data:
                        self.logger.warning(f"第 {page} 页没有提取到任何数据")
                        continue

                    # 处理成功的数据
                    if live_data:
                        # 过滤出新增的直播间数据
                        new_data = []
                        for item in live_data:
                            try:
                                # 安全地获取ID
                                item_id = str(item.get('id', '')).strip() if item.get('id') is not None else ''

                                # 检查ID是否有效且不在已存在集合中
                                if item_id and item_id not in existing_ids:
                                    new_data.append(item)
                                    new_live_data.append(item)
                                    existing_ids.add(item_id)

                            except Exception as e:
                                self.logger.error(
                                    f"处理直播间数据时出错，直播间ID: {item.get('id', 'unknown')}, 错误: {str(e)}")
                                continue

                        if new_data:
                            all_live_data.extend(new_data)
                            self.logger.info(f"第 {page} 页发现 {len(new_data)} 个新增直播间")
                        else:
                            self.logger.info(f"第 {page} 页没有新增直播间")

                    # 处理失败的数据
                    if failed_data:
                        all_failed_data.extend(failed_data)
                        self.logger.info(f"第 {page} 页有 {len(failed_data)} 条数据提取失败")

                    # 当累积的数据达到batch_size时，写入文件
                    if len(all_live_data) >= self.liveroomlist_batchsize:
                        try:
                            # 写入主文件
                            self.save_liveroomlist_to_csv(
                                all_live_data,
                                filename=self.liveroom_list_savefile,
                                mode='a' if page > 1 else 'w'
                            )
                            # 写入增量文件
                            self.save_liveroomlist_to_csv(
                                all_live_data,
                                filename=self.liveroom_list_savefile_inc,
                                mode='a'
                            )
                            self.logger.info("batch writing")
                            all_live_data = []  # 清空缓存
                        except Exception as e:
                            self.logger.error(f"保存数据到文件时出错: {str(e)}")
                            failed_pages.append(page)
                            continue

                    # 添加短暂延迟，避免请求过快
                    time.sleep(1)

                except Exception as e:
                    self.logger.error(f"处理第 {page} 页时出错: {str(e)}")
                    failed_pages.append(page)
                    continue

            # 保存剩余的成功数据
            if all_live_data:
                try:
                    # 写入主文件
                    self.save_liveroomlist_to_csv(
                        all_live_data,
                        filename=self.liveroom_list_savefile,
                        mode='a'
                    )
                    # 写入增量文件
                    self.save_liveroomlist_to_csv(
                        all_live_data,
                        filename=self.liveroom_list_savefile_inc,
                        mode='a'
                    )
                    self.logger.info(f"成功保存剩余的 {len(all_live_data)} 条数据")
                except Exception as e:
                    self.logger.error(f"保存剩余数据时出错: {str(e)}")

            # 保存失败的数据
            if all_failed_data:
                try:
                    self.save_liveroomlist_to_csv(
                        all_failed_data,
                        filename=self.failed_liveroomlist_url,
                        mode='w'
                    )
                    self.logger.info(f"已保存 {len(all_failed_data)} 条失败数据到文件")
                except Exception as e:
                    self.logger.error(f"保存失败数据时出错: {str(e)}")

            # 保存失败的页面
            if failed_pages:
                try:
                    with open(self.failed_liveroomlist_url, 'w', encoding='utf-8') as f:
                        json.dump(failed_pages, f, ensure_ascii=False, indent=4)
                    self.logger.info(f"已保存 {len(failed_pages)} 个失败的页面到文件")
                except Exception as e:
                    self.logger.error(f"保存失败页面时出错: {str(e)}")

            # 输出爬取统计信息
            self.logger.info(
                f"本次爬取完成，共发现 {len(new_live_data)} 个新增直播间，{len(all_failed_data)} 条数据提取失败")
            if is_first_crawl:
                self.logger.info("首次爬取完成，已保存所有直播间数据")
            else:
                self.logger.info(f"增量爬取完成，新增 {len(new_live_data)} 个直播间数据")

        except Exception as e:
            self.logger.error(f"获取直播间列表数据时出错: {str(e)}")
            # 打印更详细的错误信息
            import traceback
            self.logger.error("详细错误信息:")
            self.logger.error(traceback.format_exc())

    def save_failed_urls(self, failed_urls, filename):
        """
        保存失败的URL到文件

        Args:
            failed_urls (list): 失败的URL列表
            filename (str): 保存的文件名
        """
        try:
            # 如果文件已存在，先读取现有数据
            existing_urls = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_urls = json.load(f)

            # 合并新的失败URL
            all_failed_urls = list(set(existing_urls + failed_urls))

            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_failed_urls, f, ensure_ascii=False, indent=4)

            self.logger.info(f"已保存 {len(failed_urls)} 个失败的URL到 {filename}")

        except Exception as e:
            self.logger.info(f"保存失败URL时出错: {str(e)}")

    def clean_old_files(self):
        """清理之前运行产生的文件"""
        try:
            import shutil

            # 先关闭所有日志处理器
            if self.logger:
                for handler in self.logger.handlers[:]:
                    handler.close()
                    self.logger.removeHandler(handler)

            # 需要清理的文件列表
            files_to_clean = [
                self.liveroom_list_savefile,
                self.liveroom_details_savefile,
                self.failed_liveroomlist_url,
                self.failed_liveroomdetails_url,
                self.failed_liveroom_watchers_url
            ]

            # 清理文件
            for file in files_to_clean:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                        self.logger.info(f"已删除文件: {file}")
                    except Exception as e:
                        self.logger.info(f"删除文件 {file} 时出错: {str(e)}")

            # 清理watchers文件夹
            if os.path.exists(self.liveroom_watchers_savedir):
                try:
                    shutil.rmtree(self.liveroom_watchers_savedir)
                    self.logger.info(f"已删除文件夹: {self.liveroom_watchers_savedir}")
                except Exception as e:
                    self.logger.info(f"删除文件夹 {self.liveroom_watchers_savedir} 时出错: {str(e)}")

            self.logger.info("文件清理完成,再次创建存储文件夹为下一次运行")
            self.create_storage()
        except Exception as e:
            self.logger.info(f"清理文件时出错: {str(e)}")
        finally:
            # 重新设置日志
            self.setup_logging()

    def close(self):
        """关闭浏览器"""
        """关闭浏览器并输出日志文件位置"""
        self.logger.info(f"程序执行完成，日志文件保存在: {self.log_file}")
        self.context.close()
        self.browser.close()
        self.playwright.stop()


def main():
    # 配置信息
    config = {
        'username': '18611501509',  # 替换为你的用户名
        'password': 'Drtawey78',  # 替换为你的密码
        'token': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2IjoiNiIsInJvbCI6IjIiLCJhaWQiOiI0OWU3YTk0ZC0xN2NkLTQ4NTUtYjAxNC0wMzFmMThjMmIzODkiLCJ1aWQiOiIyMjM4NTA1MDkiLCJsaWQiOiIxMTc0OTU0OSIsImFwcGlkIjoiMTgiLCJ0eXBlIjoiMCIsIm5iZiI6MTc0Nzk2NjEyMiwiZXhwIjoxNzQ4MDA5MzUyLCJpYXQiOjE3NDc5NjYxNTIsImlzcyI6InZ6YW4iLCJhdWQiOiJ2emFuIn0.vZmzxtZhsZ3v7ccxQrXGsjsDoPvXpqKIbmEQ_8PIEjU"

    }

    # 创建爬虫实例
    crawler = DuanShuCrawler_vzan()

    try:
        #crawler.clean_old_files()
        # 登录
        #crawler.login(config['username'], config['password'])

        # 直接调用API获取数据
        start_time = time.time()
        crawler.parse_all_liveroomlist_data(config)
        end_time = time.time()
        execution_time1 = end_time - start_time


        start_time = time.time()
        #crawler.parse_watchers_data(config)
        end_time = time.time()
        execution_time3 = end_time - start_time

        crawler.logger.info(f"parse_all_liveroomlist_data的执行时间：{execution_time1:.2f} 秒")
        crawler.logger.info(f"parse_watchers_data的执行时间：{execution_time3:.2f} 秒")

    except Exception as e:
        print(f"爬取过程出错: {str(e)}")
    finally:
        crawler.close()


if __name__ == "__main__":
    # url = "https://live-play.vzan.com/api/topic/topic_config?isPcBrowser=true&topicId=1772215758"
    # response = requests.get(url, headers=headers)
    # url = "https://live-play.vzan.com/api/topic/video_config?tpId=5F3A086755E8BACC6CE5DC700FF65133&domain=inter.dayilive.com&agentId="
    # response = requests.get(url, headers=headers)

    main()