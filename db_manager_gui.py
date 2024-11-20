import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd

# 数据库文件路径
db_path = "news_data.db"
PAGE_SIZE = 50  # 每页显示的数据条数

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

        # 筛选查询区
        filter_frame = tk.Frame(root)
        filter_frame.pack(fill=tk.X, pady=5)

        tk.Label(filter_frame, text="筛选条件 (例如: date='2024-11-15')").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar()
        tk.Entry(filter_frame, textvariable=self.filter_var, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(filter_frame, text="应用筛选", command=self.apply_filter).pack(side=tk.LEFT, padx=5)
        tk.Button(filter_frame, text="导出到 Excel", command=self.export_to_excel).pack(side=tk.LEFT, padx=5)

        # 查询结果表格
        self.tree = ttk.Treeview(
            root,
            columns=("ID", "Title", "Date", "Province", "City", "Keywords", "Summary", "URL"),
            show="headings",
            selectmode="extended"  # 支持多选
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        self.tree.bind("<Double-1>", self.edit_record)  # 双击记录进行编辑

        # 分页按钮区
        pagination_frame = tk.Frame(root)
        pagination_frame.pack(fill=tk.X, pady=5)

        self.prev_button = tk.Button(pagination_frame, text="上一页", command=self.prev_page, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.page_label = tk.Label(pagination_frame, text="第 1 页")
        self.page_label.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(pagination_frame, text="下一页", command=self.next_page, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = tk.Button(pagination_frame, text="删除选中记录", command=self.delete_record)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        # 初始化数据
        self.all_data = pd.DataFrame()  # 保存筛选后的全部数据
        self.query_all_data()

    # 查询所有数据
    def query_all_data(self):
        self.all_data = fetch_data("SELECT * FROM articles")
        self.current_page = 0
        self.update_table()

    # 筛选查询
    def apply_filter(self):
        condition = self.filter_var.get().strip()
        query = "SELECT * FROM articles"
        if condition:
            query += f" WHERE {condition}"
        self.all_data = fetch_data(query)
        self.current_page = 0
        self.update_table()

    # 更新表格
    def update_table(self):
        # 清空表格
        for row in self.tree.get_children():
            self.tree.delete(row)

        # 分页显示
        start_idx = self.current_page * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_data = self.all_data.iloc[start_idx:end_idx]

        for _, row in page_data.iterrows():
            self.tree.insert("", tk.END, values=row.tolist())

        # 更新分页按钮状态
        self.prev_button["state"] = tk.NORMAL if self.current_page > 0 else tk.DISABLED
        self.next_button["state"] = tk.NORMAL if end_idx < len(self.all_data) else tk.DISABLED

        # 更新页码标签
        total_pages = max(1, (len(self.all_data) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_label["text"] = f"第 {self.current_page + 1} 页 / 共 {total_pages} 页"

    # 上一页
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    # 下一页
    def next_page(self):
        if (self.current_page + 1) * PAGE_SIZE < len(self.all_data):
            self.current_page += 1
            self.update_table()

    # 删除
    def delete_record(self):
        selected_items = self.tree.selection()  # 获取所有选中的记录
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的记录")
            return

        # 提取所有选中记录的 ID
        record_ids = []
        for item in selected_items:
            record_values = self.tree.item(item, "values")
            record_ids.append(record_values[0])  # 假设 ID 是第一列

        # 确认删除
        if not messagebox.askyesno("确认", f"确定要删除 {len(record_ids)} 条记录吗？"):
            return

        # 构造批量删除的 SQL 语句
        id_list = ", ".join(map(str, record_ids))
        delete_query = f"DELETE FROM articles WHERE id IN ({id_list})"

        try:
            update_record(delete_query)
            messagebox.showinfo("成功", f"已成功删除 {len(record_ids)} 条记录")
            self.query_all_data()  # 刷新数据
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")

    # 导出到 Excel
    def export_to_excel(self):
        if self.all_data.empty:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel 文件", "*.xlsx")])
        if file_path:
            try:
                # 删除 'id' 列，生成不含 'id' 的 DataFrame
                export_data = self.all_data.drop(columns=['id'], errors='ignore')
                export_data.to_excel(file_path, index=False, engine="openpyxl")
                messagebox.showinfo("成功", f"数据已成功导出到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{e}")

    # 编辑记录
    def edit_record(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        record_values = self.tree.item(selected_item, "values")

        def save_changes():
            updated_values = [
                entry_vars[i].get() for i in range(len(record_values))
            ]
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

        # 创建编辑窗口
        edit_win = tk.Toplevel(self.root)
        edit_win.title("编辑记录")
        entry_vars = []
        for i, col in enumerate(self.tree["columns"]):
            tk.Label(edit_win, text=col).grid(row=i, column=0, padx=5, pady=5)
            entry_var = tk.StringVar(value=record_values[i])
            entry_vars.append(entry_var)
            tk.Entry(edit_win, textvariable=entry_var).grid(row=i, column=1, padx=5, pady=5)
        tk.Button(edit_win, text="保存修改", command=save_changes).grid(row=len(record_values), column=0, columnspan=2, pady=10)


# 运行程序
if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseManagerApp(root)
    root.mainloop()
