import sqlite3

# 创建或连接到 SQLite 数据库
def initialize_database(db_name="news_data.db"):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    # 创建文章数据表，url 列具有唯一约束
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


    connection.commit()
    connection.close()

# 插入文章数据
def insert_article(data, db_name="news_data.db"):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    # 保证省市字段仅保留第一条信息
    province_text, city_text = data[2], data[3]  # 省市字段是 data[2] 和 data[3]
    if province_text:
        province_text = province_text.split(",")[0].strip()  # 仅保留第一个省
    if city_text:
        city_text = city_text.split(",")[0].strip()  # 仅保留第一个市

    # 插入数据
    cursor.execute('''
        INSERT OR IGNORE INTO articles (title, date, province, city, keywords, summary, url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data[0], data[1], province_text, city_text, data[4], data[5], data[6]))

    connection.commit()
    connection.close()

# 查询所有文章，支持排序
def query_all_articles(order_by=None, ascending=True, db_name="news_data.db"):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    query = 'SELECT * FROM articles'
    if order_by:
        order = 'ASC' if ascending else 'DESC'
        query += f' ORDER BY {order_by} {order}'

    cursor.execute(query)
    articles = cursor.fetchall()

    connection.close()
    return articles
