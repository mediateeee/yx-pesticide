# -*- coding:utf-8 -*-
import os
import winreg
import logging
import subprocess
import ctypes
import sys
import time
import requests
import json
import psutil
import threading
import tkinter as tk
from tkinter import Tk, Button, Label, messagebox, filedialog, ttk

# 获取程序运行目录
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__)) # 程序所在目录
LOG_FILE = os.path.join(PROGRAM_DIR, '我是主程序LOG.log') # LOG文件目录
DESKTOP_DIR = os.path.join(os.path.expanduser('~'), 'Desktop') # 当前运行应用程序的用户的桌面

# 定义应用程序版本（年.月.日.版本）
VERSION = '26.1.31.0'

# 更新下载路径
DOWNLOAD_FILE = os.path.join(DESKTOP_DIR, "更新版本的银杏杀虫剂.exe")  # 下载到桌面

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),  # 输出到主日志文件，覆写
        logging.StreamHandler(sys.stdout)  # 输出到控制台
    ]
)

# 定义病毒特征
VIRUS_NAMES = ["windows explorer.exe", " .exe"]  # 病毒文件名
HIDDEN_FOLDER_ATTRIB = 0x02  # 隐藏文件夹属性

# 定义注册表启动项路径
STARTUP_PATHS = [
    r"Software\Microsoft\Windows\CurrentVersion\Run",
    r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
]

# Gitee API 信息
GITEE_API_URL = f"https://gitee.com/api/v5/repos/mediateeee/yx-pesticide/releases/latest"

def is_admin():
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员身份重新运行程序"""
    if not is_admin():
        # 使用 ShellExecuteW 提权运行
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        # 退出当前进程
        sys.exit()

def compare_versions(current_version, latest_version):
    """
    比较版本号，判断是否需要更新
    版本号格式为: 年.月.日.版本 (例如: 25.3.16.7)
    """
    try:
        current_parts = list(map(int, current_version.split('.')))
        latest_parts = list(map(int, latest_version.split('.')))
        
        # 确保版本号有4个部分，不足的补0
        while len(current_parts) < 4:
            current_parts.append(0)
        while len(latest_parts) < 4:
            latest_parts.append(0)
        
        # 从主版本号开始逐级比较
        for i in range(4):
            if latest_parts[i] > current_parts[i]:
                return True  # 需要更新
            elif latest_parts[i] < current_parts[i]:
                return False  # 不需要更新
        
        return False  # 版本号完全相同，不需要更新
    except Exception as e:
        logging.error(f"版本号比较失败: {e}")
        return False

def check_for_updates():
    """检查是否有新版本"""
    try:
        # 获取最新发布信息
        response = requests.get(GITEE_API_URL)
        if response.status_code != 200:
            logging.error(f"无法获取发布信息，状态码：{response.status_code}")
            return None

        release_info = json.loads(response.text)
        latest_version = release_info["tag_name"]  # 最新版本号
        update_log = release_info.get("body", "暂无更新说明")  # 更新日志，添加默认值
        
        # 比对版本号
        if not compare_versions(VERSION, latest_version):
            logging.info(f"当前版本 {VERSION} 已是最新，无需更新")
            messagebox.showinfo("检查更新", f"当前版本 {VERSION} 已是最新，无需更新")
            return None
            
        assets = release_info.get("assets", [])

        # 查找可执行文件的下载链接
        download_url = None
        for asset in assets:
            if asset["name"] == "yx-pesticide.exe":  # 检查文件名
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            logging.error("未找到可执行文件的下载链接")
            return None

        return latest_version, download_url, update_log
    except Exception as e:
        logging.error(f"检查更新失败：{e}")
        return None

def download_update(download_url):
    """下载最新版本并显示进度条和实时信息"""
    download_window = None
    progress = None
    download_label = None
    
    try:
        # 创建一个新的顶级窗口来显示下载进度
        download_window = tk.Toplevel()
        download_window.title("下载更新")
        download_window.geometry("400x150")
        download_window.transient()  # 设置为临时窗口
        download_window.grab_set()   # 设置为模态窗口
        download_window.protocol("WM_DELETE_WINDOW", lambda: None)  # 禁用关闭按钮
        
        # 设置窗口居中
        download_window.update_idletasks()
        width = download_window.winfo_width()
        height = download_window.winfo_height()
        x = (download_window.winfo_screenwidth() // 2) - (width // 2)
        y = (download_window.winfo_screenheight() // 2) - (height // 2)
        download_window.geometry(f'{width}x{height}+{x}+{y}')

        # 创建进度条
        progress = ttk.Progressbar(download_window, orient="horizontal", length=300, mode="determinate")
        progress.pack(pady=10)

        # 创建标签来显示下载信息
        download_label = tk.Label(download_window, text="正在连接服务器...", font=("微软雅黑", 12))
        download_label.pack(pady=10)
        
        # 立即显示窗口
        download_window.update()

        # 下载文件
        download_label.config(text="正在下载...")
        download_window.update()
        
        response = requests.get(download_url, stream=True, timeout=30)
        if response.status_code != 200:
            download_label.config(text=f"下载失败，状态码：{response.status_code}")
            download_window.update()
            time.sleep(2)  # 让用户看到错误信息
            download_window.destroy()
            logging.error(f"下载失败，状态码：{response.status_code}")
            return False

        total_size = int(response.headers.get('content-length', 0))  # 获取文件总大小
        if total_size == 0:
            # 如果无法获取总大小，显示 "未知大小"
            logging.warning("无法获取文件大小，使用未知大小显示")
            download_label.config(text="未知大小文件，正在下载...")
            download_window.update()
        else:
            # 如果文件大小有效，显示文件大小
            logging.info(f"文件总大小: {format_size(total_size)}")

        downloaded = 0  # 已下载的字节数
        start_time = time.time()  # 记录开始时间

        with open(DOWNLOAD_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 计算已下载的百分比并更新进度条
                    if total_size > 0:
                        progress_value = (downloaded / total_size) * 100
                        progress['value'] = progress_value

                    # 计算下载速率，避免除以零
                    elapsed_time = time.time() - start_time
                    download_speed = (downloaded / elapsed_time) / 1024 if elapsed_time > 0 else 0  # KB/s
                    download_speed = round(download_speed, 2)

                    # 更新显示信息
                    if total_size > 0:
                        download_label.config(
                            text=f"已下载: {format_size(downloaded)} / {format_size(total_size)}\n"
                                 f"下载速度: {download_speed} KB/s\n"
                                 f"进度: {progress_value:.1f}%"
                        )
                    else:
                        download_label.config(
                            text=f"已下载: {format_size(downloaded)}\n"
                                 f"下载速度: {download_speed} KB/s"
                        )
                    
                    # 定期更新窗口，但不要太频繁
                    if downloaded % (8192 * 10) == 0:  # 每10个chunk更新一次
                        download_window.update()

        # 下载完成后显示100%并短暂停留
        progress['value'] = 100
        download_label.config(text="下载完成！\n请稍后...")
        download_window.update()
        time.sleep(1)  # 让用户看到完成信息

        # 先取消模态窗口，再销毁
        download_window.grab_release()
        download_window.destroy()
        download_window.update()  # 强制更新确保窗口销毁
        
        return True

    except requests.exceptions.Timeout:
        if download_label and download_window:
            download_label.config(text="下载超时，请检查网络连接")
            download_window.update()
            time.sleep(2)
            download_window.grab_release()
            download_window.destroy()
        logging.error("下载超时")
        return False
        
    except requests.exceptions.ConnectionError:
        if download_label and download_window:
            download_label.config(text="网络连接失败，请检查网络")
            download_window.update()
            time.sleep(2)
            download_window.grab_release()
            download_window.destroy()
        logging.error("网络连接失败")
        return False
        
    except Exception as e:
        # 在异常处理中安全地使用变量
        if download_label and download_window:
            error_msg = str(e)
            if len(error_msg) > 50:
                error_msg = error_msg[:50] + "..."
            download_label.config(text=f"下载失败：{error_msg}")
            download_window.update()
            time.sleep(2)
            download_window.grab_release()
            download_window.destroy()
        logging.error(f"下载失败：{e}")
        return False
    finally:
        # 确保窗口被正确销毁
        if download_window and download_window.winfo_exists():
            try:
                download_window.grab_release()
                download_window.destroy()
            except:
                pass

def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def update_program():
    """更新程序主逻辑"""
    # 检查更新
    update_info = check_for_updates()
    if not update_info:
        return

    latest_version, download_url, update_log = update_info

    # 弹出提示框询问用户是否更新
    root = Tk()
    root.withdraw()
    confirm = messagebox.askyesno("检查到更新", 
                                f"当前版本: {VERSION}\n最新版本: {latest_version}\n\n是否立即更新？\n\n更新日志：\n{update_log}")
    root.destroy()

    if not confirm:
        logging.info("用户取消更新。")
        return

    # 提示完成
    if download_update(download_url):
        # 提示用户手动重启
        root = Tk()
        root.withdraw()
        messagebox.showinfo("下载完毕", "下载完毕！新版应用程序已放置在桌面上，请使用新版应用程序并删除旧版。")
        root.destroy()

def is_explorer_running():
    """检查是否存在 Windows Explorer 进程"""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'Windows Explorer.exe':
            return True
    return False

class YxPesticide:
    def __init__(self, root):
        self.root = root
        self.root.title("银杏杀虫剂")
        self.root.geometry("600x600")

        # 界面组件 - 直接添加到root窗口
        self.welcome = Label(root, text="欢迎使用银杏杀虫剂 {}".format(VERSION), font=("微软雅黑", 28))
        self.welcome.pack(pady=10)

        self.choose = Label(root, text="请选择功能：", font=("微软雅黑", 16))
        self.choose.pack(pady=10)

        self.button_symlink = Button(root, text="检查电脑", command=self.check_computer, font=("微软雅黑", 14))
        self.button_symlink.pack(pady=10)

        self.button_scan = Button(root, text="扫描查杀", command=self.scan_and_clean, font=("微软雅黑", 14))
        self.button_scan.pack(pady=10)

        self.button_about = Button(root, text="关于病毒", command=self.show_about, font=("微软雅黑", 14))
        self.button_about.pack(pady=10)

        self.button_update = Button(root, text="检查更新", command=update_program, font=("微软雅黑", 14))
        self.button_update.pack(pady=10)

        self.button_log = Button(self.root, text="打开LOG所在目录", command=self.open_log_directory, font=("微软雅黑", 14))
        self.button_log.pack(pady=10)

        self.about = Label(self.root, text="Made by mediateeee & DeepSeek. \n 若您是第一次使用该应用程序，请先进行“检查电脑”，再进行“扫描查杀”。", font=("微软雅黑", 12))
        self.about.pack(pady=10)

        self.about = Label(self.root, text="开放源代码应用程序，详见 https://gitee.com/mediateeee/yx-pesticide ", font=("微软雅黑", 12))
        self.about.pack(pady=10)

        self.scan_progress_window = None
        self.scan_progress_bar = None
        self.scan_status_label = None
        self.scan_cancel_flag = False  
        self.scanning_thread = None 

    def check_computer(self):
        """设置防护：创建符号链接、设置文件权限并清理注册表"""
        # 提示用户
        confirm = messagebox.askokcancel(
            "检查电脑",
            "即将进行检查电脑功能！\n\n本功能将尝试检查并删除计算机中的病毒文件。\n\n是否继续？"
        )
        if not confirm:
            return

        try:
            virus_found = False # 标记是否发现病毒

            # 1. 杀死 Windows Explorer 进程
            if is_explorer_running():
                subprocess.run('taskkill /f /im "Windows Explorer.exe"', shell=True, check=True)
                logging.info("已杀死 Windows Explorer 进程。")
            else:
                logging.info("Windows Explorer 进程未运行，无需杀死。")

            # 2. 删除 AppData\Roaming 下的病毒文件
            roaming_dir = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming')
            virus_files = ["360se_dump.db", "googlechrome.log", "Windows Explorer.exe"]
            for file_name in virus_files:
                file_path = os.path.join(roaming_dir, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"已删除病毒文件: {file_path}")
                    virus_found = True  # 标记发现病毒
                else:
                    logging.warning(f"文件不存在: {file_path}")

            # 3. 扫描并清理注册表
            for startup_path in STARTUP_PATHS:
                self.scan_registry(startup_path)

            # 4. 根据操作结果提示用户
            if virus_found:
                messagebox.showinfo("完成", "发现病毒并已查杀！\n\nLOG文件已保存在：{}".format(LOG_FILE))
            else:
                messagebox.showinfo("完成", "未发现病毒。\n\nLOG文件已保存在：{}".format(LOG_FILE))
                
        except Exception as e:
            logging.error(f"操作失败: {e}")
            messagebox.showerror("错误", f"操作失败: {e}")

    def open_log_directory(self):
        """打开LOG所在目录"""
        log_dir = os.path.dirname(LOG_FILE)
        if os.path.exists(log_dir):
            os.startfile(log_dir)
        else:
            messagebox.showerror("错误", f"目录不存在: {log_dir}")

    def scan_and_clean(self):
        """扫描查杀：选择磁盘根目录并扫描"""
        confirm = messagebox.askokcancel(
            "扫描查杀",
            "请选择你要进行扫描的目录。\n\n是否继续？"
        )
        if not confirm:
            return

        # 弹出文件夹选择窗口，让用户选择
        scan_path = filedialog.askdirectory(title="选择磁盘根目录")
        if not scan_path:
            return

        # 创建扫描进度窗口
        self.create_scan_progress_window()
        
        # 在新的线程中执行扫描，避免界面卡死
        self.scan_cancel_flag = False
        self.scanning_thread = threading.Thread(
            target=self.perform_scan_and_clean, 
            args=(scan_path,),
            daemon=True
        )
        self.scanning_thread.start()
        
        # 启动进度更新
        self.root.after(100, self.update_scan_progress)

    def create_scan_progress_window(self):
        """创建扫描进度窗口"""
        if self.scan_progress_window and self.scan_progress_window.winfo_exists():
            self.scan_progress_window.destroy()
        
        self.scan_progress_window = tk.Toplevel(self.root)
        self.scan_progress_window.title("扫描进度")
        self.scan_progress_window.geometry("500x180")
        self.scan_progress_window.transient(self.root)  # 设置为临时窗口
        self.scan_progress_window.grab_set()  # 模态窗口
        self.scan_progress_window.protocol("WM_DELETE_WINDOW", self.cancel_scan)  # 点击关闭时取消扫描
        
        # 设置窗口位置（居中）
        self.scan_progress_window.update_idletasks()
        width = self.scan_progress_window.winfo_width()
        height = self.scan_progress_window.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        self.scan_progress_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 扫描标题
        title_label = tk.Label(
            self.scan_progress_window, 
            text="正在扫描...", 
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # 进度条
        self.scan_progress_bar = ttk.Progressbar(
            self.scan_progress_window, 
            orient="horizontal", 
            length=450, 
            mode="indeterminate"  # 使用不确定模式，因为不知道总文件数
        )
        self.scan_progress_bar.pack(pady=10)
        self.scan_progress_bar.start(10)  # 开始动画
        
        # 状态标签
        self.scan_status_label = tk.Label(
            self.scan_progress_window, 
            text="准备扫描...", 
            font=("微软雅黑", 12)
        )
        self.scan_status_label.pack(pady=5)
        
        # 扫描统计信息
        self.scan_stats_label = tk.Label(
            self.scan_progress_window, 
            text="已扫描文件: 0  发现病毒: 0", 
            font=("微软雅黑", 10)
        )
        self.scan_stats_label.pack(pady=5)
        
        # 取消按钮
        cancel_button = tk.Button(
            self.scan_progress_window,
            text="取消扫描",
            command=self.cancel_scan,
            font=("微软雅黑", 12),
            bg="#ff6b6b",
            fg="white",
            width=15
        )
        cancel_button.pack(pady=10)

    def cancel_scan(self):
        """取消扫描"""
        self.scan_cancel_flag = True
        if self.scan_status_label:
            self.scan_status_label.config(text="正在取消扫描...")
        messagebox.showinfo("提示", "扫描已取消")

    def update_scan_progress(self):
        """更新扫描进度显示"""
        if not self.scan_progress_window or not self.scan_progress_window.winfo_exists():
            return
            
        # 检查扫描线程是否还在运行
        if self.scanning_thread and self.scanning_thread.is_alive():
            # 继续更新进度
            self.root.after(100, self.update_scan_progress)
        else:
            # 扫描完成，关闭进度窗口
            if self.scan_progress_window and self.scan_progress_window.winfo_exists():
                self.scan_progress_window.grab_release()
                self.scan_progress_window.destroy()
                self.scan_progress_window = None

    def perform_scan_and_clean(self, scan_path):
        """执行扫描和清理的实际操作"""
        try:
            # 初始化统计信息
            total_files = 0
            scanned_files = 0
            virus_found = 0
            
            # 先统计文件总数（为了显示进度，但实际上我们使用的是不确定模式）
            # 这里可以选择性地实现文件统计，如果目录很大可能会慢
            
            logging.info(f"开始扫描目录: {scan_path}")
            
            if not os.path.exists(scan_path):
                if self.scan_status_label:
                    self.scan_status_label.config(text=f"目录不存在: {scan_path}")
                logging.warning(f"目录不存在: {scan_path}")
                return

            # 遍历目录
            for root, dirs, files in os.walk(scan_path):
                # 检查是否取消扫描
                if self.scan_cancel_flag:
                    if self.scan_status_label:
                        self.scan_status_label.config(text="扫描已取消")
                    logging.info("用户取消扫描")
                    return
                    
                # 更新状态
                if self.scan_status_label:
                    self.scan_status_label.config(text=f"正在扫描: {root}")
                
                # 扫描文件
                for file in files:
                    # 检查是否取消扫描
                    if self.scan_cancel_flag:
                        return
                    
                    file_path = os.path.join(root, file)
                    scanned_files += 1
                    
                    # 更新统计信息（每扫描100个文件更新一次）
                    if scanned_files % 100 == 0 and self.scan_stats_label:
                        self.scan_stats_label.config(
                            text=f"已扫描文件: {scanned_files}  发现病毒: {virus_found}"
                        )
                    
                    # 检查是否为病毒
                    if self.is_folder_virus(file_path):
                        logging.info(f"发现病毒文件: {file_path}")
                        self.clean_folder_virus(file_path)
                        virus_found += 1
                        
                        # 更新统计信息
                        if self.scan_stats_label:
                            self.scan_stats_label.config(
                                text=f"已扫描文件: {scanned_files}  发现病毒: {virus_found}"
                            )
                    
                    # 避免界面卡顿，每扫描500个文件稍微暂停一下
                    if scanned_files % 500 == 0:
                        time.sleep(0.01)  # 短暂暂停，让界面有机会更新

            # 检查目标病毒文件
            target_file = os.path.join(scan_path, ".exe")
            if os.path.exists(target_file):
                try:
                    os.remove(target_file)
                    logging.info(f"已删除病毒文件: {target_file}")
                    virus_found += 1
                except Exception as e:
                    logging.error(f"删除文件失败: {target_file} - {e}")
                    # 在状态中显示错误
                    if self.scan_status_label:
                        self.scan_status_label.config(text=f"删除失败: {os.path.basename(target_file)}")

            # 扫描完成
            if self.scan_status_label and not self.scan_cancel_flag:
                self.scan_status_label.config(text="扫描完成！")
                if self.scan_stats_label:
                    self.scan_stats_label.config(
                        text=f"扫描完成！共扫描文件: {scanned_files}  发现病毒: {virus_found}"
                    )
            
            # 停止进度条动画
            if self.scan_progress_bar:
                self.scan_progress_bar.stop()
            
            # 短暂显示完成状态
            time.sleep(1)
            
            # 在主线程中显示完成消息
            if not self.scan_cancel_flag:
                self.root.after(0, lambda: self.show_scan_result(scanned_files, virus_found))
                
        except Exception as e:
            logging.error(f"扫描过程中发生错误: {e}")
            if self.scan_status_label:
                self.scan_status_label.config(text=f"扫描出错: {str(e)[:50]}")
            time.sleep(2)  # 让用户看到错误信息

    def show_scan_result(self, scanned_files, virus_found):
        """显示扫描结果"""
        result_message = f"扫描完成！\n共扫描文件: {scanned_files} 个\n发现并处理病毒: {virus_found} 个\n\nLOG文件已保存在：{LOG_FILE}"
        
        if virus_found > 0:
            messagebox.showinfo("扫描完成", result_message)
        else:
            messagebox.showinfo("扫描完成", f"扫描完成！\n共扫描文件: {scanned_files} 个\n未发现病毒。\n\nLOG文件已保存在：{LOG_FILE}")

    def is_folder_virus(self, file_path):
        """检查文件是否为文件夹病毒"""
        file_name = os.path.basename(file_path)
        parent_dir = os.path.dirname(file_path)

        # 检查文件是否为 .exe 文件
        if not file_name.lower().endswith('.exe'):
            return False

        # 检查是否存在同名的隐藏文件夹
        folder_name = file_name[:-4]  # 去掉 .exe 后缀
        folder_path = os.path.join(parent_dir, folder_name)
        if os.path.exists(folder_path) and self.is_hidden_folder(folder_path):
            return True

        return False

    def clean_folder_virus(self, file_path):
        """清理文件夹病毒"""
        try:
            # 删除病毒文件
            os.remove(file_path)
            logging.info(f"已删除病毒文件: {file_path}")

            # 恢复被隐藏的文件夹
            folder_name = os.path.basename(file_path)[:-4]  # 去掉 .exe 后缀
            folder_path = os.path.join(os.path.dirname(file_path), folder_name)
            if os.path.exists(folder_path):
                self.restore_hidden_folder(folder_path)
                logging.info(f"已恢复隐藏文件夹: {folder_path}")
        except Exception as e:
            logging.error(f"清理病毒文件失败: {file_path} - {e}")

    def is_hidden_folder(self, folder_path):
        """检查是否为隐藏文件夹"""
        try:
            # 使用attrib命令避免权限问题，不会弹出CMD窗口
            result = subprocess.run(
                ['attrib', folder_path], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW  # 不创建控制台窗口
            )
            # 检查输出中是否包含 'H' (隐藏属性)
            return ' H ' in result.stdout
        except Exception as e:
            logging.error(f"检查隐藏文件夹失败: {folder_path} - {e}")
            return False

    def restore_hidden_folder(self, folder_path):
        """恢复隐藏文件夹"""
        try:
            # 使用attrib命令恢复文件夹，避免弹出CMD窗口
            subprocess.run(
                ['attrib', '-h', folder_path], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW  # 不创建控制台窗口
            )
            logging.info(f"已恢复隐藏文件夹: {folder_path}")
        except Exception as e:
            logging.error(f"恢复隐藏文件夹失败: {folder_path} - {e}")
        """恢复隐藏文件夹"""
        try:
            os.system(f'attrib -h "{folder_path}"')
            logging.info(f"已恢复隐藏文件夹: {folder_path}")
        except Exception as e:
            logging.error(f"恢复隐藏文件夹失败: {folder_path} - {e}")

    def is_virus_file(self, file_path):
        """检查文件是否为病毒文件"""
        # 检查文件路径是否包含病毒文件名
        for virus_name in VIRUS_NAMES:
            if virus_name.lower() in file_path.lower():
                return True
        return False

    def scan_registry(self, startup_path):
        """扫描注册表启动项"""
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_path)
            virus_found = False  # 标记是否发现病毒启动项
            for i in range(winreg.QueryInfoKey(reg_key)[1]):
                name, value, _ = winreg.EnumValue(reg_key, i)
                if self.is_virus_file(value):
                    logging.warning(f"发现病毒启动项: {name} - {value}")
                    self.delete_registry_value(reg_key, name)
                    virus_found = True
            winreg.CloseKey(reg_key)
            if not virus_found:
                logging.info(f"未发现病毒启动项: {startup_path}")
        except Exception as e:
            logging.error(f"扫描注册表失败: {startup_path} - {e}")

    def delete_registry_value(self, reg_key, value_name):
        """删除注册表值"""
        try:
            subprocess.run(f'reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "Windows Explorer" /f', shell=True, check=True)
            logging.info(f"已删除注册表值: {value_name}")
        except Exception as e:
            logging.error(f"删除注册表值失败: {value_name} - {e}")

    def show_about(self):
        """关于病毒：显示病毒信息"""
        about_text = """
        病毒名称："Windows Explorer.exe"
        行为特征（有待扩充）：
        1. 将U盘中的文件夹隐藏并替换为恶意可执行文件。
        2. 复制自身到系统目录（如 AppData\Roaming）。
        3. 修改注册表实现开机自启。
        4. 通过U盘传播。
        5. 看似不会危害计算机系统，但是恶心人。
        6. 更多内容请见开源仓库。
        """
        messagebox.showinfo("关于病毒", about_text)

if __name__ == "__main__":
    # 检查是否以管理员身份运行
    run_as_admin()

    # 如果以管理员身份运行，启动主程序
    root = Tk()
    app = YxPesticide(root)
    root.mainloop()