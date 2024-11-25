import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd

# 数据库文件路径
db_path = "news_data.db"
PAGE_SIZE = 50  # 每页显示的数据条数

# 读取省份和城市映射
def load_province_city_mapping():
    try:
        df = pd.read_csv('province_city_mapping.csv')
        provinces = df['province'].unique().tolist()
        city_mapping = df.groupby('province')['city'].apply(list).to_dict()
        return provinces, city_mapping
    except Exception as e:
        messagebox.showerror("错误", f"加载省份城市映射失败：{e}")
        return [], {}

# 数据库操作函数
def connect_db():
    return sqlite3.connect(db_path)

def fetch_data(query):
    connection = connect_db()
    try:
        df = pd.read_sql_query(query, connection)
        return df
    except Exception as e:
        messagebox.showerror("错误", f"查询失败：{e}")
    finally:
        connection.close()

def update_record(query):
    connection = connect_db()
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        messagebox.showinfo("成功", "记录更新成功！")
    except Exception as e:
        messagebox.showerror("错误", f"更新失败：{e}")
    finally:
        connection.close()

# GUI 界面
class DatabaseManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite 数据库管理")
        self.current_page = 0  # 当前页码
        self.sort_order_date = True

        # 读取省份和城市映射
        self.provinces, self.city_mapping = load_province_city_mapping()

        # 状态标签
        self.status_label = tk.Label(root, text="")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # 筛选框区域
        self.create_filter_frame()

        # 查询结果表格
        self.create_result_table()

        # 分页按钮区
        self.create_pagination_frame()

        # 初始化数据
        self.all_data = pd.DataFrame()
        self.query_all_data()

    def create_filter_frame(self):
        """创建筛选框区域"""
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, pady=5)

        # 第一分区：标题和关键词
        title_keywords_frame = tk.Frame(filter_frame)
        title_keywords_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        tk.Label(title_keywords_frame, text="标题 (多个用空格分开)").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.title_var = tk.StringVar()
        tk.Entry(title_keywords_frame, textvariable=self.title_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(title_keywords_frame, text="关键词 (多个用空格分开)").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.keywords_var = tk.StringVar()
        tk.Entry(title_keywords_frame, textvariable=self.keywords_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        # 第二分区：省份和城市
        province_city_frame = tk.Frame(filter_frame)
        province_city_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        tk.Label(province_city_frame, text="省份").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.province_var = tk.StringVar()
        self.province_combobox = ttk.Combobox(
            province_city_frame, textvariable=self.province_var, values=self.provinces, state="normal"
        )
        self.province_combobox.grid(row=0, column=1, padx=5, pady=5)
        self.province_combobox.bind("<<ComboboxSelected>>", self.update_city_combobox)

        tk.Label(province_city_frame, text="城市").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.city_var = tk.StringVar()
        self.city_combobox = ttk.Combobox(province_city_frame, textvariable=self.city_var, state="normal")
        self.city_combobox.grid(row=1, column=1, padx=5, pady=5)

        # 第三分区：日期范围和按钮
        date_buttons_frame = tk.Frame(filter_frame)
        date_buttons_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        tk.Label(date_buttons_frame, text="开始日期 (YYYY-MM-DD)").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.start_date_var = tk.StringVar()
        tk.Entry(date_buttons_frame, textvariable=self.start_date_var, width=15).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(date_buttons_frame, text="结束日期 (YYYY-MM-DD)").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.end_date_var = tk.StringVar()
        tk.Entry(date_buttons_frame, textvariable=self.end_date_var, width=15).grid(row=0, column=3, padx=5, pady=5)

        # 按钮一行横向排列
        tk.Button(date_buttons_frame, text="搜索", command=self.apply_filter).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(date_buttons_frame, text="清除筛选", command=self.clear_filter).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(date_buttons_frame, text="按日期排序", command=self.sort_by_date).grid(row=1, column=2, padx=5, pady=5)
        tk.Button(date_buttons_frame, text="导出到 Excel", command=self.export_to_excel).grid(row=1, column=3, padx=5, pady=5)

    def create_result_table(self):
        """创建查询结果表格"""
        self.tree = ttk.Treeview(
            self.root,
            columns=("ID", "Title", "Date", "Province", "City", "Keywords", "Summary", "URL"),
            show="headings",
            selectmode="extended"
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        self.tree.bind("<Double-1>", self.edit_record)

    def create_pagination_frame(self):
        """创建分页按钮区"""
        pagination_frame = tk.Frame(self.root)
        pagination_frame.pack(fill=tk.X, pady=5)

        self.prev_button = tk.Button(pagination_frame, text="上一页", command=self.prev_page, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.page_label = tk.Label(pagination_frame, text="第 1 页")
        self.page_label.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(pagination_frame, text="下一页", command=self.next_page, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.first_page_button = tk.Button(pagination_frame, text="第一页", command=self.first_page)
        self.first_page_button.pack(side=tk.LEFT, padx=5)

        self.last_page_button = tk.Button(pagination_frame, text="最后一页", command=self.last_page)
        self.last_page_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = tk.Button(pagination_frame, text="删除选中记录", command=self.delete_record)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        self.delete_all_button = tk.Button(pagination_frame, text="删除全部", command=self.delete_all_records)
        self.delete_all_button.pack(side=tk.LEFT, padx=5)

    def update_city_combobox(self, event):
        """根据选择的省份更新城市下拉列表"""
        province = self.province_var.get()
        if province in self.city_mapping:
            self.city_combobox['values'] = self.city_mapping[province]
        else:
            self.city_combobox['values'] = []

    def query_all_data(self):
        """查询所有数据"""
        self.all_data = fetch_data("SELECT * FROM articles")
        self.current_page = 0
        self.update_table()

    def apply_filter(self):
        """应用筛选条件"""
        filters = []
        title_condition = self.title_var.get().strip()
        keywords_condition = self.keywords_var.get().strip()
        province_condition = self.province_var.get().strip()
        city_condition = self.city_var.get().strip()
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()

        if title_condition:
            filters.append(f"title LIKE '%{title_condition}%'")
        if keywords_condition:
            filters.append(f"keywords LIKE '%{keywords_condition}%'")
        if province_condition:
            filters.append(f"province = '{province_condition}'")
        if city_condition:
            filters.append(f"city = '{city_condition}'")
        if start_date:
            filters.append(f"date >= '{start_date}'")
        if end_date:
            filters.append(f"date <= '{end_date}'")

        query = "SELECT * FROM articles"
        if filters:
            query += " WHERE " + " AND ".join(filters)

        self.all_data = fetch_data(query)
        self.current_page = 0
        self.update_table()

    def clear_filter(self):
        """清除筛选条件"""
        self.title_var.set("")
        self.keywords_var.set("")
        self.province_var.set("")
        self.city_var.set("")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.query_all_data()

    def update_table(self):
        """更新表格显示"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        start_idx = self.current_page * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_data = self.all_data.iloc[start_idx:end_idx]

        for _, row in page_data.iterrows():
            self.tree.insert("", tk.END, values=row.tolist())

        total_pages = max(1, (len(self.all_data) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_label["text"] = f"第 {self.current_page + 1} 页 / 共 {total_pages} 页"

        self.prev_button["state"] = tk.NORMAL if self.current_page > 0 else tk.DISABLED
        self.next_button["state"] = tk.NORMAL if end_idx < len(self.all_data) else tk.DISABLED

    def sort_by_date(self):
        """按日期排序"""
        self.sort_order_date = not self.sort_order_date
        self.all_data = self.all_data.sort_values(by="Date", ascending=self.sort_order_date)
        self.update_table()

    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self):
        """下一页"""
        if (self.current_page + 1) * PAGE_SIZE < len(self.all_data):
            self.current_page += 1
            self.update_table()

    def first_page(self):
        """第一页"""
        self.current_page = 0
        self.update_table()

    def last_page(self):
        """最后一页"""
        total_pages = max(1, (len(self.all_data) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.current_page = total_pages - 1
        self.update_table()

    def delete_record(self):
        """删除选中记录"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的记录")
            return

        record_ids = []
        for item in selected_items:
            record_values = self.tree.item(item, "values")
            record_ids.append(record_values[0])

        if not messagebox.askyesno("确认", f"确定要删除 {len(record_ids)} 条记录吗？"):
            return

        id_list = ", ".join(map(str, record_ids))
        delete_query = f"DELETE FROM articles WHERE id IN ({id_list})"
        update_record(delete_query)
        self.query_all_data()

    def delete_all_records(self):
        """删除全部记录"""
        if not messagebox.askyesno("确认", "确定要删除全部记录吗？此操作不可撤销！"):
            return

        delete_query = "DELETE FROM articles"
        update_record(delete_query)
        self.query_all_data()

    def export_to_excel(self):
        """导出到 Excel"""
        if self.all_data.empty:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel 文件", "*.xlsx")])
        if file_path:
            self.all_data.to_excel(file_path, index=False)
            messagebox.showinfo("成功", f"数据已成功导出到 {file_path}")

    def edit_record(self, event):
        """编辑选中记录"""
        selected_item = self.tree.focus()
        if not selected_item:
            return

        record_values = self.tree.item(selected_item, "values")
        edit_win = tk.Toplevel(self.root)
        edit_win.title("编辑记录")
        entry_vars = []
        for i, col in enumerate(self.tree["columns"]):
            tk.Label(edit_win, text=col).grid(row=i, column=0, padx=5, pady=5)
            entry_var = tk.StringVar(value=record_values[i])
            entry_vars.append(entry_var)
            tk.Entry(edit_win, textvariable=entry_var).grid(row=i, column=1, padx=5, pady=5)

        def save_changes():
            updated_values = [entry_vars[i].get() for i in range(len(record_values))]
            update_query = f"""
                UPDATE articles
                SET title='{updated_values[1]}', date='{updated_values[2]}',
                    province='{updated_values[3]}', city='{updated_values[4]}',
                    keywords='{updated_values[5]}', summary='{updated_values[6]}', url='{updated_values[7]}'
                WHERE id={updated_values[0]}
            """
            update_record(update_query)
            edit_win.destroy()
            self.query_all_data()

        tk.Button(edit_win, text="保存修改", command=save_changes).grid(row=len(record_values), column=0, columnspan=2, pady=10)

# 主函数
if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseManagerApp(root)
    root.mainloop()
