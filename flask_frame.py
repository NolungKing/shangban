from flask import Flask, request, render_template
import sqlite3
import csv
from flask import jsonify

app = Flask(__name__)

# 数据库查询函数
def fetch_filtered_data(keyword, start_date, end_date, province, city, db_path='news_data.db'):
    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if keyword:
        query += " AND (title LIKE ? OR keywords LIKE ? OR summary LIKE ?)"
        params.extend([f"%{keyword}%"] * 3)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if province:
        query += " AND province = ?"
        params.append(province)
    if city:
        query += " AND city = ?"
        params.append(city)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.route('/')
def index():
    # 获取查询参数
    keyword = request.args.get('keyword', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    province = request.args.get('province', '').strip()
    city = request.args.get('city', '').strip()

    # 获取过滤后的数据
    rows = fetch_filtered_data(keyword, start_date, end_date, province, city)
    rows = [row[1:] for row in rows]  # 剔除 ID
    return render_template('index.html', rows=rows)

# 读取省市映射
def load_province_city_mapping(csv_path="province_city_mapping.csv"):
    mapping = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        for province, city in reader:
            if not province or not city:  # 排除省市为空的行
                continue
            # 规范化处理省名，去除多余的空格
            province = province.strip()
            city = city.strip()

            if province not in mapping:
                mapping[province] = set()  # 使用集合去重
            mapping[province].add(city)
    # 转回列表形式
    return {province: list(cities) for province, cities in mapping.items()}

@app.route('/get_province_city_mapping')
def get_province_city_mapping():
    mapping = load_province_city_mapping()
    return jsonify(mapping)

if __name__ == '__main__':
    app.run(debug=True)