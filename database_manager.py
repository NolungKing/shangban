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

    # 插入数据
    cursor.execute('''
        INSERT OR IGNORE INTO articles (title, date, province, city, keywords, summary, url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)

    connection.commit()
    connection.close()

# 查询所有文章
def query_all_articles(db_name="news_data.db"):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM articles')
    articles = cursor.fetchall()

    connection.close()
    return articles
