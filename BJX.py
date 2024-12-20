import re
import pandas as pd
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from datetime import datetime, timedelta
import schedule
import time
import threading
import database_manager

# 初始化数据库
def initialize_database(db_name="news_data.db"):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    # 创建文章数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            province TEXT,
            city TEXT,
            keywords TEXT,
            summary TEXT,
            url TEXT NOT NULL UNIQUE
        )
    ''')

    connection.commit()
    connection.close()

# 插入文章数据
def insert_article(data, db_name="news_data.db"):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    # 插入数据
    cursor.execute('''
        INSERT OR IGNORE INTO articles (title, date, province, city, keywords, summary, url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)

    connection.commit()
    connection.close()

# 加载省市映射表
mapping_file = "province_city_mapping.csv"
df_mapping = pd.read_csv(mapping_file)
china_province = set(df_mapping['province'].tolist())
china_cities = df_mapping.groupby('province')['city'].apply(list).to_dict()

# 构造正则表达式
province_regex = re.compile("|".join(china_province))
city_regex = re.compile("|".join([city for cities in china_cities.values() for city in cities]))

# 找到城市所属的省份
def find_province_for_city(city_name):
    match = df_mapping[df_mapping['city'] == city_name]
    if not match.empty:
        return match.iloc[0]['province']
    return None

# 去重并规范化
def deduplicate_and_normalize(items):
    """去重并保持原有顺序"""
    seen = set()
    return [item for item in items if not (item in seen or seen.add(item))]

def collect_news(start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    service = Service('/Users/dylanw/Downloads/chromedriver-mac-x64/chromedriver')
    driver = webdriver.Chrome(service=service)
    wait = WebDriverWait(driver, 50)

    max_pages = 100
    consecutive_invalid_pages = 0  # 连续无效页数计数
    max_consecutive_invalid_pages = 50  # 允许的最大连续无效页数

    for page_num in range(1, max_pages + 1):
        url = f"https://news.bjx.com.cn/zc/{page_num}/"
        driver.get(url)
        try:
            titles = wait.until(ec.presence_of_all_elements_located((By.CSS_SELECTOR, "a[title]")))
            page_has_valid_articles = False  # 当前页是否有有效文章

            for i in range(len(titles)):
                title_text = titles[i].text

                # 过滤关键字
                filter_keywords = ["废", "污", "环境", "公示", "空气", "汇总", "解读", "秸秆", "垃圾"]
                if any(keyword in title_text for keyword in filter_keywords):
                    continue

                # 日期处理
                try:
                    date_text = titles[i].find_element(By.XPATH, "..//following-sibling::span").text
                    date_obj = datetime.strptime(date_text, "%Y-%m-%d")
                except Exception as e:
                    print(f"错误：无法获取日期 - {e}")
                    continue

                # 检查日期范围
                if start_date <= date_obj <= end_date:
                    page_has_valid_articles = True  # 标记当前页有有效文章
                    consecutive_invalid_pages = 0  # 重置无效页计数

                    title_url = titles[i].get_attribute("href")

                    # 打开次级页面并提取内容
                    driver.execute_script("window.open(arguments[0]);", title_url)
                    driver.switch_to.window(driver.window_handles[-1])

                    try:
                        content_text = wait.until(ec.presence_of_element_located((By.ID, "article_cont"))).text
                    except Exception as e:
                        print(f"错误：无法获取文章内容 - {e}")
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue

                    # 提取关键词
                    keywords = []
                    try:
                        keywords_element = driver.find_element(By.ID, "key_word")
                        keywords = [a.text for a in keywords_element.find_elements(By.TAG_NAME, "a")]
                    except Exception:
                        pass

                    # 提取省市信息
                    found_provinces = province_regex.findall(title_text)
                    found_cities = city_regex.findall(title_text)

                    # 筛选有效的省份
                    valid_provinces = set(df_mapping['province'].tolist())
                    valid_cities = set(df_mapping['city'].tolist())

                    # 筛选有效的省份和城市，并只保留第一个
                    first_province = next((province for province in found_provinces if province in valid_provinces), None)
                    first_city = next((city for city in found_cities if city in valid_cities), None)

                    # 补全省信息（如果市名匹配但无省名）
                    if first_city and not first_province:
                        province_from_city = find_province_for_city(first_city)
                        if province_from_city:
                            first_province = province_from_city

                    # 确保最终记录的省和市信息
                    province_text = first_province
                    city_text = first_city

                    # 插入数据库
                    data = [
                        title_text, date_text, province_text, city_text, ", ".join(keywords), content_text[:300],
                        title_url
                    ]
                    database_manager.insert_article(data)
                    print(f"文章已录入：{title_text}")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

            # 如果当前页没有有效文章
            if not page_has_valid_articles:
                consecutive_invalid_pages += 1
                print(f"页面 {page_num} 无有效文章，连续无效页数：{consecutive_invalid_pages}")
                if consecutive_invalid_pages >= max_consecutive_invalid_pages:
                    print("连续无效页数达到最大限制，提前终止爬取")
                    break

        except Exception as e:
            print(f"错误：{e}")

    driver.quit()

# 规范化日期格式
def normalize_date(date_str):
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("日期格式错误，请使用 yyyy/mm/dd 或 yyyy-mm-dd 或 yyyymmdd 格式")

# 手动任务输入和执行逻辑
def manual_crawl():
    try:
        start_date = input("请输入开始日期 (格式: yyyy/mm/dd 或 yyyy-mm-dd 或 yyyymmdd): ").strip()
        start_date = normalize_date(start_date)
        end_date = input("请输入结束日期 (格式: yyyy/mm/dd 或 yyyy-mm-dd 或 yyyymmdd): ").strip()
        end_date = normalize_date(end_date)

        print(f"手动任务开始，爬取日期范围：{start_date} 至 {end_date}")
        collect_news(start_date, end_date)
        print(f"手动任务完成")
    except Exception as e:
        print(f"手动任务失败: {e}")

# 定时任务：每天上午 11:59
def collect_yesterday_news():
    yesterday = datetime.now() - timedelta(days=1)
    start_date = end_date = yesterday.strftime("%Y-%m-%d")
    print(f"正在收集 {start_date} 的新闻...")
    collect_news(start_date, end_date)

# 定时任务调度线程
def schedule_jobs():
    schedule.every().day.at("08:30").do(collect_yesterday_news)
    while True:
        schedule.run_pending()
        time.sleep(1)

# 主程序入口
if __name__ == "__main__":
    initialize_database()

    # 启动定时任务线程
    threading.Thread(target=schedule_jobs, daemon=True).start()

    print("程序启动成功。输入 'run' 手动触发爬取，输入 'exit' 退出程序。")

    while True:
        command = input(">> ").strip().lower()
        if command == "run":
            manual_crawl()
        elif command == "exit":
            print("程序已退出")
            break
        else:
            print("未知命令，请输入 'run' 或 'exit'")
