import json
import os
from datetime import datetime, date
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import sys

DATA_FILE = "homework_data.json"

class Homework:
    def __init__(self, id, title, description, due_date, created_at=None, completed=False):
        self.id = id
        self.title = title
        self.description = description
        self.due_date = due_date
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.completed = completed

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "completed": self.completed
        }

    @staticmethod
    def from_dict(data):
        return Homework(
            data["id"], data["title"], data["description"], data["due_date"],
            data.get("created_at"), data.get("completed", False)
        )

    def days_until_due(self):
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            return (due - today).days
        except:
            return None

    def is_overdue(self):
        days = self.days_until_due()
        return days is not None and days < 0 and not self.completed

    def is_due_soon(self, days=3):
        days_left = self.days_until_due()
        return days_left is not None and 0 <= days_left <= days and not self.completed

class HomeworkManager:
    def __init__(self):
        self.homeworks = []
        self.next_id = 1
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.homeworks = [Homework.from_dict(item) for item in data.get("homeworks", [])]
                    self.next_id = data.get("next_id", 1)
            except:
                self.homeworks = []
                self.next_id = 1

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "homeworks": [hw.to_dict() for hw in self.homeworks],
                "next_id": self.next_id
            }, f, ensure_ascii=False, indent=2)

    def add_homework(self, title, description, due_date):
        homework = Homework(self.next_id, title, description, due_date)
        self.homeworks.append(homework)
        self.next_id += 1
        self.save_data()
        return homework

    def delete_homework(self, id):
        self.homeworks = [hw for hw in self.homeworks if hw.id != id]
        self.save_data()

    def update_homework(self, id, title=None, description=None, due_date=None):
        for hw in self.homeworks:
            if hw.id == id:
                if title is not None:
                    hw.title = title
                if description is not None:
                    hw.description = description
                if due_date is not None:
                    hw.due_date = due_date
                self.save_data()
                return hw
        return None

    def mark_completed(self, id, completed=True):
        for hw in self.homeworks:
            if hw.id == id:
                hw.completed = completed
                self.save_data()
                return hw
        return None

    def get_homework(self, id):
        for hw in self.homeworks:
            if hw.id == id:
                return hw
        return None

    def list_homeworks(self, filter_type="all"):
        if filter_type == "all":
            return self.homeworks
        elif filter_type == "pending":
            return [hw for hw in self.homeworks if not hw.completed]
        elif filter_type == "completed":
            return [hw for hw in self.homeworks if hw.completed]
        elif filter_type == "overdue":
            return [hw for hw in self.homeworks if hw.is_overdue()]
        elif filter_type == "due_soon":
            return [hw for hw in self.homeworks if hw.is_due_soon()]
        return self.homeworks

    def check_reminders(self):
        reminders = []
        for hw in self.homeworks:
            if hw.is_overdue():
                reminders.append(f"【已逾期】{hw.title}")
            elif hw.is_due_soon():
                days = hw.days_until_due()
                if days == 0:
                    reminders.append(f"【今天到期】{hw.title}")
                else:
                    reminders.append(f"【还剩{days}天】{hw.title}")
        return reminders

class ReminderService:
    def __init__(self, manager, callback):
        self.manager = manager
        self.callback = callback
        self.check_interval = 300
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _run(self):
        while self.running:
            reminders = self.manager.check_reminders()
            if reminders and self.running:
                self.callback(reminders)
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

class CalendarDialog(tk.Toplevel):
    def __init__(self, parent, initial_date=None, min_date=None, title="选择日期", allow_past=False):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.min_date = min_date
        self.allow_past = allow_past

        if initial_date is None:
            initial_date = date.today()

        self.withdraw()
        self._create_widgets(initial_date)
        self._center_window()
        self.deiconify()

    def _create_widgets(self, initial_date):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        if self.allow_past:
            self.calendar = Calendar(main_frame, selectmode="day", date_pattern="yyyy-mm-dd",
                                    year=initial_date.year, month=initial_date.month, day=initial_date.day,
                                    showweeknumbers=False, font=("Microsoft YaHei", 10), locale="zh_CN",
                                    mindate=date(1900, 1, 1))
        else:
            mindate = self.min_date if self.min_date else date.today()
            self.calendar = Calendar(main_frame, selectmode="day", date_pattern="yyyy-mm-dd",
                                    year=initial_date.year, month=initial_date.month, day=initial_date.day,
                                    mindate=mindate, showweeknumbers=False, font=("Microsoft YaHei", 10), locale="zh_CN")

        self.calendar.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="取消", command=self.cancel, width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="今天", command=self._select_today, width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="确定", command=self._confirm, width=12).pack(side=tk.LEFT, padx=10)

    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _select_today(self):
        today = date.today()
        self.calendar.selection_set(today)

    def _confirm(self):
        selected = self.calendar.selection_get()
        if selected:
            if not self.allow_past and selected < date.today():
                messagebox.showwarning("提示", "不能选择过去的日期！", parent=self)
                return
            self.result = selected.strftime("%Y-%m-%d")
            self.destroy()
        else:
            messagebox.showwarning("提示", "请选择一个日期！", parent=self)

    def cancel(self):
        self.destroy()

class AddHomeworkDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("添加作业")
        self.geometry("450x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self._create_widgets()
        self._center_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="作业标题:", font=("", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.title_entry = ttk.Entry(main_frame, width=40, font=("", 11))
        self.title_entry.grid(row=0, column=1, pady=8, padx=10)

        ttk.Label(main_frame, text="作业描述:", font=("", 11, "bold")).grid(row=1, column=0, sticky=tk.NW, pady=8)
        self.desc_text = tk.Text(main_frame, width=40, height=6, font=("", 10))
        self.desc_text.grid(row=1, column=1, pady=8, padx=10)

        ttk.Label(main_frame, text="截止日期:", font=("", 11, "bold")).grid(row=2, column=0, sticky=tk.W, pady=8)

        date_frame = ttk.Frame(main_frame)
        date_frame.grid(row=2, column=1, pady=8, padx=10, sticky=tk.W)

        self.date_entry = ttk.Entry(date_frame, width=20, font=("", 11))
        self.date_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(date_frame, text="📅 选择日期", command=self._pick_date, width=12).pack(side=tk.LEFT)

        ttk.Label(main_frame, text="(不能选择过去的日期)", font=("", 9)).grid(row=3, column=1, sticky=tk.W, padx=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="取消", command=self.cancel, width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="确定添加", command=self.confirm, width=12).pack(side=tk.LEFT, padx=10)

    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _pick_date(self):
        dialog = CalendarDialog(self, min_date=date.today(), title="选择截止日期")
        self.wait_window(dialog)
        if dialog.result:
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, dialog.result)

    def confirm(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("提示", "请输入作业标题！", parent=self)
            return

        description = self.desc_text.get("1.0", tk.END).strip()
        due_date = self.date_entry.get().strip()

        if not due_date:
            messagebox.showwarning("提示", "请选择截止日期！", parent=self)
            return

        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("错误", "日期格式错误！", parent=self)
            return

        self.result = (title, description, due_date)
        self.destroy()

    def cancel(self):
        self.destroy()

class EditHomeworkDialog(tk.Toplevel):
    def __init__(self, parent, homework):
        super().__init__(parent)
        self.title("编辑作业")
        self.geometry("450x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.homework = homework
        self.result = None
        self._create_widgets()
        self._center_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="作业标题:", font=("", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.title_entry = ttk.Entry(main_frame, width=40, font=("", 11))
        self.title_entry.insert(0, self.homework.title)
        self.title_entry.grid(row=0, column=1, pady=8, padx=10)

        ttk.Label(main_frame, text="作业描述:", font=("", 11, "bold")).grid(row=1, column=0, sticky=tk.NW, pady=8)
        self.desc_text = tk.Text(main_frame, width=40, height=6, font=("", 10))
        self.desc_text.insert("1.0", self.homework.description)
        self.desc_text.grid(row=1, column=1, pady=8, padx=10)

        ttk.Label(main_frame, text="截止日期:", font=("", 11, "bold")).grid(row=2, column=0, sticky=tk.W, pady=8)

        date_frame = ttk.Frame(main_frame)
        date_frame.grid(row=2, column=1, pady=8, padx=10, sticky=tk.W)

        self.date_entry = ttk.Entry(date_frame, width=20, font=("", 11))
        self.date_entry.insert(0, self.homework.due_date)
        self.date_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(date_frame, text="📅 选择日期", command=self._pick_date, width=12).pack(side=tk.LEFT)

        ttk.Label(main_frame, text="(日历可选择任意日期)", font=("", 9)).grid(row=3, column=1, sticky=tk.W, padx=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="取消", command=self.cancel, width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="保存修改", command=self.confirm, width=12).pack(side=tk.LEFT, padx=10)

    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _pick_date(self):
        initial = None
        try:
            initial = datetime.strptime(self.homework.due_date, "%Y-%m-%d").date()
        except:
            pass

        dialog = CalendarDialog(self, initial_date=initial, min_date=date.today(), title="选择截止日期", allow_past=True)
        self.wait_window(dialog)
        if dialog.result:
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, dialog.result)

    def confirm(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("提示", "请输入作业标题！", parent=self)
            return

        description = self.desc_text.get("1.0", tk.END).strip()
        due_date = self.date_entry.get().strip()

        if not due_date:
            messagebox.showwarning("提示", "请选择截止日期！", parent=self)
            return

        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("错误", "日期格式错误！", parent=self)
            return

        self.result = (title, description, due_date)
        self.destroy()

    def cancel(self):
        self.destroy()

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tooltip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", foreground="#000000",
                        relief=tk.SOLID, borderwidth=1, font=("Microsoft YaHei", 9))
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class HomeworkApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.manager = HomeworkManager()
        self.reminder_service = ReminderService(self.manager, self.show_reminder)

        self.title("作业提醒系统 v0.2")
        self.geometry("900x600")
        self.minsize(800, 500)

        self._create_widgets()
        self._center_window()
        self.refresh_list()

        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

        self.reminder_service.start()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Escape>", lambda e: self.tree.selection_remove(self.tree.selection()))
        self.bind("<space>", lambda e: self.tree.selection_remove(self.tree.selection()))

    def _create_widgets(self):
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=(15, 10))

        ttk.Label(title_frame, text="作业提醒系统", font=("Microsoft YaHei", 22, "bold")).pack(side=tk.LEFT, padx=20)

        self.status_label = ttk.Label(title_frame, text="", font=("Microsoft YaHei", 10), foreground="green")
        self.status_label.pack(side=tk.RIGHT, padx=20)

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="➕ 添加作业", command=self.add_homework, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="✏️ 编辑", command=self.edit_homework, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ 删除", command=self.delete_homework, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="✓ 标记完成", command=self.toggle_complete, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔔 检查提醒", command=self.check_reminders, width=15).pack(side=tk.LEFT, padx=5)

        filter_frame = ttk.LabelFrame(main_frame, text="筛选条件", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        self.filter_var = tk.StringVar(value="pending")
        filters = [
            ("全部", "all"),
            ("待完成", "pending"),
            ("已完成", "completed"),
            ("已逾期", "overdue"),
            ("临期(3天内)", "due_soon")
        ]

        for text, value in filters:
            ttk.Radiobutton(filter_frame, text=text, variable=self.filter_var,
                          value=value, command=self.refresh_list).pack(side=tk.LEFT, padx=10)

        sort_frame = ttk.Frame(filter_frame)
        sort_frame.pack(side=tk.RIGHT, padx=10)

        self.sort_order_var = tk.BooleanVar(value=True)
        self.sort_order_label = ttk.Label(sort_frame, text="🔽 截止日期", font=("", 9))
        self.sort_order_label.pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(sort_frame, text="倒序", variable=self.sort_order_var,
                        command=self._toggle_sort_order).pack(side=tk.LEFT)

        list_frame = ttk.LabelFrame(main_frame, text="作业列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("title", "description", "due_date", "status", "days_left")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", selectmode="extended")

        style = ttk.Style()
        style.configure("Treeview", rowheight=30)

        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("title", anchor="w", width=200)
        self.tree.column("description", anchor="w", width=250)
        self.tree.column("due_date", anchor="center", width=100)
        self.tree.column("status", anchor="center", width=80)
        self.tree.column("days_left", anchor="center", width=100)

        self.tree.heading("title", text="标题")
        self.tree.heading("description", text="描述")
        self.tree.heading("due_date", text="截止日期")
        self.tree.heading("status", text="状态")
        self.tree.heading("days_left", text="剩余天数")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("overdue", foreground="red", font=("", 10, "bold"))
        self.tree.tag_configure("due_soon", foreground="orange", font=("", 10, "bold"))
        self.tree.tag_configure("completed", foreground="gray")
        self.tree.tag_configure("normal", foreground="black")

        self.tree.bind("<Double-Button-1>", lambda e: self.edit_homework())
        self.tree.bind("<Return>", lambda e: self.edit_homework())
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tooltip_label = None

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="✏️ 编辑", command=self.edit_homework)
        self.context_menu.add_command(label="✓ 标记完成/未完成", command=self.toggle_complete)
        self.context_menu.add_command(label="🗑️ 删除", command=self.delete_homework)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-1>", self._on_tree_click)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(info_frame, text="� 说明", command=self._show_help, width=10).pack(side=tk.LEFT, padx=10)

    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _show_help(self):
        help_text = """作业提醒系统 v0.2 使用说明

【基本操作】
• 单击选中一项作业
• Ctrl + 单击 多选/取消选中
• Shift + 单击 范围选择
• 双击或回车 编辑作业
• 右键点击 显示操作菜单
• 空格键或Escape 取消选择
• 点击列表空白处 取消选择

【筛选功能】
• 全部：显示所有作业
• 待完成：显示未完成的作业
• 已完成：显示已完成的作业
• 已逾期：显示已过截止日期的作业
• 临期(3天内)：显示即将到期的作业

【排序功能】
• 按截止日期排序
• 勾选"倒序"可切换升序/降序

【批量操作】
• 选择多个作业后，可批量删除或标记完成状态

【其他】
• 添加作业时不能选择过去的日期
• 编辑作业时可以修改为任意日期
• 鼠标悬停在描述上可查看完整内容"""
        messagebox.showinfo("使用说明", help_text)

    def _toggle_sort_order(self):
        reverse = self.sort_order_var.get()
        self.sort_order_label.config(text="🔼 截止日期" if reverse else "🔽 截止日期")
        self.refresh_list()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        homeworks = self.manager.list_homeworks(self.filter_var.get())
        homeworks.sort(key=lambda hw: hw.due_date, reverse=self.sort_order_var.get())

        for hw in homeworks:
            days = hw.days_until_due()
            if hw.completed:
                status = "已完成"
                tags = ("completed",)
            elif hw.is_overdue():
                status = "已逾期"
                tags = ("overdue",)
            elif hw.is_due_soon():
                status = "临期"
                tags = ("due_soon",)
            else:
                status = "待完成"
                tags = ("normal",)

            if days is not None:
                if days < 0:
                    days_text = f"已逾期{-days}天"
                elif days == 0:
                    days_text = "今天到期"
                else:
                    days_text = f"{days}天"
            else:
                days_text = "-"

            description = hw.description[:30] + "..." if len(hw.description) > 30 else hw.description

            self.tree.insert("", "end", iid=hw.id, values=(
                hw.title, description, hw.due_date, status, days_text
            ), tags=tags)

        self.update_status()

    def update_status(self):
        total = len(self.manager.homeworks)
        pending = len([hw for hw in self.manager.homeworks if not hw.completed])
        overdue = len([hw for hw in self.manager.homeworks if hw.is_overdue()])
        due_soon = len([hw for hw in self.manager.homeworks if hw.is_due_soon()])

        status_text = f"总计: {total} | 待完成: {pending}"
        if overdue > 0:
            status_text += f" | 已逾期: {overdue}"
        if due_soon > 0:
            status_text += f" | 临期: {due_soon}"

        self.status_label.config(text=status_text)

    def get_selected_ids(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择作业！")
            return []
        return [int(item) for item in selection]

    def get_selected_id(self):
        ids = self.get_selected_ids()
        return ids[0] if ids else None

    def add_homework(self):
        dialog = AddHomeworkDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            title, description, due_date = dialog.result
            hw = self.manager.add_homework(title, description, due_date)
            self.refresh_list()
            messagebox.showinfo("成功", f"作业添加成功！\n标题: {hw.title}")

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            selection_count = len(self.tree.selection())
            self.context_menu.entryconfigure(0, state="normal" if selection_count == 1 else "disabled")
            self.context_menu.post(event.x_root, event.y_root)

    def _on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            self.tree.selection_remove(self.tree.selection())

    def _on_tree_motion(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label:
            self.tooltip_label.destroy()
            self.tooltip_label = None

        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column = self.tree.identify_column(event.x)
        if column != "#2":
            return

        hw = self.manager.get_homework(int(item_id))
        if not hw or not hw.description:
            return

        if len(hw.description) <= 30:
            return

        x = event.x_root + 15
        y = event.y_root + 15
        self.tooltip_label = tk.Toplevel(self)
        self.tooltip_label.wm_overrideredirect(True)
        self.tooltip_label.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_label, text=hw.description, justify=tk.LEFT,
                        background="#ffffe0", foreground="#000000",
                        relief=tk.SOLID, borderwidth=1, font=("Microsoft YaHei", 9),
                        wraplength=400)
        label.pack()

    def edit_homework(self):
        hw_id = self.get_selected_id()
        if hw_id is None:
            return

        homework = self.manager.get_homework(hw_id)
        if homework:
            dialog = EditHomeworkDialog(self, homework)
            self.wait_window(dialog)
            if dialog.result:
                title, description, due_date = dialog.result
                self.manager.update_homework(hw_id, title, description, due_date)
                self.refresh_list()
                messagebox.showinfo("成功", "作业已更新！")

    def delete_homework(self):
        hw_ids = self.get_selected_ids()
        if not hw_ids:
            return

        if len(hw_ids) == 1:
            homework = self.manager.get_homework(hw_ids[0])
            if homework:
                if messagebox.askyesno("确认删除", f"确定要删除作业「{homework.title}」吗？"):
                    self.manager.delete_homework(hw_ids[0])
                    self.refresh_list()
                    messagebox.showinfo("成功", "作业已删除！")
        else:
            if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(hw_ids)} 项作业吗？"):
                for hw_id in hw_ids:
                    self.manager.delete_homework(hw_id)
                self.refresh_list()
                messagebox.showinfo("成功", f"已删除 {len(hw_ids)} 项作业！")

    def toggle_complete(self):
        hw_ids = self.get_selected_ids()
        if not hw_ids:
            return

        completed_count = 0
        for hw_id in hw_ids:
            homework = self.manager.get_homework(hw_id)
            if homework:
                new_status = not homework.completed
                self.manager.mark_completed(hw_id, new_status)
                completed_count += 1

        self.refresh_list()
        messagebox.showinfo("成功", f"已更新 {completed_count} 项作业！")

    def check_reminders(self):
        reminders = self.manager.check_reminders()
        if reminders:
            msg = "\n".join(reminders)
            messagebox.showwarning("临期提醒", f"以下作业需要关注：\n\n{msg}")
        else:
            messagebox.showinfo("检查提醒", "目前没有需要提醒的作业！")

    def show_reminder(self, reminders):
        self.after(0, lambda: self._show_reminder_dialog(reminders))

    def _show_reminder_dialog(self, reminders):
        msg = "\n".join(reminders)
        overdue_count = len([r for r in reminders if "已逾期" in r])
        due_soon_count = len([r for r in reminders if "还剩" in r or "今天到期" in r])

        if overdue_count > 0 and due_soon_count > 0:
            result = messagebox.askyesno("🔔 临期提醒", f"以下作业需要关注：\n\n{msg}\n\n逾期{overdue_count}项，临期{due_soon_count}项\n点击【是】查看逾期作业，【否】查看临期作业？")
            if result:
                self.filter_var.set("overdue")
            else:
                self.filter_var.set("due_soon")
        elif overdue_count > 0:
            result = messagebox.askyesno("🔔 逾期提醒", f"以下作业已逾期：\n\n{msg}\n\n是否查看作业列表？")
            if result:
                self.filter_var.set("overdue")
        elif due_soon_count > 0:
            result = messagebox.askyesno("🔔 临期提醒", f"以下作业即将到期：\n\n{msg}\n\n是否查看作业列表？")
            if result:
                self.filter_var.set("due_soon")
        else:
            return

        if result:
            self.refresh_list()

    def on_closing(self):
        self.reminder_service.running = False
        self.destroy()

if __name__ == "__main__":
    app = HomeworkApp()
    app.mainloop()