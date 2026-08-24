# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import tkinter as tk
from tkinter import Tk, messagebox, ttk

from ypCHECK import check_computer
from ypMAIN import CREATE_NO_WINDOW, LOG_FILE, VERSION
from ypSCAN import choose_and_scan, count_files
from ypUPDATE import update_program

#关于病毒的界面
def show_about():
    about_text = """病毒名称："Windows Explorer.exe"
行为特征（有待扩充）：
1. 将U盘中的文件夹隐藏并替换为恶意可执行文件。
2. 复制自身到系统目录（如 AppData\\Roaming）。
3. 修改注册表实现开机自启。
4. 通过U盘传播。
5. 看似不会危害计算机系统，但是恶心人。
6. 更多内容请见开源仓库。
"""
    messagebox.showinfo("关于病毒", about_text)

#打开日志的界面
def open_log_file():
    if not os.path.exists(LOG_FILE):
        messagebox.showerror("错误", f"日志文件不存在：\n{LOG_FILE}")
        return
    try:
        os.startfile(LOG_FILE)
    except OSError:
        try:
            subprocess.run(["notepad.exe", LOG_FILE], check=True, creationflags=CREATE_NO_WINDOW)
        except (OSError, subprocess.CalledProcessError) as e:
            logging.error("打开日志失败: %s", e)

#程序主界面
class YxPesticide:
    #主界面
    def __init__(self, root):
        self.root = root
        self.root.title("银杏杀虫软件")
        dpi_scale = max(1.0, self.root.winfo_fpixels("1i") / 96)
        self.ui_scale = min(1.25, 1 + (dpi_scale - 1) * 0.65)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        base_width = round(680 * self.ui_scale)
        base_height = round(720 * self.ui_scale)
        min_width = round(520 * self.ui_scale)
        min_height = round(420 * self.ui_scale)
        window_width = min(base_width, max(min_width, int(screen_width * 0.7)))
        window_height = min(base_height, max(min_height, int(screen_height * 0.8)))
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(min(min_width, window_width), min(min_height, window_height))
        self.root.configure(bg="#eef3f1")
        self.setup_styles()
        header = tk.Frame(root, bg="#123c36", height=round(158 * self.ui_scale))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="银杏杀虫软件", bg="#123c36", fg="#f7fbf8", font=("微软雅黑", round(28 * self.ui_scale), "bold"), pady=round(18 * self.ui_scale)).pack()
        tk.Label(header, text=f"专注于 Windows Explorer.exe 文件夹病毒的清理工具  ·  v{VERSION}", bg="#123c36", fg="#b9d8cd", font=("微软雅黑", round(10 * self.ui_scale))).pack()
        content = tk.Frame(root, bg="#eef3f1")
        content.pack(fill="both", expand=True, padx=42, pady=(28, 16))
        tk.Label(content, text="选择操作", bg="#eef3f1", fg="#173a34", font=("微软雅黑", 16, "bold"), anchor="w").pack(fill="x")
        tk.Label(content, text="建议首次使用先检查电脑，再扫描需要查杀的目录。", bg="#eef3f1", fg="#60736e", font=("微软雅黑", 10), anchor="w").pack(fill="x", pady=(4, 18))
        actions = tk.Frame(content, bg="#eef3f1")
        actions.pack(fill="x")
        buttons = (("检查电脑", "检查并清理系统中的病毒本体与启动项", check_computer), ("扫描查杀", "选择目录，查找并清理病毒文件", self.scan_and_clean), ("关于病毒", "了解目标病毒的行为特征", show_about), ("检查更新", "获取软件的最新版本", self.update_program), ("打开日志", "查看详细的运行与查杀记录", open_log_file))
        for text, hint, command in buttons:
            row = tk.Frame(actions, bg="#ffffff", highlightthickness=1, highlightbackground="#d9e5e0")
            row.pack(fill="x", pady=5)
            ttk.Button(row, text=text, command=command, style="secondary.TButton", width=11).pack(side="left", padx=12, pady=10)
            tk.Label(row, text=hint, bg="#ffffff", fg="#61736e", font=("微软雅黑", 10)).pack(side="left", padx=(4, 12))
        footer = tk.Frame(root, bg="#dfeae6", height=(78 * self.ui_scale))
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(footer, text="反馈邮箱  mediateeee@foxmail.com", bg="#dfeae6", fg="#45645b", font=("微软雅黑", round(9 * self.ui_scale))).pack(pady=(round(12 * self.ui_scale), round(2 * self.ui_scale)))
        tk.Label(footer, text="开源项目  https://gitee.com/mediateeee/yx-pesticide", bg="#dfeae6", fg="#45645b", font=("微软雅黑", round(9 * self.ui_scale))).pack()
        self.scanning = False
        self.scan_stats = {"scanned": 0, "virus_found": 0}
        self.total_files = 0
        self.progress_window = None
        self.last_ui_update = 0

    #初始化样式
    def setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("vista")
        style.configure("secondary.TButton", font=("微软雅黑", 10), foreground="#234941", background="#edf5f2", padding=(12, 7), borderwidth=0)
        style.map("secondary.TButton", background=[("active", "#d6e9e2"), ("pressed", "#c2ddd3")])

    #扫描查杀功能
    def scan_and_clean(self):
        choose_and_scan(self)
    #扫描查杀功能的界面
    def show_progress(self):
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("扫描进度")
        window_width = round(450 * self.ui_scale)
        window_height = round(220 * self.ui_scale)
        self.root.update_idletasks()
        window_x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        window_y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        self.progress_window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
        self.progress_window.configure(bg="#eef3f1")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        self.progress_window.protocol("WM_DELETE_WINDOW", self.cancel_scanning)
        tk.Label(self.progress_window, text="正在扫描...", bg="#eef3f1", fg="#173a34", font=("微软雅黑", 16, "bold")).pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_window, length=400, mode="indeterminate", orient="horizontal")
        self.progress_bar.pack(pady=5)
        self.progress_bar.start(10)
        self.progress_label = tk.Label(self.progress_window, text="正在准备扫描...", bg="#eef3f1", fg="#45645b", font=("微软雅黑", 11))
        self.progress_label.pack(pady=5)
        self.stats_label = tk.Label(self.progress_window, text="已扫描: 0 个文件 | 发现病毒: 0 个 | 进度: --", bg="#eef3f1", fg="#71817c", font=("微软雅黑", 9))
        self.stats_label.pack(pady=5)
        ttk.Button(self.progress_window, text="取消扫描", command=self.cancel_scanning, style="secondary.TButton", width=14).pack(pady=8, ipady=3)

    def switch_progress_mode(self):
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate", maximum=100, value=0)

    def cancel_scanning(self):
        self.scanning = False
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_label.config(text="正在停止扫描...")

    def queue_progress(self, folder_path):
        scanned = self.scan_stats["scanned"]
        found = self.scan_stats["virus_found"]
        self.root.after(0, lambda: self.update_progress(folder_path, scanned, found))

    def update_progress(self, folder_path, scanned, virus_found):
        if not self.progress_window or not self.progress_window.winfo_exists():
            return
        percent = min(round(scanned / self.total_files * 100, 1), 100) if self.total_files else 0
        self.progress_label.config(text=f"正在扫描: {os.path.basename(folder_path) or folder_path}...")
        self.progress_bar["value"] = percent
        self.stats_label.config(text=f"已扫描: {scanned} 个文件 | 发现病毒: {virus_found} 个 | 进度: {percent}%")

    def finish_scan(self):
        self.scanning = False
        self.root.after(0, self.close_scan_window)

    def close_scan_window(self):
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_bar.stop()
            self.progress_window.grab_release()
            self.progress_window.destroy()
        scanned = self.scan_stats["scanned"]
        found = self.scan_stats["virus_found"]
        message = f"扫描完成！\n\n共扫描文件: {scanned} 个\n"
        message += f"发现并清理病毒: {found} 个" if found else "未发现病毒文件"
        messagebox.showinfo("扫描完成", message + f"\n\n详细日志：\n{LOG_FILE}")

    def show_error(self, error_msg):
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        messagebox.showerror("扫描错误", error_msg)

    #检查更新功能
    def update_program(self):
        update_program(self.root)

#打开主界面
if __name__ == "__main__":
    from ypMAIN import start
    start()
