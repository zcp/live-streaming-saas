from playwright.sync_api import sync_playwright
import time
import json
import csv
import os
from datetime import datetime
from bs4 import BeautifulSoup


class DuanShuCrawler:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)  # 设置为False可以看到浏览器操作
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def login(self, username, password):
        """登录短书"""
        try:
            print("正在登录短书...")
            self.page.goto('https://www.duanshu.com/login')

            # 等待页面完全加载
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)  # 额外等待确保页面加载完成

            # 打印页面标题，帮助调试
            print(f"页面标题: {self.page.title()}")

            # 等待登录表单加载
            print("等待登录表单加载...")
            self.page.wait_for_selector('input[type="text"]', timeout=10000)
            self.page.wait_for_selector('input[type="password"]', timeout=10000)

            # 使用更精确的选择器
            print("正在输入用户名和密码...")
            # 用户名输入框
            self.page.fill('input[type="text"]', username)
            # 密码输入框
            self.page.fill('input[type="password"]', password)

            # 点击登录按钮
            print("点击登录按钮...")
            self.page.click('button[type="submit"]')

            # 等待登录成功并处理对话框
            print("等待登录成功...")
            try:
                # 等待对话框出现
                self.page.wait_for_selector('.el-message-box__btns button', timeout=5000)
                # 点击确定按钮
                self.page.click('.el-message-box__btns button')
                print("已关闭登录成功对话框")
            except:
                print("未检测到登录成功对话框")

            # 等待页面跳转完成
            self.page.wait_for_load_state('networkidle')
            print("登录成功！")
            return True

        except Exception as e:
            print(f"登录失败: {str(e)}")
            # 打印页面内容，帮助调试
            #print("当前页面内容:")
            #self.page.goto('https://my.duanshu.com/live/list')
            #print(self.page.content())
            return True

    def get_live_urls(self):
        """获取所有直播URL"""
        print("正在获取直播列表...")
        self.page.goto('https://my.duanshu.com/live/list')
        self.page.wait_for_load_state('networkidle')
        time.sleep(2)  # 等待页面完全加载

        # 存储标题和URL的映射
        title_url_map = {}

        # 获取所有标题元素
        title_elements = self.page.query_selector_all('.router-title')
        print(f"找到 {len(title_elements)} 个标题元素")

        for title_element in title_elements:
            try:
                # 获取标题文本
                title = title_element.inner_text().strip()
                if not title:
                    continue

                print(f"正在处理标题: {title}")

                # 点击标题
                title_element.click()

                # 等待新页面加载
                self.page.wait_for_load_state('networkidle')
                time.sleep(1)

                # 获取当前URL
                current_url = self.page.url
                print(f"获取到URL: {current_url}")

                # 存储标题和URL的映射
                title_url_map[title] = current_url

                # 返回上一页
                self.page.go_back()

                # 等待列表页面重新加载
                self.page.wait_for_load_state('networkidle')
                time.sleep(1)

            except Exception as e:
                print(f"处理标题时出错: {str(e)}")
                continue

        return title_url_map

    def parse_live_data(self):
        self.page.goto('https://my.duanshu.com/live/list')
        html_content = self.page.content()
        print(html_content)
        soup = BeautifulSoup(html_content, 'html.parser')

        # 获取所有直播URL
        title_url_map = self.get_live_urls(html_content)

        # 找到所有直播行
        live_rows = soup.find_all('div', class_='table-row-box')

        data = []
        for row in live_rows:
            try:
                # 获取主行数据
                main_row = row.find('div', class_='table-row-main')

                # 提取标题和链接
                title_element = main_row.find('p', class_='router-title')
                title = title_element.text.strip()

                # 获取对应的URL
                live_link = title_url_map.get(title, '')

                # 提取直播类型
                type_div = main_row.find_all('div', attrs={'type': 'row'})[2]
                live_type = type_div.find('p').text.strip()

                # 提取访客数据
                visitors_div = main_row.find_all('div', attrs={'type': 'row'})[3]
                visitors_text = visitors_div.get_text(strip=True)
                visitors = visitors_text.replace(live_type, '').strip()
                visitors = visitors.replace('人', '').strip()

                # 提取销量
                sales = main_row.find('div', class_='sales-total-click').text.strip()

                # 提取状态
                status = main_row.find('span', class_='state-up').text.strip() if main_row.find('span',
                                                                                                class_='state-up') else '未上架'

                # 提取序号
                order = main_row.find_all('div', attrs={'type': 'row'})[5].find('span').text.strip()

                # 提取直播状态
                expand_row = row.find('div', class_='table-row-expand')
                live_status = expand_row.find('span', class_='font-12-999').text.strip() if expand_row else '未知'

                # 提取开播时间
                start_time = ''
                if expand_row:
                    time_span = expand_row.find_all('span', class_='font-12-999')[-1]
                    if time_span:
                        start_time = time_span.text.replace('开播时间：', '').strip()

                # 打印调试信息
                print(f"标题: {title}")
                print(f"直播链接: {live_link}")
                print(f"直播类型: {live_type}")
                print(f"访客数据: {visitors}")
                print("-------------------")

                data.append({
                    '标题': title,
                    '直播链接': live_link,
                    '直播类型': live_type,
                    '访客数/浏览量': visitors,
                    '销量': sales,
                    '状态': status,
                    '序号': order,
                    '直播状态': live_status,
                    '开播时间': start_time
                })
            except Exception as e:
                print(f"处理行数据时出错: {str(e)}")
                continue

        return data

    def save_to_csv(self, data, filename):
        """保存数据到CSV文件"""
        if not data:
            print("没有数据可保存")
            return

        try:
            os.makedirs('output', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'output/{filename}_{timestamp}.csv'

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"数据已保存到: {filename}")

        except Exception as e:
            print(f"保存数据失败: {str(e)}")

    def close(self):
        """关闭浏览器"""
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
        # 登录
        if crawler.login(config['username'], config['password']):
            # 解析直播数据
            data = crawler.parse_live_data()
            # 保存数据
            crawler.save_to_csv(data, 'live_data')

    except Exception as e:
        print(f"爬取过程出错: {str(e)}")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()