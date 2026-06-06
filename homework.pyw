import json
import os
from datetime import datetime, date
import threading
import time
import customtkinter as ctk
from tkinter import messagebox, Menu
from CTkMenuBar import CTkMenuBar, CustomDropdownMenu
from tkcalendar import Calendar
import sys

DATA_FILE = "homework_data.json"

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

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
        except ValueError:
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
            except (json.JSONDecodeError, Exception):
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
            if self.running:
                reminders = self.manager.check_reminders()
                if reminders and self.running:
                    self.callback(reminders)
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

class CalendarDialog(ctk.CTkToplevel):
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
        main_frame = ctk.CTkFrame(self, fg_color="#ffffff")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

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

        self.calendar.pack(fill="both", expand=True, pady=(0, 10))

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="取消", command=self.cancel, width=100, height=32, fg_color="#D0D0D0", text_color="#333333").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="今天", command=self._select_today, width=100, height=32, fg_color="#4A90D9", text_color="white").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="确定", command=self._confirm, width=100, height=32).pack(side="left", padx=10)

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

class AddHomeworkDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("添加作业")
        self.geometry("500x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self._create_widgets()
        self._center_window()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="#ffffff")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(main_frame, text="作业标题:", font=("Microsoft YaHei", 14, "bold"), text_color="#2c3e50")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        self.title_entry = ctk.CTkEntry(main_frame, width=350, font=("Microsoft YaHei", 12), placeholder_text="请输入作业标题")
        self.title_entry.grid(row=0, column=1, pady=(0, 8), padx=(10, 0))

        desc_label = ctk.CTkLabel(main_frame, text="作业描述:", font=("Microsoft YaHei", 14, "bold"), text_color="#2c3e50")
        desc_label.grid(row=1, column=0, sticky="nw", pady=(0, 8))
        
        self.desc_text = ctk.CTkTextbox(main_frame, width=350, height=120, font=("Microsoft YaHei", 11), border_width=1, border_color="#cccccc")
        self.desc_text.grid(row=1, column=1, pady=(0, 8), padx=(10, 0))

        date_label = ctk.CTkLabel(main_frame, text="截止日期:", font=("Microsoft YaHei", 14, "bold"), text_color="#2c3e50")
        date_label.grid(row=2, column=0, sticky="w", pady=(0, 8))

        date_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        date_frame.grid(row=2, column=1, pady=(0, 8), padx=(10, 0), sticky="w")

        self.date_entry = ctk.CTkEntry(date_frame, width=180, font=("Microsoft YaHei", 12), placeholder_text="YYYY-MM-DD")
        self.date_entry.pack(side="left", padx=(0, 10))
        ctk.CTkButton(date_frame, text="📅 选择", command=self._pick_date, width=80, height=32).pack(side="left")

        hint_label = ctk.CTkLabel(main_frame, text="(不能选择过去的日期)", font=("Microsoft YaHei", 10), text_color="#95A5A6")
        hint_label.grid(row=3, column=1, sticky="w", padx=(10, 0))

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))

        ctk.CTkButton(btn_frame, text="取消", command=self.cancel, width=120, height=36, fg_color="#D0D0D0", text_color="#333333").pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="确定添加", command=self.confirm, width=120, height=36, fg_color="#4A90D9", hover_color="#3A7BC8").pack(side="left", padx=15)

    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _pick_date(self):
        dialog = CalendarDialog(self, min_date=date.today(), title="选择截止日期")
        self.wait_window(dialog)
        if dialog.result:
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, dialog.result)

    def confirm(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("提示", "请输入作业标题！", parent=self)
            return

        description = self.desc_text.get("0.0", "end").strip()
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

class EditHomeworkDialog(ctk.CTkToplevel):
    def __init__(self, parent, homework):
        super().__init__(parent)
        self.title("编辑作业")
        self.geometry("500x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.homework = homework
        self.result = None
        self._create_widgets()
        self._center_window()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="#ffffff")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(main_frame, text="作业标题:", font=("Microsoft YaHei", 14, "bold"), text_color="#2c3e50")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        self.title_entry = ctk.CTkEntry(main_frame, width=350, font=("Microsoft YaHei", 12))
        self.title_entry.insert(0, self.homework.title)
        self.title_entry.grid(row=0, column=1, pady=(0, 8), padx=(10, 0))

        desc_label = ctk.CTkLabel(main_frame, text="作业描述:", font=("Microsoft YaHei", 14, "bold"), text_color="#2c3e50")
        desc_label.grid(row=1, column=0, sticky="nw", pady=(0, 8))
        
        self.desc_text = ctk.CTkTextbox(main_frame, width=350, height=120, font=("Microsoft YaHei", 11), border_width=1, border_color="#cccccc")
        self.desc_text.insert("0.0", self.homework.description)
        self.desc_text.grid(row=1, column=1, pady=(0, 8), padx=(10, 0))

        date_label = ctk.CTkLabel(main_frame, text="截止日期:", font=("Microsoft YaHei", 14, "bold"), text_color="#2c3e50")
        date_label.grid(row=2, column=0, sticky="w", pady=(0, 8))

        date_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        date_frame.grid(row=2, column=1, pady=(0, 8), padx=(10, 0), sticky="w")

        self.date_entry = ctk.CTkEntry(date_frame, width=180, font=("Microsoft YaHei", 12))
        self.date_entry.insert(0, self.homework.due_date)
        self.date_entry.pack(side="left", padx=(0, 10))
        ctk.CTkButton(date_frame, text="📅 选择", command=self._pick_date, width=80, height=32).pack(side="left")

        hint_label = ctk.CTkLabel(main_frame, text="(日历可选择任意日期)", font=("Microsoft YaHei", 10), text_color="#95A5A6")
        hint_label.grid(row=3, column=1, sticky="w", padx=(10, 0))

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))

        ctk.CTkButton(btn_frame, text="取消", command=self.cancel, width=120, height=36, fg_color="#D0D0D0", text_color="#333333").pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="保存修改", command=self.confirm, width=120, height=36, fg_color="#4A90D9", hover_color="#3A7BC8").pack(side="left", padx=15)

    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _pick_date(self):
        initial = None
        try:
            initial = datetime.strptime(self.homework.due_date, "%Y-%m-%d").date()
        except ValueError:
            pass

        dialog = CalendarDialog(self, initial_date=initial, min_date=date.today(), title="选择截止日期", allow_past=True)
        self.wait_window(dialog)
        if dialog.result:
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, dialog.result)

    def confirm(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("提示", "请输入作业标题！", parent=self)
            return

        description = self.desc_text.get("0.0", "end").strip()
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
        self.tooltip = ctk.CTkToplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(self.tooltip, text=self.text, justify="left",
                           text_color="#000000", fg_color="#ffffe0")
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class HomeworkApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.manager = HomeworkManager()
        self.reminder_service = ReminderService(self.manager, self.show_reminder)

        self.title("作业提醒系统 v0.3")
        self.geometry("950x650")
        self.minsize(850, 550)

        self.homework_items = {}
        self.selected_ids = []

        self._create_widgets()
        self._center_window()
        
        self.fade_in()
        
        self.refresh_list()

        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

        self.reminder_service.start()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Escape>", lambda e: self._clear_selection())
        self.bind("<space>", lambda e: self._clear_selection())

    def _create_widgets(self):
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", pady=(20, 15))

        # 添加标题图标
        icon_label = ctk.CTkLabel(title_frame, text="📋", font=("Arial", 30), text_color="#4A90D9")
        icon_label.pack(side="left", padx=(25, 10))

        ctk.CTkLabel(title_frame, text="作业提醒系统", font=("Microsoft YaHei", 28, "bold"), 
                    text_color="#4A90D9").pack(side="left")

        self.status_label = ctk.CTkLabel(title_frame, text="", font=("Microsoft YaHei", 11), text_color="#27AE60")
        self.status_label.pack(side="right", padx=25)

        main_frame = ctk.CTkFrame(self, fg_color="#F5F7FA")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        toolbar = ctk.CTkFrame(main_frame, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(toolbar, text="➕ 添加作业", command=self.add_homework, width=130, height=36, font=("Microsoft YaHei", 12), fg_color="#4A90D9", hover_color="#3A7BC8").pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="✏️ 编辑", command=self.edit_homework, width=130, height=36, font=("Microsoft YaHei", 12), fg_color="#5B8DEF", hover_color="#4A7ED9").pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="🗑️ 删除", command=self.delete_homework, width=130, height=36, fg_color="#E74C3C", hover_color="#C0392B", font=("Microsoft YaHei", 12)).pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="✓ 标记完成", command=self.toggle_complete, width=130, height=36, fg_color="#27AE60", hover_color="#229954", font=("Microsoft YaHei", 12)).pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="🔔 检查提醒", command=self.check_reminders, width=130, height=36, font=("Microsoft YaHei", 12), fg_color="#5B8DEF", hover_color="#4A7ED9").pack(side="left", padx=8)
        
        ctk.CTkButton(toolbar, text="?", command=self._show_help, width=40, height=36, 
                     font=("Microsoft YaHei", 16, "bold"), fg_color="#4A90D9", hover_color="#3A7BC8").pack(side="right", padx=10)

        filter_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF", border_color="#E1E8ED", border_width=1, corner_radius=12)
        filter_frame.pack(fill="x", pady=(0, 15))

        self.filter_var = ctk.StringVar(value="pending")
        filters = [
            ("全部", "all"),
            ("待完成", "pending"),
            ("已完成", "completed"),
            ("已逾期", "overdue"),
            ("临期(3天内)", "due_soon")
        ]

        filter_content = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_content.pack(fill="x", padx=15, pady=10)

        for text, value in filters:
            ctk.CTkRadioButton(filter_content, text=text, variable=self.filter_var,
                              value=value, command=self.refresh_list,
                              radiobutton_height=20, radiobutton_width=20).pack(side="left", padx=12)

        sort_frame = ctk.CTkFrame(filter_content, fg_color="transparent")
        sort_frame.pack(side="right", padx=15)

        self.sort_order_var = ctk.BooleanVar(value=True)
        ctk.CTkLabel(sort_frame, text="截止日期", font=("Microsoft YaHei", 10), text_color="#666666").pack(side="left", padx=8)
        ctk.CTkCheckBox(sort_frame, text="倒序", variable=self.sort_order_var,
                       command=self._toggle_sort_order, checkbox_height=20, checkbox_width=36).pack(side="left")

        list_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF", border_color="#E1E8ED", border_width=1, corner_radius=12)
        list_frame.pack(fill="both", expand=True)

        columns = ("title", "description", "due_date", "status", "days_left")
        self.tree = ctk.CTkScrollableFrame(list_frame, fg_color="#FFFFFF", scrollbar_fg_color="#F0F0F0", scrollbar_button_color="#D0D0D0")
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.columns = columns
        self.header_labels = {}
        
        header_frame = ctk.CTkFrame(self.tree, fg_color="#4A90D9", corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 8))
        header_frame.pack_propagate(False)
        header_frame.configure(height=32)
        
        col_widths = {"title": 150, "description": 350, "due_date": 120, "status": 90, "days_left": 110}
        col_anchors = {"title": "w", "description": "w", "due_date": "w", "status": "w", "days_left": "w"}
        col_texts = {"title": "标题", "description": "描述", "due_date": "截止日期", "status": "状态", "days_left": "剩余天数"}
        
        current_x = 2
        for col in columns:
            width = col_widths.get(col, 100)
            anchor = col_anchors.get(col, "w")
            text = col_texts.get(col, col)
            
            label = ctk.CTkLabel(header_frame, text=text, font=("Microsoft YaHei", 11, "bold"),
                                text_color="white", height=32, width=width, corner_radius=0, anchor=anchor)
            label.place(x=current_x, y=0)
            self.header_labels[col] = label
            current_x += width + 2

        self.tree.bind("<Double-Button-1>", lambda e: self.edit_homework())
        self.tree.bind("<Return>", lambda e: self.edit_homework())
        self.bind("<Return>", lambda e: self.edit_homework())

        self.context_menu = Menu(self, tearoff=0, bg="#ffffff", borderwidth=1, relief="solid")
        self.context_menu.add_command(label="✏️ 编辑", command=self.edit_homework)
        self.context_menu.add_command(label="✓ 标记完成/未完成", command=self.toggle_complete)
        self.context_menu.add_command(label="🗑️ 删除", command=self.delete_homework)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-1>", self._on_tree_click)

    def _center_window(self):
        self.update_idletasks()
        x = 350  # 距离左边100像素
        y = 100  # 距离顶部100像素
        self.geometry(f"+{x}+{y}")

    def _show_help(self):
        help_text = """作业提醒系统 v0.3 使用说明

【基本操作】
• 单击选中一项作业
• Ctrl + 单击 多选/取消选中
• Shift + 单击 范围选择
• 双击或回车 编辑作业
• 空格键或Escape 取消选择

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
• 点击描述区域展开/收起完整内容"""
        messagebox.showinfo("使用说明", help_text)

    def _show_about(self):
        about_text = """作业提醒系统 v0.3

一个简洁高效的作业管理工具

功能特点：
• 添加、编辑、删除作业
• 多种筛选和排序方式
• 到期提醒功能
• 直观的用户界面

技术栈：
• Python + CustomTkinter
• 现代扁平化设计

© 2026 作业提醒系统"""
        messagebox.showinfo("关于", about_text)

    def _toggle_sort_order(self):
        self.refresh_list()

    def fade_in(self, alpha=0.0):
        alpha += 0.1
        if alpha <= 1.0:
            self.attributes('-alpha', alpha)
            self.after(30, lambda: self.fade_in(alpha))
        else:
            self.attributes('-alpha', 1.0)

    def refresh_list(self):
        self._do_refresh()

    def _do_refresh(self):
        for item_id in list(self.homework_items.keys()):
            if item_id in self.homework_items:
                self.homework_items[item_id].destroy()
        self.homework_items.clear()

        homeworks = self.manager.list_homeworks(self.filter_var.get())
        homeworks.sort(key=lambda hw: hw.due_date, reverse=self.sort_order_var.get())

        for hw in homeworks:
            days = hw.days_until_due()
            if hw.completed:
                status = "已完成"
                text_color = "#95A5A6"
            elif hw.is_overdue():
                status = "已逾期"
                text_color = "#E74C3C"
            elif hw.is_due_soon():
                status = "临期"
                text_color = "#F39C12"
            else:
                status = "待完成"
                text_color = "#333333"

            if days is not None:
                if days < 0:
                    days_text = f"已逾期{-days}天"
                elif days == 0:
                    days_text = "今天到期"
                else:
                    days_text = f"{days}天"
            else:
                days_text = "-"

            # 处理描述显示
            display_description = hw.description[:50] + "..." if len(hw.description) > 50 else hw.description
            
            # 创建主项框架
            item_frame = ctk.CTkFrame(self.tree, fg_color="#FFFFFF", border_color="#E8E8E8", border_width=1)
            item_frame.pack(fill="x", pady=2)
            
            # 创建内容框架
            content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            content_frame.pack(fill="x", pady=2, padx=2)
            content_frame.pack_propagate(False)
            content_frame.configure(height=35)
            
            values = {
                "title": hw.title,
                "description": display_description,
                "due_date": hw.due_date,
                "status": status,
                "days_left": days_text
            }
            
            col_widths = {"title": 150, "description": 350, "due_date": 120, "status": 90, "days_left": 110}
            
            # 存储描述标签的引用
            description_label = None
            
            # 初始化当前x坐标
            current_x = 2
            
            # 遍历所有列
            for col in self.columns:
                width = col_widths.get(col, 100)
                if col == "status":
                    color = text_color
                elif col == "days_left" and days is not None:
                    if days < 0:
                        color = "#E74C3C"
                    elif days == 0:
                        color = "#E74C3C"
                    elif days <= 3:
                        color = "#F39C12"
                    else:
                        color = "#333333"
                else:
                    color = "#333333"
                
                # 处理描述列
                if col == "description" and len(hw.description) > 30:
                    # 创建包含描述和按钮的框架
                    desc_frame = ctk.CTkFrame(content_frame, fg_color="transparent", width=width, height=30)
                    desc_frame.place(x=current_x, y=2)
                    
                    # 创建包含描述和按钮的水平框架
                    desc_content_frame = ctk.CTkFrame(desc_frame, fg_color="transparent")
                    desc_content_frame.pack(fill="x", expand=True, padx=5, pady=2)
                    
                    # 创建描述标签
                    description_label = ctk.CTkLabel(desc_content_frame, text=display_description, 
                                                  font=("Microsoft YaHei", 10),
                                                  text_color=color, height=26, 
                                                  anchor="w")
                    description_label.pack(side="left", fill="x", expand=True, padx=(0, 2))
                    
                    # 创建展开/收起按钮
                    toggle_button = ctk.CTkButton(desc_content_frame, text="▼", width=20, height=20, 
                                                 fg_color="transparent", hover_color="#e0e0e0",
                                                 text_color="#666666", font=("Arial", 8))
                    # 设置按钮命令
                    toggle_button.configure(command=lambda frame=item_frame, desc=hw.description, btn=toggle_button, desc_label=description_label: 
                                           self._toggle_description(frame, desc, btn, desc_label))
                    toggle_button.pack(side="left", padx=2)
                    
                    # 存储按钮引用
                    item_frame.toggle_button = toggle_button
                    item_frame.description_label = description_label
                else:
                    # 创建普通列标签
                    label = ctk.CTkLabel(content_frame, text=values[col], font=("Microsoft YaHei", 10),
                                        text_color=color, height=30, width=width, anchor="w")
                    label.place(x=current_x, y=2)
                    
                    # 保存描述标签的引用（如果是描述列但不需要展开）
                    if col == "description":
                        description_label = label
                
                # 更新当前x坐标
                current_x += width + 2
            
            # 绑定点击事件
            item_frame.bind("<Button-1>", lambda e, hw_id=hw.id: self._on_item_click(e, hw_id))
            item_frame.bind("<Double-Button-1>", lambda e, hw_id=hw.id: self._on_item_double_click(e, hw_id))
            
            # 绑定子元素的点击事件
            # 首先绑定 content_frame 的直接子元素
            for child in content_frame.winfo_children():
                child.bind("<Button-1>", lambda e, hw_id=hw.id: self._on_item_click(e, hw_id))
                child.bind("<Double-Button-1>", lambda e, hw_id=hw.id: self._on_item_double_click(e, hw_id))
                
                # 检查是否是描述框架，遍历其内部子元素
                if isinstance(child, ctk.CTkFrame) and hasattr(child, 'winfo_children'):
                    for desc_child in child.winfo_children():
                        # 只有按钮不绑定选择事件
                        if not isinstance(desc_child, ctk.CTkButton):
                            desc_child.bind("<Button-1>", lambda e, hw_id=hw.id: self._on_item_click(e, hw_id))
                        desc_child.bind("<Double-Button-1>", lambda e, hw_id=hw.id: self._on_item_double_click(e, hw_id))
                        
                        # 检查是否有更深层的子元素
                        if isinstance(desc_child, ctk.CTkFrame) and hasattr(desc_child, 'winfo_children'):
                            for deep_child in desc_child.winfo_children():
                                # 只有按钮不绑定选择事件
                                if not isinstance(deep_child, ctk.CTkButton):
                                    deep_child.bind("<Button-1>", lambda e, hw_id=hw.id: self._on_item_click(e, hw_id))
                                deep_child.bind("<Double-Button-1>", lambda e, hw_id=hw.id: self._on_item_double_click(e, hw_id))
            
            self.homework_items[hw.id] = item_frame

        self.update_status()
        # 刷新后更新选中状态
        self._update_selection()

    def _on_item_click(self, event, hw_id):
        # 检测Ctrl键
        is_ctrl = event.state & 0x4 or event.state & 0x100
        # 检测Shift键
        is_shift = event.state & 0x1 or event.state & 0x200
        
        if is_ctrl:  # Ctrl+单击
            if hw_id in self.selected_ids:
                self.selected_ids.remove(hw_id)
            else:
                self.selected_ids.append(hw_id)
        elif is_shift:  # Shift+单击
            if self.selected_ids:
                # 获取当前作业在列表中的位置
                homeworks = self.manager.list_homeworks(self.filter_var.get())
                homeworks.sort(key=lambda hw: hw.due_date, reverse=self.sort_order_var.get())
                
                current_index = -1
                last_selected_index = -1
                
                for i, hw in enumerate(homeworks):
                    if hw.id == hw_id:
                        current_index = i
                    if hw.id == self.selected_ids[-1]:
                        last_selected_index = i
                
                if current_index != -1 and last_selected_index != -1:
                    # 选择范围内的所有作业
                    start = min(current_index, last_selected_index)
                    end = max(current_index, last_selected_index)
                    
                    self.selected_ids = [homeworks[i].id for i in range(start, end + 1)]
        else:  # 普通单击
            self.selected_ids = [hw_id]
        self._update_selection()
        # 停止事件传播，防止触发tree的点击事件
        return "break"

    def _on_item_double_click(self, event, hw_id):
        self.selected_ids = [hw_id]
        self._update_selection()
        self.edit_homework()

    def _update_selection(self):
        for hw_id, frame in self.homework_items.items():
            if hw_id in self.selected_ids:
                frame.configure(fg_color="#E8F4FD", border_color="#4A90D9")
            else:
                frame.configure(fg_color="#FFFFFF", border_color="#E8E8E8")

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

        self.status_label.configure(text=status_text)

    def get_selected_ids(self):
        if not hasattr(self, 'selected_ids'):
            self.selected_ids = []
        return self.selected_ids

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
        # 检查点击位置是否在作业项上
        clicked_hw_id = None
        click_x = event.x_root
        click_y = event.y_root
        
        for hw_id, frame in self.homework_items.items():
            if frame.winfo_containing(click_x, click_y):
                clicked_hw_id = hw_id
                break
        
        if clicked_hw_id:
            if clicked_hw_id not in self.get_selected_ids():
                self.selected_ids = [clicked_hw_id]
                self._update_selection()
            self.context_menu.post(click_x, click_y)

    def _on_tree_click(self, event):
        # Clear selection when clicking on empty area
        # This will be overridden by item click handlers if click is on an item
        self.selected_ids = []
        self._update_selection()

    def _clear_selection(self):
        self.selected_ids = []
        self._update_selection()
    
    def _toggle_description(self, frame, desc, btn, desc_label):
        # 检查是否已有展开的描述
        if hasattr(frame, 'expanded_frame') and frame.expanded_frame:
            # 收起描述
            frame.expanded_frame.destroy()
            frame.expanded_frame = None
            desc_label.configure(text=desc[:50] + "..." if len(desc) > 50 else desc)
            btn.configure(text="▼")
        else:
            # 展开描述
            # 清空原描述标签
            desc_label.configure(text="")
            # 创建展开的描述框架
            expanded_frame = ctk.CTkFrame(frame, fg_color="#f5f5f5")
            expanded_frame.pack(fill="x", padx=2, pady=2)
            full_desc_label = ctk.CTkLabel(expanded_frame, text=desc, 
                                        font=("Microsoft YaHei", 10),
                                        text_color="#333333", 
                                        wraplength=820, justify="left", anchor="w")
            full_desc_label.pack(side="left", padx=5, pady=3, fill="x", expand=True)
            frame.expanded_frame = expanded_frame
            btn.configure(text="▲")



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
