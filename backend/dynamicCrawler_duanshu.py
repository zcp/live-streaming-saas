import shutil
import tempfile
from sys import prefix

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import json
import csv
import os
from datetime import datetime


class DuanShuCrawler:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)  # 设置为False可以看到浏览器操作
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.liveroom_url_prefix = "https://my.duanshu.com/details/live/"
        self.liveroom_details_url_prefix = "https://api.duanshu.com/fairy/manage/v1/lives/"
        self.liveroomlist_batchsize = 500
        self.liveroom_details_batchsize = 500

        import tempfile
        import platform

        # 获取系统临时文件夹路径
        if platform.system() == 'Windows':
            # Windows: C:\Users\<username>\AppData\Local\Temp\duanshu_crawler
            self.temp_dir = os.path.join(tempfile.gettempdir(), 'duanshu_crawler')
        else:
            # Linux: /tmp/duanshu_crawler
            self.temp_dir = os.path.join(tempfile.gettempdir(), 'duanshu_crawler')

        # 所有文件都放在临时文件夹下
        self.liveroom_list_savefile = os.path.join(self.temp_dir, "liveroomlist.csv")
        self.liveroom_details_savefile = os.path.join(self.temp_dir, "liveroom_elements.csv")
        self.liveroom_watchers_savefile_prefix = "liveroom_watchers"
        self.liveroom_watchers_savedir = os.path.join(self.temp_dir, "watchers")

        #用于记录每次爬取时获取的新增直播间id， 第一次爬取将获取所有的直播间id
        self.liveroom_list_savefile_inc = os.path.join(self.temp_dir, "liveroomlist_inc.csv")
        self.liveroom_details_savefile_inc = os.path.join(self.temp_dir, "liveroomlist_elements_inc_duanshu.csv")

        self.failed_liveroomlist_url = os.path.join(self.temp_dir, 'failed_liveroomlist_urls.txt')
        self.failed_liveroomdetails_url = os.path.join(self.temp_dir, 'failed_liveroomdetails_urls.txt')
        self.failed_liveroom_watchers_url = os.path.join(self.temp_dir, 'failed_watchers_urls.txt')

        # 初始化logger为None
        # 设置日志
        self.logger = None
        self.log_file = None

        self.setup_logging()
        self.create_storage()

    def create_storage(self):
        # 设置临时文件夹
        # 创建临时文件夹
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            self.logger.info(f"创建临时文件夹: {self.temp_dir}")

        if not os.path.exists(self.liveroom_watchers_savedir):
            os.makedirs(self.liveroom_watchers_savedir)
            self.logger.info(f"创建watchers文件夹: {self.liveroom_watchers_savedir}")

    def setup_logging(self):
        """配置日志系统，使用系统临时文件夹存储日志"""
        import logging
        from datetime import datetime
        import os

        # 生成日志文件名
        log_filename = f'duanshu_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        self.logger.info(f"日志文件路径: {log_file}")

        # 保存日志文件路径，方便后续查看
        self.log_file = log_file

    def login(self, username, password):
        """登录短书"""
        try:
            self.logger.info("正在登录短书...")
            self.page.goto('https://my.duanshu.com/list')

            # 等待页面完全加载
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)  # 额外等待确保页面加载完成

            # 等待登录表单加载
            self.logger.info("等待登录表单加载...")
            self.page.wait_for_selector('.login-form', timeout=10000)

            # 使用更精确的选择器
            self.logger.info("正在输入用户名和密码...")
            # 用户名输入框
            self.page.fill('.login-form input[type="text"]', username)
            # 密码输入框
            self.page.fill('.login-form input[type="password"]', password)

            # 点击登录按钮
            self.logger.info("点击登录按钮...")
            # 尝试多个可能的选择器
            try:
                # 方法1：使用type属性
                self.page.click('button[type="submit"]')
            except:
                #self.page.goto('https://my.duanshu.com/live/list')
                #print(self.page.content())
                try:
                    # 方法2：使用class
                    self.page.click('.login-btn')
                except:
                    try:
                        # 方法3：使用文本内容
                        self.page.click('button:has-text("登录")')
                    except:
                        # 方法4：使用XPath
                        self.page.click('//button[contains(text(), "登录")]')


            self.logger.info("登录成功！")
            """
            print("等待二维码弹窗...")
            try:
                # 等待弹窗出现，使用多个可能的选择器
                try:
                    # 方法1：使用class
                    self.page.wait_for_selector('.el-message-box__btns .el-button--primary', timeout=5000)
                    self.page.click('.el-message-box__btns .el-button--primary')
                except:
                    try:
                        # 方法2：使用文本内容
                        self.page.wait_for_selector('button:has-text("好的")', timeout=5000)
                        self.page.click('button:has-text("好的")')
                    except:
                        # 方法3：使用XPath
                        self.page.wait_for_selector('//button[contains(text(), "好的")]', timeout=5000)
                        self.page.click('//button[contains(text(), "好的")]')

                print("已关闭二维码弹窗")
            except Exception as e:
                print("没有检测到二维码弹窗或关闭失败:", str(e))
                # 打印页面内容，帮助调试
                print("当前页面内容:")
                #content = self.page.content()
                #print(content)  # 只打印前1000个字符
            """
            self.page.wait_for_selector('.user-avatar', timeout=10000)

            return True

        except Exception as e:
            self.logger.info(f"登录失败: {str(e)}")
            # 打印页面内容，帮助调试
            #print("当前页面内容:")
            #self.page.goto('https://my.duanshu.com/live/list')
            #print(self.page.content())
            return self.page

    def extract_liveroomlist_data(self, html_content):
        """从HTML内容中提取直播数据"""
        try:
            # 首先从HTML中提取JSON字符串
            import json
            import re
            import csv
            from datetime import datetime

            # 使用正则表达式提取JSON部分
            json_match = re.search(r'<pre>(.*?)</pre>', html_content, re.DOTALL)
            if not json_match:
                self.logger.info("未找到JSON数据")
                return []

            json_str = json_match.group(1)
            # 解析JSON数据
            data = json.loads(json_str)

            # 提取直播数据
            live_data = []
            if 'response' in data and 'data' in data['response']:
                for item in data['response']['data']:
                    live_info = {
                        'liveroom_url': self.liveroom_url_prefix + item.get('content_id', ''),
                        'content_id': item.get('content_id', ''),
                        'title': item.get('title', ''),
                        'created_at': item.get('create_time', ''),
                        'price': item.get('price', '0.00'),
                        'view_count': item.get('view_count', 0),
                        'live_type': item.get('live_type', ''),
                        'live_state': item.get('live_state', ''),
                        'start_time': item.get('start_time', ''),
                        'end_time': item.get('end_time', ''),
                        'status': item.get('status', ''),
                        'sales_total': item.get('sales_total', 0),
                        'unique_member': item.get('unique_member', 0),
                    }
                    live_data.append(live_info)
                return live_data
            else:
                self.logger.info("API响应格式不正确")
                return []

        except Exception as e:
            self.logger.info(f"提取数据时出错: {str(e)}")
            return []

    def save_liveroomlist_to_csv(self,live_data, filename = None, mode = 'w'):
        """将直播数据保存到CSV文件"""
        filename = self.liveroom_list_savefile if filename is None else filename
        try:
            # 定义CSV文件的表头
            headers = [
                '直播间url', '直播间ID','标题', '创建时间', '价格', '观看次数',
                '直播类型', '直播状态', '开始时间', '结束时间',
                '状态', '销售总额', '独立访客数'
            ]

            # 检查文件是否存在
            file_exists = os.path.exists(filename)

            with open(filename, mode, newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)

                # 如果是新文件，写入表头
                if not file_exists or mode == 'w':
                    writer.writeheader()

                for item in live_data:
                    # 准备写入的数据行
                    row = {
                        '直播间url': item['liveroom_url'],
                        '直播间ID': item['content_id'],
                        '标题': item['title'],
                        '创建时间': item['created_at'],
                        '价格': item['price'],
                        '观看次数': item['view_count'],
                        '直播类型': item['live_type'],
                        '直播状态': item['live_state'],
                        '开始时间': item['start_time'],
                        '结束时间': item['end_time'],
                        '状态': item['status'],
                        '销售总额': item['sales_total'],
                        '独立访客数': item['unique_member'],
                    }
                    #print("row:", row)
                    writer.writerow(row)

            self.logger.info(f"数据已成功保存到 {filename}")
            return filename

        except Exception as e:
            self.logger.info(f"保存CSV文件时出错: {str(e)}")
            return None

    def get_max_page(self, url, max_retries=3, try_pages=3):
        """
        从多个页面中获取最大页数，支持重试和自动翻页

        Args:
            url: 请求URL
            max_retries: 每个页面的最大重试次数
            try_pages: 尝试获取的页面数量

        Returns:
            int: 最大页数，如果获取失败返回None
        """
        # 依次尝试每个页面
        for page in range(1, try_pages + 1):
            retry_count = 0
            self.logger.info(f"开始尝试获取第{page}页数据...")

            # 对当前页面进行重试
            while retry_count < max_retries:
                try:
                    current_url = f'{url}?page={page}&count=10'
                    self.logger.info(f"正在获取第{page}页数据 (第{retry_count + 1}次尝试)...")

                    # 尝试加载页面
                    html_content, success = self.wait_for_page_load(current_url)
                    if not success:
                        retry_count += 1
                        self.logger.warning(f"第{page}页第{retry_count}次尝试失败")
                        if retry_count < max_retries:
                            time.sleep(2)  # 等待2秒后重试
                        continue

                    # 解析页面内容
                    soup = BeautifulSoup(html_content, 'html.parser')
                    pre_tag = soup.find('pre')
                    if not pre_tag:
                        retry_count += 1
                        self.logger.warning(f"第{page}页未找到pre标签")
                        if retry_count < max_retries:
                            time.sleep(2)
                        continue

                    try:
                        json_data = json.loads(pre_tag.text)
                    except json.JSONDecodeError:
                        retry_count += 1
                        self.logger.warning(f"第{page}页JSON解析失败")
                        if retry_count < max_retries:
                            time.sleep(2)
                        continue

                    # 从响应中获取最大页数
                    if 'response' in json_data and 'page' in json_data['response']:
                        max_page = json_data['response']['page']['last_page']
                        self.logger.info(f"从第{page}页成功获取最大页数: {max_page}")
                        return max_page
                    else:
                        retry_count += 1
                        self.logger.warning(f"第{page}页未找到last_page信息")
                        if retry_count < max_retries:
                            time.sleep(2)
                        continue

                except Exception as e:
                    retry_count += 1
                    self.logger.error(f"获取第{page}页时出错: {str(e)}")
                    if retry_count < max_retries:
                        time.sleep(2)
                    continue

            # 如果当前页面重试次数用完，尝试下一个页面
            self.logger.warning(f"第{page}页尝试{max_retries}次后失败，尝试下一页")
            continue

        # 如果所有页面都尝试失败
        self.logger.error(f"尝试了{try_pages}个页面，均无法获取max_page")
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

    def parse_all_liveroomlist_data(self, config):
        """
        解析直播间列表数据，支持分页

        Args:
            config (dict): 配置信息，包含用户名和密码
        """
        liveroom_ids = self.extract_liveroom_ids_from_csv(self.liveroom_list_savefile)
        is_first_crawl = not liveroom_ids

        if is_first_crawl:
            self.logger.info("未找到直播间ID列表，判定为第一次抓取")
            liveroom_ids = set()
        else:
            self.logger.info(f"找到 {len(liveroom_ids)} 个已存在的直播间ID，判定为增量抓取")
            liveroom_ids = set(liveroom_ids)

        self.login(config['username'], config['password'])

        all_live_data = []  # 存储所有页的数据
        failed_urls = []  # 存储失败的URL
        total_new_live_data = []  # 用于记录新增的直播间ID

        batch_size = self.liveroomlist_batchsize  # 每500条数据写入一次文件
        url = f'https://api.duanshu.com/admin/content/alive/lists?page=1&count=10'
        pre_url = f'https://api.duanshu.com/admin/content/alive/lists'
        max_page = self.get_max_page(pre_url, max_retries=3, try_pages=3)

        #每次爬取都创建一个新的增量文件，它可以为空，方便parse_liveroom_elements函数调用
        try:
            self.save_liveroomlist_to_csv(
                [],
                self.liveroom_list_savefile_inc,
                mode='w'
            )
            self.logger.info(f"创建一个新增直播间到增量空文件,{self.liveroom_list_savefile_inc}")
        except Exception as e:
            self.logger.error(f"保存新增直播间数据时出错,{self.liveroom_list_savefile_inc}: {str(e)}")

        if max_page is None:
            self.logger.warning(f"未找到last_page信息, 爬取失败 ")
            return

        # 记录是否遇到已抓取的直播间
        found_existing = False
        page = 1
        #while page <= max_page:
        while page <= 3 and not found_existing:
            try:
                #print(f"正在处理第 {page} 页...")
                url = f'https://api.duanshu.com/admin/content/alive/lists?page={page}&count=10'
                # 页面加载策略
                # 使用新的函数加载页面
                html_content, success = self.wait_for_page_load(url)
                if not success:
                    failed_urls.append(url)
                    page += 1
                    continue

                # 提取当前页的数据
                live_data = self.extract_liveroomlist_data(html_content)
                #分析数据失败，可能抓取的数据有问题，比如json格式不对
                if len(live_data) == 0:
                    failed_urls.append(url)
                    page += 1
                    continue

                # 检查当前页的直播间是否都已抓取过
                new_live_data = []
                for item in live_data:
                    live_state = item['live_state']
                    #live_state = 0 =1 表示正在直播，表示未开始直播，=2 表示已经直播结束。我们只爬取直播结束的直播间信息
                    if live_state != 2:
                        continue
                    content_id = item['content_id']
                    if content_id in liveroom_ids:
                        # 如果遇到已抓取的直播间，标记并退出
                        self.logger.info(f"在第 {page} 页遇到已抓取的直播间 {content_id}，停止抓取")
                        continue
                    else:
                        new_live_data.append(item)
                        total_new_live_data.append(item)  # 记录新增的直播间ID

                #如果一个页面中的所有直播间都被抓取过，我们认为这个页面已经在之前被抓取了，之后的页面页都被i抓取了，因此增量抓取任务完成
                if new_live_data:
                    all_live_data.extend(new_live_data)
                    self.logger.info(f"第 {page} 页成功获取 {len(new_live_data)} 条数据")
                else:
                    self.logger.info(f"在第 {page} 页的所有直播间都被抓取过，推测后续页面也已经被抓取，停止本次抓取任务。")
                    found_existing = True
                    break

                # 当累积的数据达到batch_size时，写入文件
                file_exists = os.path.exists(self.liveroom_list_savefile)
                if len(all_live_data) >= batch_size:
                    self.save_liveroomlist_to_csv(
                        all_live_data,
                        filename=self.liveroom_list_savefile,
                        mode='a' if file_exists else 'w'  # 根据文件是否存在决定写入模式
                    )

                    all_live_data = []  # 清空缓存
                # 添加短暂延迟，避免请求过快
                time.sleep(1)
                page += 1

            except Exception as e:
                self.logger.info(f"处理第 {page} 页时出错: {str(e)}")
                failed_urls.append(url)

        # 保存失败URL
        if failed_urls:
            try:
                self.save_failed_urls(failed_urls, self.failed_liveroomlist_url)
            except Exception as e:
                self.logger.info(f"保存failed_urls时出错: {str(e)}")

        # 保存所有数据
        if all_live_data:
            try:
                self.save_liveroomlist_to_csv(all_live_data,self.liveroom_list_savefile,mode='a')
            except Exception as e:
                self.logger.info(f"保存数据时出错: {str(e)}")

        if is_first_crawl:
            # 第一次爬取，复制整个文件
            try:
                # 确保目标文件存在,删除它
                if os.path.exists(self.liveroom_list_savefile_inc):
                    os.remove(self.liveroom_list_savefile_inc)
                # 复制文件
                shutil.copy2(self.liveroom_list_savefile, self.liveroom_list_savefile_inc)
                self.logger.info("第一次爬取，已复制完整文件到增量文件")
            except Exception as e:
                self.logger.error(f"复制文件时出错: {str(e)}")
        else:
            # 增量爬取，只保存新增数据。total_new_live_data可能是null，这样就创建一个空文件，方便parser_liveroom_elements函数调用
            try:
                    self.save_liveroomlist_to_csv(
                        total_new_live_data,
                        self.liveroom_list_savefile_inc,
                        mode='w'
                    )
                    self.logger.info(f"已保存 {len(total_new_live_data)} 个新增直播间到增量文件")
            except Exception as e:
                    self.logger.error(f"保存新增直播间数据时出错: {str(e)}")

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

    def extract_liveroom_elements(self,html_text):
        """
        从HTML文本中提取JSON数据并解析关键信息

        Args:
            html_text (str): 包含JSON数据的HTML文本

        Returns:
            dict: 包含提取的信息的字典
        """
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_text, 'html.parser')

            # 找到包含JSON数据的pre标签
            pre_tag = soup.find('pre')
            if not pre_tag:
                self.logger.info("未找到JSON数据")
                return {}

            # 解析JSON数据
            import json
            json_data = json.loads(pre_tag.text)

            # 时间戳转换函数
            def convert_timestamp(timestamp):
                if not timestamp:
                    return ""
                from datetime import datetime
                return datetime.fromtimestamp(int(timestamp)).strftime('%Y/%m/%d:%H:%M:%S')

            # 提取基本信息
            info = {
                'name': json_data.get('response', {}).get('name', ''),
                'images': json_data.get('response', {}).get('images', []),
                'view_count': json_data.get('response', {}).get('view_count', 0),
                'unique_member': json_data.get('response', {}).get('unique_member', 0),
                'average_stayed_time': json_data.get('response', {}).get('average_stayed_time', 0),
                'message_count': json_data.get('response', {}).get('message_count', 0),
                'status':  json_data.get('response', {}).get('status', 0),
                'play_url': json_data.get('response', {}).get('live_config', {}).get('play_url', ''),
                'created_at': convert_timestamp(json_data.get('response', {}).get('created_at')),
                'start_time': convert_timestamp(json_data.get('response', {}).get('start_time')),
                'end_time': convert_timestamp(json_data.get('response', {}).get('end_time'))
            }

            # 提取detail中的图片URL
            detail = json_data.get('response', {}).get('detail', '')
            if detail:
                detail_soup = BeautifulSoup(detail, 'html.parser')
                detail_images = [img.get('src') for img in detail_soup.find_all('img')]
                info['detail_images'] = detail_images

            return info

        except Exception as e:
            self.logger.info(f"提取直播信息时出错: {str(e)}")
            return {}


    def save_liveroom_elements_to_csv(self, live_data, filename=None, mode = 'w'):
        """
        将直播数据保存到CSV文件

        Args:
            live_data (dict): 包含直播信息的字典
            filename (str): 文件名，如果为None则自动生成
        """
        if not filename:
            # 使用当前时间生成文件名
            filename = self.liveroom_details_savefile

        try:
            # 定义CSV文件的表头
            #直播状态=2 表示已经直播结束，=0 表示未开始直播
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
                'uv',
                '平均停留时间(秒)',
                '详情图片',
                '消息数量'
            ]
            # 检查文件是否存在
            file_exists = os.path.exists(filename)

            with open(filename, mode, newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)

                # 如果是新文件，写入表头
                if not file_exists or mode == 'w':
                    writer.writeheader()

                # 处理每一行数据
                for data in live_data:
                    # 准备写入的数据行
                    # 安全地处理图片列表
                    images = data.get('images', [])
                    detail_images = data.get('detail_images', [])

                    row = {
                        '直播间ID': data.get('content_id', ''),
                        '标题': data.get('name', ''),
                        '直播间url': data.get('liveroom_url', ''),
                        '创建时间': data.get('created_at', ''),
                        '开始时间': data.get('start_time', ''),
                        '结束时间': data.get('end_time', ''),
                        '直播类型': "",
                        "直播状态": data.get('status', ''),
                        '播放url': data.get('play_url', ''),
                        '封面图片': ';'.join(str(img) for img in images if img) if images else '',
                        '观看次数': data.get('view_count', 0),
                        'uv': data.get('unique_member', 0),
                        '平均停留时间(秒)': data.get('average_stayed_time', 0),
                        '详情图片': ';'.join(str(img) for img in detail_images if img) if detail_images else '',
                        '消息数量': data.get('message_count', 0)
                    }

                    #print(f"正在写入行数据: {row}")
                    writer.writerow(row)

            self.logger.info(f"数据已成功保存到 {filename}")
            return filename

        except Exception as e:
            self.logger.info(f"保存CSV文件时出错: {str(e)}")
            # 打印更详细的错误信息
            import traceback
            self.logger.info("详细错误信息:")
            self.logger.info(traceback.format_exc())
            return None

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

    def parse_liveroom_elements(self,config):
        self.login(config['username'], config['password'])
        # 没有新增直播间，新建一个空文件，方便parse_liveroom_watchers函数的执行
        try:
            self.save_liveroom_elements_to_csv(
                [],
                filename=self.liveroom_details_savefile_inc,
                mode='w'
            )
            self.logger.error(f"创建文件{self.liveroom_details_savefile_inc}")
        except Exception as e:
            self.logger.error(f"创建文件{self.liveroom_details_savefile_inc}失败: {str(e)}")

        liveroom_ids = self.extract_liveroom_ids_from_csv(self.liveroom_list_savefile_inc)
        if not liveroom_ids:
            self.logger.info("未找到直播间ID列表")
            return

        #print(liveroom_ids)
        results = []
        failed_urls = []  # 存储失败的URL
        batch_size = self.liveroom_details_batchsize # 每500条数据写入一次文件

        file_exists = os.path.exists(self.liveroom_details_savefile)
        for i, liveroom_id in enumerate(liveroom_ids):
            try:
                liveroom_detail_url = self.liveroom_details_url_prefix + liveroom_id
                #print(f"\n正在处理第 {i}/{len(liveroom_ids)} 个直播间: {liveroom_id}")

                # 页面加载策略
                # 使用新的函数加载页面
                html_content, success = self.wait_for_page_load(liveroom_detail_url)
                if not success:
                    failed_urls.append(liveroom_detail_url)
                    continue

                data = self.extract_liveroom_elements(html_content)
                if data:
                    data['content_id'] = liveroom_id
                    data['liveroom_url'] = liveroom_detail_url
                    results.append(data)
                    #print(f"成功获取直播间 {liveroom_id} 的数据")
                    # 当累积的数据达到batch_size时，写入文件
                    if len(results) >= batch_size:
                        # 写入主文件（追加模式）
                        self.save_liveroom_elements_to_csv(
                            results,
                            filename=self.liveroom_details_savefile,
                            mode='a' if file_exists else 'w'  # 如果文件存在则追加，不存在则创建
                        )
                        # 写入增量文件
                        self.save_liveroom_elements_to_csv(
                            results,
                            filename=self.liveroom_details_savefile_inc,
                            mode='a' if i > 0 else 'w'
                        )
                        results = []  # 清空缓存
                else:
                    self.logger.info(f"获取直播间 {liveroom_id} 的数据失败")
                    failed_urls.append(liveroom_detail_url)

            except Exception as e:
                self.logger.info(f"处理直播间 {liveroom_id} 时出错: {str(e)}")
                failed_urls.append(liveroom_detail_url)
                continue

        # 保存失败URL
        if failed_urls:
            try:
                self.save_failed_urls(failed_urls, self.failed_liveroomdetails_url)
            except Exception as e:
                self.logger.info(f" 保存failed_urls时出错: {str(e)}")
        # 保存剩余的数据
        if results:
            try:
                # 写入主文件（追加模式）
                self.save_liveroom_elements_to_csv(
                    results,
                    filename=self.liveroom_details_savefile,
                    mode='a' if file_exists else 'w'  # 如果文件存在则追加，不存在则创建
                )
                # 写入增量文件
                self.save_liveroom_elements_to_csv(
                    results,
                    filename=self.liveroom_details_savefile_inc,
                    mode='a'
                )
                self.logger.info(f"成功保存 {len(results)} 条剩余数据")
            except Exception as e:
                self.logger.error(f"保存数据时出错: {str(e)}")


    def extract_watchers_data(self, html_text):
        """
        从JSON数据中提取观看视频人员信息并保存为CSV格式

        Args:
            json_data (dict): 包含会员信息的JSON数据

        Returns:
            list: 包含提取的会员信息的列表
        """
        # 使用BeautifulSoup解析HTML
        try:
            soup = BeautifulSoup(html_text, 'html.parser')

            # 找到包含JSON数据的pre标签
            pre_tag = soup.find('pre')
            if not pre_tag:
                self.logger.info("未找到JSON数据")
                return {}

            # 解析JSON数据
            import json
            json_data = json.loads(pre_tag.text)

            # 检查是否有数据
            if 'response' not in json_data or 'data' not in json_data['response']:
                self.logger.info("JSON数据格式不正确")
                return []

            # 提取所有会员数据
            watchers_data = []
            for member in json_data['response']['data']:
                member_data = {
                    'member_id': member.get('member_id', ''),
                    'first_entry_time': member.get('first_entry_time', ''),
                    'latest_entry_time': member.get('latest_entry_time', ''),
                    'nickname': member.get('nickname', ''),
                    'avatar': member.get('avatar', ''),
                    'member_uid': member.get('member_uid', ''),
                    'message_count': member.get('message_count', 0),
                    'total_stayed_time': member.get('total_stayed_time', 0),
                    'source': member.get('source', '')
                }

                # 转换时间戳
                if member_data['first_entry_time']:
                    member_data['first_entry_time'] = datetime.fromtimestamp(
                        int(member_data['first_entry_time'])
                    ).strftime('%Y/%m/%d:%H:%M:%S')

                if member_data['latest_entry_time']:
                    member_data['latest_entry_time'] = datetime.fromtimestamp(
                        int(member_data['latest_entry_time'])
                    ).strftime('%Y/%m/%d:%H:%M:%S')

                watchers_data.append(member_data)

            return watchers_data

        except Exception as e:
            self.logger.info(f"提取会员数据时出错: {str(e)}")
            return []

    def save_watchers_data_to_csv(self, watchers_data_list, liveroom_id, mode = 'w'):
        """
        将会员数据保存到CSV文件

        Args:
            member_data_list (list): 会员数据列表
        """
        filename = os.path.join(
            self.liveroom_watchers_savedir,
            f'{self.liveroom_watchers_savefile_prefix}_{liveroom_id}.csv'
        )

        try:
            # 定义CSV文件的表头
            headers = [
                '会员ID',
                '直播间ID',
                '首次进入时间',
                '最后进入时间',
                '昵称',
                '头像',
                '会员UID',
                '消息数量',
                '总停留时间(秒)',
                '来源'  # 添加source字段的中文表头
            ]

            # 检查文件是否存在
            file_exists = os.path.exists(filename)

            with open(filename, mode, newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)

                # 如果是新文件，写入表头
                if not file_exists or mode == 'w':
                    writer.writeheader()

                # 写入数据
                for data in watchers_data_list:
                    row = {
                        '会员ID': data.get('member_id', ''),
                        '直播间ID': str(liveroom_id),
                        '首次进入时间': data.get('first_entry_time', ''),
                        '最后进入时间': data.get('latest_entry_time', ''),
                        '昵称': data.get('nickname', ''),
                        '头像': data.get('avatar', ''),
                        '会员UID': data.get('member_uid', ''),
                        '消息数量': data.get('message_count', 0),
                        '总停留时间(秒)': data.get('total_stayed_time', 0),
                        '来源': data.get('source', '')  # 添加source字段
                    }
                    writer.writerow(row)

            self.logger.info(f"数据已成功保存到 {filename}")
            return filename

        except Exception as e:
            self.logger.info(f"保存CSV文件时出错: {str(e)}")
            return None



    def parse_watchers_data(self, config):
        """
        解析直播间列表数据，支持分页

        Args:
            config (dict): 配置信息，包含用户名和密码
        """

        # 创建watchers文件夹
        watchers_dir = 'watchers'
        if not os.path.exists(watchers_dir):
            os.makedirs(watchers_dir)
            #print(f"创建文件夹: {watchers_dir}")

        self.login(config['username'], config['password'])
        liveroom_ids = self.extract_liveroom_ids_from_csv(self.liveroom_list_savefile_inc)
        if not liveroom_ids:
            self.logger.info("未找到直播间ID列表")
            return

        #print(liveroom_ids)

        batch_size = self.liveroom_details_batchsize # 每500条数据写入一次文件

        for i, liveroom_id in enumerate(liveroom_ids[:211]):
            failed_urls = []  # 存储失败的URL
            all_watchers_data = []

            #这并不是一个真实的最大页面数，后面会进行更新
            # 首先获取第一页数据，并从中获取最大页数
            url = f'https://api.duanshu.com/fairy/manage/v1/lives/{liveroom_id}/chatgroup_visitors/?page=1&count=10'
            prefix_url = f'https://api.duanshu.com/fairy/manage/v1/lives/{liveroom_id}/chatgroup_visitors/?'
            max_page = self.get_max_page(prefix_url, max_retries=3, try_pages=3)
            if max_page is None:
                self.logger.warning(f"未找到last_page信息, 爬取失败 ")
                return

            page = 1
            #while page <= max_page:
            while page <=2:
                try:
                    #print(f"正在处理第 {page} 页...")
                    url = f'https://api.duanshu.com/fairy/manage/v1/lives/{liveroom_id}/chatgroup_visitors/?page={page}&count=10'
                    # 页面加载策略
                    # 使用新的函数加载页面
                    html_content, success = self.wait_for_page_load(url)
                    if not success:
                        failed_urls.append(url)
                        page += 1
                        continue

                    # 提取当前页的数据
                    watchers_data = self.extract_watchers_data(html_content)
                    #分析数据失败，可能原因是json格式不对，等等
                    if len(watchers_data) == 0:
                        failed_urls.append(url)
                        page += 1
                        continue

                    all_watchers_data.extend(watchers_data)
                    print(f"第 {page}/{max_page}页成功获取 {len(watchers_data)} 条数据")

                    # 当累积的数据达到batch_size时，写入文件
                    if len(all_watchers_data) >= batch_size:
                        self.save_watchers_data_to_csv(
                            all_watchers_data,
                            liveroom_id,
                            mode='a'
                        )
                        all_watchers_data = []  # 清空缓存
                    # 添加短暂延迟，避免请求过快
                    time.sleep(1)
                    page += 1

                except Exception as e:
                    print(f"处理第 {page} 页时出错: {str(e)}")
                    failed_urls.append(url)

            # 保存失败URL
            if failed_urls:
                self.save_failed_urls(failed_urls, self.failed_liveroom_watchers_url)
            # 保存所有数据
            if all_watchers_data:
                try:
                    self.save_watchers_data_to_csv(all_watchers_data,liveroom_id,mode='a')
                except Exception as e:
                    self.logger.info(f"保存数据时出错: {str(e)}")
            else:
                self.logger.info("没有获取到任何数据")

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
        'username': 'dayixueyuan',  # 替换为你的用户名
        'password': 'taowei'  # 替换为你的密码
    }

    # 创建爬虫实例
    crawler = DuanShuCrawler()

    try:
        #crawler.clean_old_files()
        # 登录
        #crawler.login(config['username'], config['password'])

        start_time = time.time()
        crawler.parse_all_liveroomlist_data(config)
        end_time = time.time()
        execution_time1 = end_time - start_time


        start_time = time.time()
        crawler.parse_liveroom_elements(config)
        end_time = time.time()
        execution_time2 = end_time - start_time


        start_time = time.time()
        crawler.parse_watchers_data(config)
        end_time = time.time()
        execution_time3 = end_time - start_time

        crawler.logger.info(f"parse_all_liveroomlist_data的执行时间：{execution_time1:.2f} 秒")
        crawler.logger.info(f"parse_all_liveroom_elements的执行时间：{execution_time2:.2f} 秒")
        crawler.logger.info(f"parse_watchers_data的执行时间：{execution_time3:.2f} 秒")

    except Exception as e:
        print(f"爬取过程出错: {str(e)}")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()