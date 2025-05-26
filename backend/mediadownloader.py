import json
import os
import threading

import requests
from urllib.parse import urlparse, urljoin
import time
import logging
import m3u8
import concurrent.futures

from pycparser.ply.yacc import token


class M3U8Downloader:
    def __init__(self, save_dir, flag = 'inc_download'):
        """初始化下载器"""
        self.save_dir = save_dir
        self.chunk_size = 1024 * 1024  # 1MB
        self.max_retries = 3
        self.thread_timeout = 30  # 线程超时时间（秒）
        self.timeout = 30
        self.maximum_error_ts = 2

        # 初始化线程管理相关的属性
        self.thread_status = {}  # 用于监控线程状态
        self.active_threads = set()  # 记录活跃的线程
        self._stop_event = threading.Event()  # 用于控制线程停止的标志位

        self.max_workers = 20  # 同时下载的线程数

        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            print(f"创建保存目录: {save_dir}")

        self.error_log_file = os.path.join(self.save_dir, 'download_errors.json')
        self.success_log_file = os.path.join(self.save_dir, 'successful_downloads.csv')

        # 初始化成功下载记录
        self.successful_downloads = []

        # 设置日志
        self.setup_logging()
        #如果是增量下载，则需要判断被下载的视频是否已经成功下载过。第一次下载也属于增量下载
        if flag == 'inc_download':
            self.downloaded_urls = self.extract_m3u8_url()
        #如果是处理错误下载，则不需要抽取extract_m3u8_url去判断是否已经下载了。
        else:
            self.downloaded_urls = []
    def extract_m3u8_url(self):
        """从CSV文件中提取包含m3u8的直播间ID

        Args:
            csv_file (str): CSV文件路径

        Returns:
            list: 包含m3u8的直播间ID列表
        """
        csv_file = self.success_log_file
        urls = set()  # 使用集合去重

        try:
            with (open(csv_file, 'r', encoding='utf-8') as f):
                # 跳过标题行
                next(f)
                for line in f:
                    content_id, url, _ = line.strip().split(',')
                    # 检查URL是否包含m3u8
                    if '.m3u8' in url:
                        urls.add(url)
                    #处理图片url，一个直播间可能有多个图片，它们之间通过$$$$$分割，
                    # 因此需要将它们转化为多个图片url在添加到urls里面
                    if 'png' in url or 'jpg' in url or 'jpeg' in url or 'gif' in url:
                        if "$$$$$" in url:
                            image_urls = url.split("$$$$$")
                            for image_url in image_urls:
                                urls.add(image_url)
                        else:
                            urls.add(url)


            self.logger.info(f"从CSV文件中提取到 {len(urls)} 个包含m3u8或图片的直播间ID")
            return list(urls)

        except Exception as e:
            self.logger.error(f"提取m3u8直播间ID时出错: {str(e)}")
            return []


    def save_successful_downloads(self):
        """保存成功下载记录到CSV文件"""
        try:
            # 如果文件不存在，创建文件并写入标题行
            file_exists = os.path.exists(self.success_log_file)
            with open(self.success_log_file, 'a', encoding='utf-8', newline='') as f:
                # 如果文件不存在，先写入标题行
                if not file_exists:
                    f.write("content_id,m3u8_url/image_url,timestamp\n")

                # 写入所有记录
                record = self.successful_downloads[-1]
                f.write(f"{record['content_id']},{record['url']},{record['timestamp']}\n")
        except Exception as e:
            self.logger.error(f"保存成功下载记录时出错: {str(e)}")

    def setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger('M3U8Downloader')
        self.logger.setLevel(logging.INFO)

        # 创建文件处理器
        current_time = time.strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.save_dir, f'download_{current_time}.log')

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def check_server_support_range(self, url):
        """检查服务器是否支持断点续传"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://my.duanshu.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }

            # 发送HEAD请求检查服务器响应头
            response = requests.head(url, headers=headers, timeout=self.timeout)

            # 打印所有响应头，用于调试
            self.logger.info("服务器响应头:")
            for key, value in response.headers.items():
                self.logger.info(f"{key}: {value}")

            # 检查是否支持断点续传
            if 'Accept-Ranges' in response.headers:
                self.logger.info(f"服务器支持断点续传: {response.headers['Accept-Ranges']}")
                return True
            else:
                self.logger.info("服务器不支持断点续传")
                return False

        except Exception as e:
            self.logger.error(f"检查断点续传支持时出错: {str(e)}")
            return False

    def download_file(self, url, filename, is_ts=False):
        """下载文件，支持断点续传"""
        temp_file = f"{filename}.temp"
        max_retries = 3
        retry_count = 0

        # 首先检查服务器是否支持断点续传
        supports_range = self.check_server_support_range(url)

        while retry_count < max_retries:
            try:
                # 添加请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://my.duanshu.com/',
                    'Accept': '*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                }

                # 检查是否存在未完成的下载
                downloaded_size = 0
                if os.path.exists(temp_file) and supports_range:
                    downloaded_size = os.path.getsize(temp_file)
                    self.logger.info(f"发现未完成的下载: {filename}, 已下载: {downloaded_size} bytes")
                    headers['Range'] = f'bytes={downloaded_size}-'
                else:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.logger.info("服务器不支持断点续传，删除临时文件重新下载")

                # 开始下载
                with requests.get(url, headers=headers, stream=True, timeout=self.timeout) as response:
                    response.raise_for_status()

                    # 获取文件总大小
                    total_size = int(response.headers.get('content-length', 0))

                    # 打开文件进行写入
                    mode = 'ab' if downloaded_size > 0 else 'wb'
                    with open(temp_file, mode) as f:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)

                                # 计算下载进度
                                #if total_size > 0:
                                #    progress = (downloaded_size / total_size) * 100
                                #    if is_ts:
                                #        self.logger.debug(f"TS片段下载进度: {progress:.2f}%")
                                #    else:
                                #        self.logger.info(f"下载进度: {progress:.2f}%")

                # 下载完成后重命名文件
                if os.path.exists(filename):
                    os.remove(filename)  # 如果目标文件已存在，先删除
                os.rename(temp_file, filename)

                if is_ts:
                    self.logger.debug(f"TS片段下载完成: {filename}")
                else:
                    self.logger.info(f"文件下载完成: {filename}")
                return True

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 416:  # Range Not Satisfiable
                    self.logger.warning(f"断点续传失败，重新开始下载: {str(e)}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    retry_count += 1
                    continue
                else:
                    self.logger.error(f"下载文件时出错: {str(e)}")
                    return False
            except Exception as e:
                self.logger.error(f"下载文件时出错: {str(e)}")
                return False
            finally:
                # 如果下载失败，删除临时文件
                if not os.path.exists(filename) and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass

        self.logger.error(f"下载失败，已达到最大重试次数: {max_retries}")
        return False

    def download_ts_segment(self, url, filename, headers):
        """下载单个ts片段，增加超时和标志位控制"""
        thread_id = threading.get_ident()
        self.thread_status[thread_id] = {
            "start_time": time.time(),
            "status": "running",
            "url": url,
            "filename": filename,
            "last_active": time.time()  # 记录最后活动时间
        }
        self.active_threads.add(thread_id)

        try:
            # 开始下载
            with requests.get(url, headers=headers, stream=True, timeout=self.timeout,
                              allow_redirects=True) as response:
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                with open(filename, 'wb') as f:
                    downloaded_size = 0
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        # 检查是否需要停止
                        if self._stop_event.is_set():
                            self.logger.info(f"线程 {thread_id} 被要求停止")
                            return False

                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # 更新最后活动时间
                            self.thread_status[thread_id]["last_active"] = time.time()

                            # 检查是否超时
                            if time.time() - self.thread_status[thread_id]["start_time"] > self.thread_timeout:
                                self.logger.warning(f"线程 {thread_id} 下载超时")
                                return False

            self.thread_status[thread_id]["status"] = "completed"
            return True

        except Exception as e:
            self.thread_status[thread_id]["status"] = "failed"
            self.thread_status[thread_id]["error"] = str(e)
            self.logger.error(f"下载TS片段时出错: {str(e)}")
            return False
        finally:
            # 清理线程状态
            if thread_id in self.thread_status:
                del self.thread_status[thread_id]
            if thread_id in self.active_threads:
                self.active_threads.remove(thread_id)

    def check_thread_health(self):
        """检查线程健康状态"""
        current_time = time.time()
        dead_threads = []

        for thread_id, status in self.thread_status.items():
            # 检查线程是否超时
            if current_time - status["start_time"] > self.thread_timeout:
                dead_threads.append((thread_id, status))
                continue

            # 检查线程是否长时间没有活动
            if current_time - status["last_active"] > 30:  # 30秒没有活动视为僵死
                dead_threads.append((thread_id, status))

        return dead_threads

    def download_vzan_image(self, image_url, save_dir, authorization, image_name=None):
            """
            专门用于下载微赞图片的函数

            Args:
                image_url (str): 图片URL
                save_dir (str): 保存目录
                image_name (str, optional): 图片名称，如果不提供则从URL中提取

            Returns:
                tuple: (success, saved_path)
                    - success: 是否下载成功
                    - saved_path: 保存的路径，如果失败则为None
            """
            try:
                self.logger.info(f"开始下载微赞图片: {image_url}")

                # 检查URL是否为空
                if not image_url or not image_url.strip():
                    self.logger.error("图片URL为空")
                    return False
                # 从URL中提取文件名

                filename = os.path.basename(urlparse(image_url).path)
                if not filename:
                    filename = f"image_{int(time.time())}.jpg"

                # 确保保存目录存在

                # 构建保存路径
                save_path = os.path.join(save_dir, 'images', filename)
                try:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                except Exception as e:
                    self.logger.error(f"创建保存目录失败: {str(e)}")
                    return False

                # 设置请求头
                headers = {
                    'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'authorization': f'Bearer {authorization}',
                    'lid': '11749549',
                    'origin': 'https://live.vzan.com',
                    'referer': 'https://live.vzan.com/',
                    'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="136", "Chromium";v="136"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'image',
                    'sec-fetch-mode': 'no-cors',
                    'sec-fetch-site': 'same-site',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                    'zbid': '11749549'
                }

                # 最多重试3次
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # 发送请求
                        with requests.get(image_url, headers=headers, stream=True, timeout=self.timeout) as response:
                            # 检查响应状态
                            response.raise_for_status()
                            # 检查Content-Type
                            content_type = response.headers.get('content-type', '')
                            if not content_type.startswith('image/'):
                                self.logger.error(f"响应不是图片类型: {content_type}")
                                return False
                            # 获取文件大小
                            file_size = int(response.headers.get('content-length', 0))
                            if file_size == 0:
                                self.logger.error("图片大小为0")
                                return False
                            # 保存图片
                            with open(save_path, 'wb') as f:
                                downloaded_size = 0
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded_size += len(chunk)
                                        # 记录下载进度
                                        #if file_size > 0:
                                        #    progress = (downloaded_size / file_size) * 100
                                        #    self.logger.info(f"下载进度: {progress:.1f}%")
                        # 验证文件是否完整下载
                        if os.path.getsize(save_path) == 0:
                            self.logger.error("下载的文件大小为0")
                            if os.path.exists(save_path):
                                os.remove(save_path)
                            return False
                        self.logger.info(f"成功下载图片: {save_path}")
                        return True

                    except requests.exceptions.RequestException as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"下载图片失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                            time.sleep(1)  # 等待1秒后重试
                        else:
                            self.logger.error(f"下载图片失败，已达到最大重试次数: {str(e)}")
                            if os.path.exists(save_path):
                                os.remove(save_path)
                            return False

            except Exception as e:
                self.logger.error(f"下载图片时发生错误: {str(e)}")
                if 'save_path' in locals() and os.path.exists(save_path):
                    os.remove(save_path)
                return False


    def download_duanshu_image(self, url, save_dir, authorization=None):
        """下载图片，使用简单重试机制"""
        try:
            # 从URL中提取文件名
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = f"image_{int(time.time())}.jpg"

            # 构建保存路径
            if save_dir is None:
                save_dir = self.save_dir
            save_path = os.path.join(save_dir, 'images', filename)

            # 确保图片保存目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 添加请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://my.duanshu.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }

            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    # 开始下载
                    with requests.get(url, headers=headers, stream=True, timeout=self.timeout) as response:
                        response.raise_for_status()

                        # 获取文件总大小
                        total_size = int(response.headers.get('content-length', 0))

                        # 直接写入文件
                        with open(save_path, 'wb') as f:
                            downloaded_size = 0
                            for chunk in response.iter_content(chunk_size=self.chunk_size):
                                if chunk:
                                    f.write(chunk)
                                    downloaded_size += len(chunk)

                                    # 计算下载进度
                                    #if total_size > 0:
                                    #    progress = (downloaded_size / total_size) * 100
                                    #    self.logger.info(f"下载进度: {progress:.2f}%")

                    self.logger.info(f"图片下载完成: {save_path}")
                    return True

                except Exception as e:
                    retry_count += 1
                    self.logger.warning(f"下载图片失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                    if retry_count < max_retries:
                        time.sleep(1)  # 等待1秒后重试
                    continue

            self.logger.error(f"图片下载失败，已达到最大重试次数: {url}")
            return False

        except Exception as e:
            self.logger.error(f"下载图片时出错: {str(e)}")
            return False

    def download_image(self,url, save_dir, authorization):
        if "duanshu" in url:
            return self.download_duanshu_image(url, save_dir)
        if "vzan" in url:
            return self.download_vzan_image(url, save_dir,authorization)

    def download_and_verify_ts_segment(self, url, filename, headers, index):
        """
        下载并验证单个ts片段

        Args:
            url (str): ts片段的URL
            filename (str): 保存的文件路径
            headers (dict): 请求头
            index (int): 片段的索引号

        Returns:
            dict: 包含下载和验证结果的字典
            {
                "success": bool,  # 是否成功
                "index": int,     # 片段索引
                "size": int,      # 文件大小
                "url": str,       # 下载URL
                "error": str      # 错误信息（如果失败）
            }
        """
        try:
            with requests.get(url, headers=headers, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()

                # 获取文件大小
                total_size = int(response.headers.get('content-length', 0))

                # 下载文件
                with open(filename, 'wb') as f:
                    downloaded_size = 0
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                # 验证文件大小
                actual_size = os.path.getsize(filename)
                if actual_size != total_size:
                    raise Exception(f"文件大小不匹配: 预期 {total_size}, 实际 {actual_size}")

                # 验证文件是否为空
                if actual_size == 0:
                    raise Exception("下载的文件大小为0")

                # 验证文件是否可读
                try:
                    with open(filename, 'rb') as f:
                        # 读取文件头部，检查是否是有效的ts文件
                        header = f.read(4)
                        if not header:
                            raise Exception("无法读取文件头部")
                except Exception as e:
                    raise Exception(f"文件验证失败: {str(e)}")

                return True
        except requests.exceptions.RequestException as e:
            return False
        except Exception as e:
            return False


    def download_m3u8(self, url, save_dir=None):
        # 初始化结果
        result = {
            "success": True,
            "error": None,
            "failed_ts_segments": [],
            "ts_urls": [],
            "download_start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "download_end_time": None,
            "total_segments": 0,
            "successful_segments": 0,
            "failed_segments": 0
        }

        try:
            # 使用指定的保存目录或默认目录
            if save_dir is None:
                save_dir = self.save_dir

            # 创建视频保存目录
            video_dir = os.path.join(save_dir, 'videos')
            os.makedirs(video_dir, exist_ok=True)
            self.logger.info(f"视频文件将保存在: {video_dir}")

            # 下载m3u8文件
            m3u8_filename = os.path.join(video_dir, 'playlist.m3u8')
            self.logger.info(f"开始下载m3u8文件: {url}")

            # 模拟VLC的请求头
            headers = {
                'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Range': 'bytes=0-',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
            }

            # 创建session来保持连接
            session = requests.Session()
            session.max_redirects = 5

            # 尝试下载m3u8文件
            response = session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            # 保存m3u8文件
            with open(m3u8_filename, 'wb') as f:
                f.write(response.content)

            self.logger.info("m3u8文件下载成功")

            # 解析m3u8文件
            with open(m3u8_filename, 'r') as f:
                m3u8_content = f.read()

            playlist = m3u8.loads(m3u8_content)

            # 获取所有ts片段的URL
            ts_urls = []
            for segment in playlist.segments:
                ts_url = urljoin(url, segment.uri)
                #print("ts_url", ts_url)
                ts_urls.append(ts_url)

            result["ts_urls"] = ts_urls
            result["total_segments"] = len(ts_urls)
            self.logger.info(f"找到 {len(ts_urls)} 个视频片段")

            # 创建ts文件保存目录
            ts_dir = os.path.join(video_dir, 'ts')
            os.makedirs(ts_dir, exist_ok=True)

            # 使用线程池并发下载ts片段
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                self.logger.info(f"开始下载 {len(ts_urls)} 个视频片段")

                # 提交所有下载任务
                for i, ts_url in enumerate(ts_urls[:7]):
                    ts_filename = os.path.join(ts_dir, f'segment_{i:04d}.ts')
                    future = executor.submit(self.download_and_verify_ts_segment, ts_url, ts_filename, headers, i)
                    futures.append((i, ts_url, future))
                print("1")
                # 等待所有下载完成，同时监控线程健康状态
                while futures:
                    # 检查失败数量是否超过限制
                    if result["failed_segments"] >= self.maximum_error_ts:
                        print("2-1")
                        self.logger.error(f'失败片段数量超过{self.maximum_error_ts}个，停止当前视频下载')
                        # 取消所有未完成的下载任务
                        for _, _, future in futures:
                            future.cancel()
                        # 更新结果
                        futures.clear()
                        result["success"] = False
                        result["error"] = f'失败片段数量超过{self.maximum_error_ts}个，停止当前视频下载'
                        result["download_end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        result['failed_m3u8'] = None
                        # 清空futures列表，退出while循环，继续处理下一个视频

                        return result

                    # 检查线程健康状态
                    current_time = time.time()
                    for thread_id, status in list(self.thread_status.items()):
                        # 检查线程是否超时或僵死
                        if (current_time - status["start_time"] > self.thread_timeout or
                                current_time - status.get("last_active", status["start_time"]) > 30):
                            self.logger.warning(f"发现僵死线程 {thread_id}，正在重启")
                            # 找到对应的future
                            for idx, (i, ts_url, future) in enumerate(futures):
                                if future.done():
                                    continue
                                # 取消旧的future
                                future.cancel()
                                # 创建新的下载任务
                                new_future = executor.submit(
                                    self.download_and_verify_ts_segment,
                                    ts_url,
                                    os.path.join(ts_dir, f'segment_{i:04d}.ts'),
                                    headers,
                                    i
                                )
                                futures[idx] = (i, ts_url, new_future)
                                break

                    # 检查已完成的future
                    for i, ts_url, future in futures[:]:
                        try:
                            if future.done():
                                if not future.result():
                                    self.logger.error(f"TS片段 {i} 下载失败: {ts_url}")
                                    result["failed_ts_segments"].append({
                                        "url": ts_url,
                                        "segment_index": i,
                                        "error": "TS片段下载失败",
                                        "total_segments": len(ts_urls),
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "retry_count": 0
                                    })
                                    result["failed_segments"] += 1
                                else:
                                    result["successful_segments"] += 1
                                futures.remove((i, ts_url, future))
                        except concurrent.futures.TimeoutError:
                            self.logger.error(f"TS片段 {i} 下载超时: {ts_url}")
                            result["failed_ts_segments"].append({
                                "url": ts_url,
                                "segment_index": i,
                                "error": "下载超时",
                                "total_segments": len(ts_urls),
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "retry_count": 0
                            })
                            result["failed_segments"] += 1
                            futures.remove((i, ts_url, future))
                        except Exception as e:
                            self.logger.error(f"TS片段 {i} 下载出错: {str(e)}")
                            result["failed_ts_segments"].append({
                                "url": ts_url,
                                "segment_index": i,
                                "error": str(e),
                                "total_segments": len(ts_urls),
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "retry_count": 0
                            })
                            result["failed_segments"] += 1
                            futures.remove((i, ts_url, future))

                    time.sleep(1)

                # 更新下载结束时间
                result["download_end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

                # 检查是否有失败的片段
                if result["failed_ts_segments"]:
                    result["success"] = False
                    result["error"] = f"有 {len(result['failed_ts_segments'])} 个TS片段下载失败"
                    self.logger.error(result["error"])
                    # 记录详细的失败统计
                    self.logger.error(f"下载统计: 总数={result['total_segments']}, "
                                      f"成功={result['successful_segments']}, "
                                      f"失败={result['failed_segments']}")
                else:
                    self.logger.info("所有视频片段下载完成")
                    self.logger.info(f"下载统计: 总数={result['total_segments']}, "
                                     f"成功={result['successful_segments']}, "
                                     f"失败={result['failed_segments']}")



                return result

        except requests.exceptions.RequestException as e:
            error_msg = f"下载m3u8文件时出错: {str(e)}"
            self.logger.error(error_msg)
            result["success"] = False
            result["error"] = error_msg
            result["download_end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return result
        except Exception as e:
            error_msg = f"处理m3u8文件时出错: {str(e)}"
            self.logger.error(error_msg)
            result["success"] = False
            result["error"] = error_msg
            result["download_end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return result


    def process_data(self, data, token):
        """处理输入数据(一个直播间的视频和图像)，下载视频和图片"""
        try:
            # 解析数据
            fields = data.split(',')
            if len(fields) < 2:
                self.logger.error("数据格式错误")
                return False

            content_id = fields[0]  # 获取ID
            self.logger.info(f"处理内容ID: {content_id}")

            # 创建以ID命名的目录，使用短路径
            content_dir = os.path.join(self.save_dir, content_id)  # 只使用ID的前8位
            os.makedirs(content_dir, exist_ok=True)
            self.logger.info(f"创建内容目录: {content_dir}")

            # 创建错误记录文件

            # 初始化错误记录
            error_record = {
                "content_id": content_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "failed_images": [],
                "failed_m3u8": None,
                "total_ts_segments": 0
            }

            # 提取视频URL
            video_url = None
            for field in fields:
                if '.m3u8' in field and (field.startswith('http://') or field.startswith('https://')):
                    video_url = field
                    break

            # 提取图片URL
            image_urls = []
            for field in fields:
                if field.startswith(('http://', 'https://')):
                    urls = field.split(';')
                    for url in urls:
                        url = url.strip()
                        if url and ('.png' in url or '.jpg' in url or 'gif' in url or 'jpeg' in url):
                            image_urls.append(url)

            # 去重图片URL
            image_urls = list(set(image_urls))

            # 下载图片
            if image_urls:
                self.logger.info(f"开始下载 {len(image_urls)} 张图片")
                success_flag = True
                for i, url in enumerate(image_urls, 1):
                    self.logger.info(f"下载第 {i}/{len(image_urls)} 张图片: {url}")
                    try:
                        # 使用content_dir而不是self.save_dir
                        #if not self.download_image(url, content_dir):
                         if url in self.downloaded_urls:
                            self.logger.info(f"该直播间的图片已经下载，{url}，跳过")
                            continue
                         if not self.download_image(url, content_dir,token):
                            error_record["failed_images"].append({
                                "url": url,
                                "error": "图片下载失败"
                            })
                            success_flag = False
                         else:
                             self.logger.info(f"该直播间的图片下载成功，{url}")
                    except Exception as e:
                        error_record["failed_images"].append({
                            "url": url,
                            "error": str(e)
                        })
                        success_flag = False

                if success_flag:
                    content_id = os.path.basename(content_dir)
                    successful_download = {
                            "content_id": content_id,
                            "url": '$$$$$'.join(str(x) for x in image_urls) if image_urls else "",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.successful_downloads.append(successful_download)
                    self.save_successful_downloads()
                    self.logger.info(f"已记录成功下载的images: {image_urls} (直播间ID: {content_id})")


            # 下载视频
            if video_url:
                self.logger.info(f"开始下载视频: {video_url}")
                try:
                    # 使用content_dir而不是self.save_dir
                    content_id = os.path.basename(content_dir)
                    #print(content_id,self.downloaded_content_ids)
                    #if content_id in self.downloaded_content_ids:
                    if video_url in self.downloaded_urls:
                        self.logger.info(f"该直播间的视频已经下载，{video_url}，跳过")
                        return True
                    m3u8_result = self.download_m3u8(video_url, content_dir)
                    if  m3u8_result["success"]:
                        # 记录成功下载的m3u8信息

                        successful_download = {
                            "content_id": content_id,
                            "url": video_url,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        self.successful_downloads.append(successful_download)
                        self.save_successful_downloads()
                        self.logger.info(f"已记录成功下载的m3u8: {video_url} (直播间ID: {content_id})")
                    else:
                        error_record["failed_m3u8"] = {
                            "url": video_url,
                            "error": m3u8_result["error"],
                            "failed_ts_segments": m3u8_result["failed_ts_segments"],
                            "total_ts_segments": len(m3u8_result.get("ts_urls", []))
                        }

                except Exception as e:
                    error_record["failed_m3u8"] = {
                        "url": video_url,
                        "error": str(e),
                        "failed_ts_segments": [],
                        "total_ts_segments": 0
                    }

            # 如果有错误，保存到JSON文件
            if error_record["failed_images"] or error_record["failed_m3u8"]:
                with open(self.error_log_file, 'a', encoding='utf-8') as f:
                    # 检查文件是否为空
                    if os.path.getsize(self.error_log_file) == 0:
                        # 如果文件为空，直接写入JSON对象
                        f.write(json.dumps(error_record, ensure_ascii=False))
                    else:
                        # 如果文件不为空，先写入换行符，再写入JSON对象
                        f.write('\n' + json.dumps(error_record, ensure_ascii=False))
                self.logger.info(f"错误记录已保存到: {self.error_log_file}")
                self.logger.info(f"错误记录已保存到: {self.error_log_file}")

            return True

        except Exception as e:
            self.logger.error(f"处理数据时出错: {str(e)}")
            return False

    def read_and_process_file(self, file_path, vzan_token):
        """读取CSV文件并处理每一行数据"""
        error_records = []  # 用于记录处理失败的数据
        success_count = 0
        error_count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 读取标题行
                header = f.readline().strip()
                self.logger.info(f"文件标题: {header}")

                # 读取每一行数据
                for line_num, line in enumerate(f, 2):  # 从第2行开始计数
                    try:
                        line = line.strip()
                        if not line:  # 跳过空行
                            continue

                        self.logger.info(f"正在处理第 {line_num} 行数据")

                        # 处理数据
                        if self.process_data(line,vzan_token):
                            success_count += 1
                            self.logger.info(f"第 {line_num} 行数据处理成功")
                        else:
                            error_count += 1
                            error_records.append({
                                "line_number": line_num,
                                "data": line,
                                "error": "处理失败",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            self.logger.error(f"第 {line_num} 行数据处理失败")

                    except Exception as e:
                        error_count += 1
                        error_records.append({
                            "line_number": line_num,
                            "data": line,
                            "error": str(e),
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        self.logger.error(f"处理第 {line_num} 行数据时出错: {str(e)}")
                        continue  # 继续处理下一行

            # 保存错误记录
            if error_records:
                error_log_file = os.path.join(self.save_dir, 'processing_errors.json')
                with open(error_log_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "total_records": line_num - 1,
                        "success_count": success_count,
                        "error_count": error_count,
                        "error_records": error_records,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }, f, ensure_ascii=False, indent=2)
                self.logger.info(f"错误记录已保存到: {error_log_file}")

            # 输出处理统计
            self.logger.info(f"处理完成: 总数={line_num - 1}, 成功={success_count}, 失败={error_count}")
            return True

        except Exception as e:
            self.logger.error(f"读取文件时出错: {str(e)}")
            return False

    def retry_failed_downloads(self, token):
        """
        读取错误日志并重新下载失败的内容

        Args:
            token (str): 授权token
        """
        try:
            # 首先检查错误日志文件是否存在
            if not os.path.exists(self.error_log_file):
                self.logger.info(f"错误日志文件不存在: {self.error_log_file}")
                return


            self.logger.info(f"开始处理错误日志: {self.error_log_file}")

            # 读取错误日志
            # 读取错误日志
            # 读取错误日志
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                error_records = []

                # 将内容按完整的JSON对象分割
                json_objects = []
                current_object = ""
                brace_count = 0

                for line in content.split('\n'):
                    current_object += line + '\n'
                    brace_count += line.count('{') - line.count('}')

                    if brace_count == 0 and current_object.strip():
                        # 找到一个完整的JSON对象
                        json_objects.append(current_object.strip())
                        current_object = ""

                # 解析每个JSON对象
                for json_str in json_objects:
                    try:
                        record = json.loads(json_str)
                        error_records.append(record)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"解析JSON记录时出错: {str(e)}")
                        self.logger.error(f"问题JSON字符串: {json_str}")
                        continue

            self.logger.info(f"从错误日志中读取到 {len(error_records)} 条记录")
            # 如果没有成功解析任何记录，抛出异常
            if not error_records:
                raise Exception("错误日志文件中没有有效的记录")

            # 处理每条错误记录
            for record in error_records:
                content_id = record.get('content_id')
                if not content_id:
                    continue

                self.logger.info(f"处理内容ID: {content_id}")

                # 创建内容目录
                content_dir = os.path.join(self.save_dir, content_id)
                os.makedirs(content_dir, exist_ok=True)

                # 处理失败的图片
                failed_images = record.get('failed_images', [])
                if failed_images:
                    self.logger.info(f"重新下载 {len(failed_images)} 张失败的图片")
                    success_images = []
                    for image_info in failed_images:
                        url = image_info.get('url')
                        if not url:
                            continue

                        try:
                            if self.download_image(url, content_dir, token):
                                success_images.append(image_info)
                                self.logger.info(f"成功重新下载图片: {url}")
                            else:
                                self.logger.error(f"重新下载图片失败: {url}")
                        except Exception as e:
                            self.logger.error(f"重新下载图片时出错: {str(e)}")

                    # 更新错误记录中的失败图片列表
                    record['failed_images'] = [img for img in failed_images if img not in success_images]

                # 处理失败的m3u8
                failed_m3u8 = record.get('failed_m3u8')
                if failed_m3u8:
                    url = failed_m3u8.get('url')
                    failed_ts_segments = failed_m3u8.get('failed_ts_segments', [])

                    if url:
                        if failed_ts_segments:
                            # 如果有失败的ts片段，只重新下载这些片段
                            self.logger.info(f"重新下载 {len(failed_ts_segments)} 个失败的ts片段")
                            success_ts = []

                            # 创建ts文件保存目录
                            video_dir = os.path.join(content_dir, 'videos')
                            ts_dir = os.path.join(video_dir, 'ts')
                            os.makedirs(ts_dir, exist_ok=True)

                            # 设置请求头
                            headers = {
                                'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18',
                                'Accept': '*/*',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Accept-Encoding': 'gzip, deflate, br',
                                'Connection': 'keep-alive',
                                'Range': 'bytes=0-',
                                'Sec-Fetch-Dest': 'empty',
                                'Sec-Fetch-Mode': 'cors',
                                'Sec-Fetch-Site': 'cross-site',
                                'Pragma': 'no-cache',
                                'Cache-Control': 'no-cache',
                            }

                            # 使用线程池并发下载失败的ts片段
                            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                                futures = []

                                for ts_info in failed_ts_segments:
                                    ts_url = ts_info.get('url')
                                    segment_index = ts_info.get('segment_index')
                                    self.logger.info(f"处理ts片段: URL={ts_url}, segment_index={segment_index}")
                                    if ts_url and segment_index is not None:
                                        ts_filename = os.path.join(ts_dir, f'segment_{segment_index:04d}.ts')
                                        future = executor.submit(self.download_and_verify_ts_segment, ts_url, ts_filename, headers, segment_index)
                                        futures.append((ts_info, future))

                                # 等待所有下载完成
                                for ts_info, future in futures:
                                    try:
                                        if future.result():
                                            success_ts.append(ts_info)
                                            self.logger.info(f"成功重新下载ts片段: {ts_info['url']}")
                                        else:
                                            self.logger.error(f"重新下载ts片段失败: {ts_info['url']}")
                                    except Exception as e:
                                        self.logger.error(f"重新下载ts片段时出错: {str(e)}")

                            # 更新失败的ts片段列表
                            failed_m3u8['failed_ts_segments'] = [ts for ts in failed_ts_segments if
                                                                 ts not in success_ts]

                            # 如果所有ts片段都下载成功，清除failed_m3u8
                            if not failed_m3u8['failed_ts_segments']:
                                record['failed_m3u8'] = None
                                self.logger.info("所有ts片段下载成功")
                                self.logger.info(f"成功重新下载m3u8: {url}")
                            else:
                                self.logger.error(f"仍有 {len(failed_m3u8['failed_ts_segments'])} 个ts片段下载失败")
                        else:
                            # 如果没有失败的ts片段，说明是m3u8文件本身下载失败，需要重新下载整个m3u8
                            self.logger.info(f"重新下载失败的m3u8: {url}")
                            try:
                                m3u8_result = self.download_m3u8(url, content_dir)
                                if m3u8_result["success"]:
                                    self.logger.info(f"成功重新下载m3u8: {url}")
                                    record['failed_m3u8'] = None
                                else:
                                    # 更新失败信息
                                    record['failed_m3u8'] = {
                                        "url": url,
                                        "error": m3u8_result["error"],
                                        "failed_ts_segments": m3u8_result["failed_ts_segments"],
                                        "total_ts_segments": len(m3u8_result.get("ts_urls", []))
                                    }
                                    self.logger.error(f"重新下载m3u8失败: {url}")
                            except Exception as e:
                                record['failed_m3u8'] = {
                                    "url": url,
                                    "error": str(e),
                                    "failed_ts_segments": [],
                                    "total_ts_segments": 0
                                }
                                self.logger.error(f"重新下载m3u8时出错: {str(e)}")

                # 更新错误记录的时间戳
                #print("1")
                if (record.get('failed_m3u8') is None and
                        (not record.get('failed_images') or len(record.get('failed_images', [])) == 0)):
                    #print("2")
                    self.logger.info(f'所有下载失败的图片和视频都重新下载成功，更新{self.success_log_file}文件')
                    successful_download = {
                        "content_id": content_id,
                        "url": url,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.successful_downloads.append(successful_download)
                    self.save_successful_downloads()

                record['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")

            # 保存更新后的错误记录
            updated_error_records = [record for record in error_records
                                     if record.get('failed_images') or record.get('failed_m3u8')]

            if updated_error_records:
                with open(self.error_log_file, 'w', encoding='utf-8') as f:
                    for record in updated_error_records:
                        # 保持原始格式，每个记录单独一行
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
                self.logger.info(f"更新后的错误记录已保存到: {self.error_log_file}")
            else:
                # 只有在所有记录都成功处理后才删除文件
                if all(not record.get('failed_images') and not record.get('failed_m3u8') for record in error_records):
                    os.remove(self.error_log_file)
                    self.logger.info("所有内容下载成功，已删除错误日志文件")
                else:
                    self.logger.warning("错误日志文件格式可能有问题，保留文件以供检查")
        except Exception as e:
            self.logger.error(f"处理错误日志时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())


def main():
    # 首先执行duanshu_mylive_parser.py的main函数
    from dynamicCrawler_duanshu import main as parser_main
    # parser_main()

    # 创建下载器实例
    downloader = M3U8Downloader('D:\\duanshu\\downloaded_media',"download_for_error_logs")
    #downloader = M3U8Downloader('D:\\duanshu\\downloaded_media')
    # 处理文件
    start_time = time.time()
    file_path = 'liveroomlist_inc_vzan.csv'  # 替换为您的输入文件路径
    #file_path = "liveroomlist_elements_inc_duanshu.csv"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2IjoiNiIsInJvbCI6IjIiLCJhaWQiOiI0OWU3YTk0ZC0xN2NkLTQ4NTUtYjAxNC0wMzFmMThjMmIzODkiLCJ1aWQiOiIyMjM4NTA1MDkiLCJsaWQiOiIxMTc0OTU0OSIsImFwcGlkIjoiMTgiLCJ0eXBlIjoiMCIsIm5iZiI6MTc0ODIyNjgyMSwiZXhwIjoxNzQ4MjcwMDUxLCJpYXQiOjE3NDgyMjY4NTEsImlzcyI6InZ6YW4iLCJhdWQiOiJ2emFuIn0.3hJZh2m3NjIrI3K2poqa_yYTn8ec4ha0xvk_XBwoCBc"
    #downloader.read_and_process_file(file_path, token)
    downloader.retry_failed_downloads(token)
    end_time = time.time()
    execution_time = end_time - start_time

    downloader.logger.info(f"总执行时间：{execution_time:.2f} 秒")


if __name__ == "__main__":
    main()