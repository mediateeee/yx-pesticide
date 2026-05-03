# -*- coding:utf-8 -*-
import os
import logging
import subprocess
import ctypes
import sys
import hashlib
import time
import requests
import json
import winreg
import threading
import tkinter as tk
from tkinter import Tk, Button, Label, messagebox, filedialog, ttk

# 基本变量
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__)) # 程序所在目录
LOG_FILE = os.path.join(PROGRAM_DIR, '我是主程序LOG.log') # LOG文件目录
DESKTOP_DIR = os.path.join(os.path.expanduser('~'), 'Desktop') # 当前运行应用程序的用户的桌面
DOWNLOAD_FILE = os.path.join(DESKTOP_DIR, "更新版本的银杏杀虫剂.exe")  # 下载到桌面
GITEE_API_URL = f"https://gitee.com/api/v5/repos/mediateeee/yx-pesticide/releases/latest"  # Gitee API 信息

# 定义应用程序版本（年.月.日.版本）
VERSION = '26.5.3.0'

# 扫描查杀变量
VIRUS_SIZE = 9376256  # 病毒大小：8.94 MB (9,376,256 字节)
VIRUS_HEAD_HASH = "134f9b0d2a51fd14e9ebdcbc56d63e11"  # 头部64KB病毒哈希值
HASH_READ_SIZE = 65536 # 读取文件头部的大小，此为64KB

# 哈希值计算模块
def get_file_head_hash(file_path):
    """计算文件头部哈希。成功返回哈希字符串，失败返回空字符串"""
    try:
        if not os.path.isfile(file_path):
            return ""
        with open(file_path, "rb") as f:
            data = f.read(HASH_READ_SIZE) 
        return hashlib.md5(data).hexdigest()
    except Exception as e:
        logging.debug(f"计算文件哈希失败 {file_path}: {e}")
        return ""

# 日志模块
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),  # 输出到主日志文件，覆写
        logging.StreamHandler(sys.stdout)  # 输出到控制台
    ]
)

logging.info(f"银杏杀虫软件 {VERSION}")
logging.info(f"程序路径: {PROGRAM_DIR}")
logging.info(f"Python 版本: {sys.version}")

try:
    """Windows 详细版本"""
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
    product_name = winreg.QueryValueEx(key, "ProductName")[0]
    current_build = winreg.QueryValueEx(key, "CurrentBuild")[0]
    winreg.CloseKey(key)
    logging.info(f"Windows 详细版本: {product_name} (Build {current_build})")
except Exception as e:
    logging.debug(f"获取 Windows 详细版本失败: {e}")

def is_admin():
    """检查是否是管理员"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

logging.info(f"当前用户: {os.environ.get('USERNAME', 'Unknown')}")
logging.info(f"计算机名: {os.environ.get('COMPUTERNAME', 'Unknown')}")
logging.info("="*60)

## 以管理员程序运行模块
def run_as_admin():
    """以管理员身份重新运行程序"""
    if not is_admin():
        # 使用 ShellExecuteW 提权运行并退出
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

# 软件更新模块
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
                                f"当前版本: {VERSION}\n最新版本: {latest_version}\n\n是否立即更新？ 注意，如果点击下载没反应，请查看桌面上是不是有一个叫做“更新版本的银杏杀虫剂”的软件？如果是，请给他改个名字再下载更新。\n\n更新日志：\n{update_log}")
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

def check_for_updates():
    """检查是否有新版本"""
    try:
        # 获取最新发布信息
        response = requests.get(GITEE_API_URL, timeout=10, proxies={"http": None, "https": None})
        if response.status_code != 200:
            logging.error(f"无法获取发布信息，状态码：{response.status_code}")
            messagebox.showerror("检查更新失败", f"服务器响应错误：{response.status_code}")
            return None

        release_info = json.loads(response.text)
        latest_version = release_info["tag_name"]
        update_log = release_info.get("body", "暂无更新说明")
        
        # 比对版本号
        if not compare_versions(VERSION, latest_version):
            logging.info(f"当前版本 {VERSION} 已是最新，无需更新")
            messagebox.showinfo("检查更新", f"当前版本 {VERSION} 已是最新")
            return None
            
        assets = release_info.get("assets", [])

        # 查找可执行文件的下载链接
        download_url = None
        for asset in assets:
            if asset["name"] == "yx-pesticide.exe":
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            logging.error("没能找到更新文件的下载链接")
            messagebox.showerror("检查更新失败", "未找到更新文件下载链接")
            return None

        return latest_version, download_url, update_log
    except Exception as e:
        logging.error(f"检查更新失败：{e}")
        # 分类错误信息，避免输出过长
        error_msg = str(e)
        if "ProxyError" in error_msg:
            msg = "检查更新失败\n\n网络代理错误，请检查网络连接后重试"
        elif "Timeout" in error_msg:
            msg = "检查更新失败\n\n连接超时，请检查网络后重试"
        elif "Connection" in error_msg:
            msg = "检查更新失败\n\n无法连接服务器，请检查网络后重试"
        else:
            msg = f"检查更新失败\n\n错误：{error_msg[:200]}\n\n请检查网络后重试"
        messagebox.showerror("检查更新失败", msg)
        return None
        
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

def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

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
        
        response = requests.get(download_url, stream=True, timeout=30, proxies={"http": None, "https": None})
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

# 检查电脑模块
def check_computer():
    """检查电脑"""
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
        try:
            result = subprocess.run(
                'taskkill /f /im "Windows Explorer.exe"',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                logging.info("已杀死 Windows Explorer 进程。")
            elif result.returncode == 128:
                logging.info("Windows Explorer 进程未运行，无需杀死。")
            else:
                error_msg = f"终止Windows Explorer进程时出错: 返回码{result.returncode}"
                if result.stderr:
                    error_msg += f", 错误信息: {result.stderr.strip()}"
                logging.error(error_msg)
        except Exception as e:
            logging.error(f"检查Windows Explorer进程时发生异常: {e}")

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
        try:
            # 尝试删除注册表项
            result = subprocess.run(
                'reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "Windows Explorer" /f', 
                shell=True, 
                capture_output=True, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
                
            if result.returncode == 0:
                logging.info('已删除注册表项: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run 下的 "Windows Explorer" 项')
            elif "错误: 系统找不到指定的注册表项或值。" in result.stderr:
                logging.info('这个注册表项不存在: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run 下的 "Windows Explorer" 项')
            else:
                logging.error('删除注册表项失败: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run 下的 "Windows Explorer" 项')
                    
        except Exception as e:
            logging.error(f'在处理注册表项时出错: {e}')
        
        # 4. 根据操作结果提示用户
        if virus_found:
            messagebox.showinfo("完成", "发现病毒并已查杀！\n\nLOG文件已保存在：{}".format(LOG_FILE))
        else:
            messagebox.showinfo("完成", "未发现病毒。\n\nLOG文件已保存在：{}".format(LOG_FILE))
                
    except Exception as e:
        logging.error(f"操作失败: {e}")
        messagebox.showerror("错误", f"操作失败: {e}")

# 关于病毒和打开日志模块
def show_about():
    """关于病毒：显示病毒信息"""
    about_text = """    病毒名称："Windows Explorer.exe"
    行为特征（有待扩充）：
    1. 将U盘中的文件夹隐藏并替换为恶意可执行文件。
    2. 复制自身到系统目录（如 AppData\Roaming）。
    3. 修改注册表实现开机自启。
    4. 通过U盘传播。
    5. 看似不会危害计算机系统，但是恶心人。
    6. 更多内容请见开源仓库。
    """
    messagebox.showinfo("关于病毒", about_text)

def open_log_file():
    """打开LOG文件"""
    if os.path.exists(LOG_FILE):
        try:  # 直接打开日志
            os.startfile(LOG_FILE)
            logging.info("已打开LOG文件")
        except Exception as e:
            try: # 指定记事本打开日志
                subprocess.run(['notepad.exe', LOG_FILE], check=True)
                logging.info("已使用记事本打开LOG文件")
            except Exception as e2:
                error_msg = f"无法打开LOG文件: {str(e)}\n尝试用记事本打开也失败: {str(e2)}"
                logging.error(error_msg)
                messagebox.showerror("错误", f"{error_msg}\n\n将尝试打开LOG文件所在目录。")
            # 尝试打开目录
            log_dir = os.path.dirname(LOG_FILE)
            if os.path.exists(log_dir):
                os.startfile(log_dir)
                messagebox.showerror("错误", f"目录打不开: {log_dir}")

# UI 与 扫描查杀模块
class YxPesticide:
    def __init__(self, root):
        self.root = root
        self.root.title("银杏杀虫剂")
        self.root.geometry("600x650")

        self.welcome = Label(root, text="欢迎使用银杏杀虫剂 {}".format(VERSION), font=("微软雅黑", 28))
        self.welcome.pack(pady=10)

        self.choose = Label(root, text="请选择功能：", font=("微软雅黑", 16))
        self.choose.pack(pady=10)

        self.button_symlink = Button(root, text="检查电脑", command=check_computer, font=("微软雅黑", 14))
        self.button_symlink.pack(pady=10)

        self.button_scan = Button(root, text="扫描查杀", command=self.scan_and_clean, font=("微软雅黑", 14))
        self.button_scan.pack(pady=10)

        self.button_about = Button(root, text="关于病毒", command=show_about, font=("微软雅黑", 14))
        self.button_about.pack(pady=10)

        self.button_update = Button(root, text="检查更新", command=update_program, font=("微软雅黑", 14))
        self.button_update.pack(pady=10)

        self.button_log = Button(self.root, text="打开日志", command=open_log_file, font=("微软雅黑", 14))
        self.button_log.pack(pady=10)

        self.about = Label(self.root, text="Made by mediateeee & Ai \n 若您是第一次使用该应用程序，请先进行“检查电脑”，再进行“扫描查杀”", font=("微软雅黑", 12))
        self.about.pack(pady=10)

        self.about = Label(self.root, text="有任何问题，欢迎联系：mediateeee@foxmail.com", font=("微软雅黑", 12))
        self.about.pack(pady=10)

        self.about = Label(self.root, text="开放源代码应用程序，详见 https://gitee.com/mediateeee/yx-pesticide ", font=("微软雅黑", 12))
        self.about.pack(pady=10)

        self.scanning = False  # 添加扫描状态标志
        self.scan_stats = {"scanned": 0, "virus_found": 0}  # 扫描统计

    def scan_and_clean(self):
        """扫描查杀"""
        confirm = messagebox.askokcancel(
            "扫描查杀",
            "请选择你要进行扫描的目录。\n\n是否继续？"
        )
        if not confirm:
            return

        scan_path = filedialog.askdirectory(title="请选择你要进行扫描的目录。")
        if not scan_path:
            return

        if not os.path.exists(scan_path):
            messagebox.showerror("错误", "选择的目录不存在！")
            return

        # 统计总文件数，便于确定进度条
        self.total_files = 0
        def count_files(path):
            try:
                for entry in os.listdir(path):
                    full_path = os.path.join(path, entry)
                    if os.path.isfile(full_path):
                        self.total_files += 1
                    elif os.path.isdir(full_path):
                        count_files(full_path)
            except:
                pass
        count_files(scan_path)
        logging.info(f"扫描目录总文件数: {self.total_files}")

        # 初始化进度更新频率控制变量
        self.last_virus_count = 0

        # 创建扫描进度窗口
        self.show_progress()
        
        # 重置统计
        self.scan_stats = {"scanned": 0, "virus_found": 0}
        self.scanning = True
        
        # 在新线程中扫描
        threading.Thread(
            target=self.scan_directory,
            args=(scan_path,),
            daemon=True
        ).start()
    
    def show_progress(self):
        """显示扫描进度窗口"""
        if hasattr(self, 'progress_window') and self.progress_window:
            try:
                self.progress_window.destroy()
            except:
                pass
        
        # 创建进度窗口
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("扫描进度")
        self.progress_window.geometry("450x160")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        
        # 窗口居中
        self.progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 160) // 2
        self.progress_window.geometry(f'450x160+{x}+{y}')
        
        # 标题
        tk.Label(
            self.progress_window,
            text="正在扫描...",
            font=("微软雅黑", 16, "bold")
        ).pack(pady=10)
        
        # 进度条
        self.progress_bar = ttk.Progressbar(
            self.progress_window,
            length=400,
            mode="determinate",
            orient="horizontal",
            variable=tk.DoubleVar()
        )
        self.progress_bar.pack(pady=5)
        
        # 状态标签
        self.progress_label = tk.Label(
            self.progress_window,
            text="正在准备扫描...",
            font=("微软雅黑", 11)
        )
        self.progress_label.pack(pady=5)
        
        # 统计信息
        self.stats_label = tk.Label(
            self.progress_window,
            text="已扫描: 0 个文件 | 发现病毒: 0 个 | 进度: 0%",
            font=("微软雅黑", 9)
        )
        self.stats_label.pack(pady=5)
        
        # 取消按钮
        tk.Button(
            self.progress_window,
            text="取消扫描",
            command=self.cancel_scanning,
            font=("微软雅黑", 10),
            width=12
        ).pack(pady=5)
    
    def cancel_scanning(self):
        """取消扫描"""
        self.scanning = False
        self.progress_label.config(text="正在停止扫描...")
        logging.info("用户取消扫描")
    
    def update_progress(self, folder_path, scanned, virus_found):
        """更新进度显示（优化版：解决更新缓慢/卡顿）"""
        # 1. 跳过已关闭的窗口，避免无效操作
        if not hasattr(self, 'progress_window') or not self.progress_window.winfo_exists():
            return
    
        # 2. 频率控制：每扫描10个文件才更新一次UI（减少主线程压力）
        if scanned % 10 != 0 and virus_found == self.last_virus_count:
            return
    
        # 3. 用after方法异步更新UI（核心：不阻塞主线程）
        def async_update():
            # 更新当前扫描目录
            folder_name = os.path.basename(folder_path)
            self.progress_label.config(text=f"正在扫描: {folder_name}...")
        
            # 计算进度百分比
            percent = 0
            if hasattr(self, 'total_files') and self.total_files > 0:
                percent = min(round((scanned / self.total_files) * 100, 1), 100)  # 防止超过100%
            self.progress_bar['value'] = percent
        
            # 更新统计文本
            self.stats_label.config(
                text=f"已扫描: {scanned} 个文件 | 发现病毒: {virus_found} 个 | 进度: {percent}%"
            )
    
        # 异步执行UI更新（避免阻塞扫描线程）
        self.root.after(0, async_update)
    
        # 记录最后一次病毒数，用于频率控制
        self.last_virus_count = virus_found
    
    def scan_directory(self, scan_path):
        """扫描目录"""
        try:
            logging.info(f"开始扫描目录: {scan_path}")
            
            # 使用栈而不是递归，避免深度递归问题
            scan_stack = [scan_path]
            
            while scan_stack and self.scanning:
                current_path = scan_stack.pop()
                
                try:
                    # 获取当前目录内容
                    entries = os.listdir(current_path)
                    
                    # 先处理当前目录的文件
                    for entry in entries:
                        if not self.scanning:
                            break
                            
                        full_path = os.path.join(current_path, entry)
                        
                        try:
                            if os.path.isfile(full_path):
                                # 扫描文件
                                self.scan_stats["scanned"] += 1
                                
                                # 检查是否为病毒
                                if self.is_virus_file(full_path):
                                    self.scan_stats["virus_found"] += 1
                                    self.clean_virus_file(full_path)
                                    logging.info(f"发现并清理病毒文件: {full_path}")
                                
                                # 定期更新显示（每扫描50个文件更新一次）
                                if self.scan_stats["scanned"] % 50 == 0:
                                    self.root.after(0, lambda: self.update_progress(
                                        current_path, 
                                        self.scan_stats["scanned"], 
                                        self.scan_stats["virus_found"]
                                    ))
                                    time.sleep(0.001)  # 短暂暂停，让UI响应
                            
                            elif os.path.isdir(full_path):
                                # 将子目录加入栈中
                                scan_stack.append(full_path)
                                
                        except (PermissionError, OSError) as e:
                            logging.debug(f"无法访问 {full_path}: {e}")
                
                except (PermissionError, OSError) as e:
                    logging.warning(f"无法访问目录 {current_path}: {e}")
            
            # 扫描完成
            self.finish_scan()
            
        except Exception as e:
            logging.error(f"扫描过程中发生错误: {e}")
            self.root.after(0, lambda: self.show_error(f"扫描失败: {str(e)[:100]}"))
    
    def is_virus_file(self, file_path):
        """检查是否为病毒文件"""
        try:
            file_name = os.path.basename(file_path)
            
            # 第一步：特殊病毒文件名匹配
            virus_patterns = [
                "windows explorer.exe",
                "System Volume Information.exe"
            ]

            for pattern in virus_patterns:
                if pattern in file_name:
                    return True

            if file_name == ".exe":
                logging.info(f"发现特殊病毒文件: {file_path}")
                return True

            # 第二步：病毒特征 + 大小 + 哈希过滤
            if file_name.lower().endswith('.exe'):
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size == 0: # 如果U盘空间不足，会生成0字节文件
                        # 提取同名文件夹路径
                        folder_name = file_name[:-4]
                        folder_path = os.path.join(os.path.dirname(file_path), folder_name)
                        # 检查是否存在同名文件夹
                        if os.path.exists(folder_path) and os.path.isdir(folder_path):
                            try:
                                logging.info(f"认定一个0字节病毒: {file_path}")
                                return True
                            except Exception as e:
                                logging.error(f"认定0字节病毒失败 {file_path}: {e}")
                        return False

                    # 文件大小不匹配的，直接排除
                    if not (file_size== VIRUS_SIZE):
                        logging.warning(f"文件大小不匹配，排除: {file_path}")
                        return False

                except:
                    return False
                # 同名文件夹检查
                folder_name = file_name[:-4]
                folder_path = os.path.join(os.path.dirname(file_path), folder_name)
                if os.path.exists(folder_path):
                    try:
                        if VIRUS_HEAD_HASH: # 哈希值验证
                            file_hash = get_file_head_hash(file_path)
                            if file_hash == VIRUS_HEAD_HASH:
                                return True
                            else:
                                logging.warning(f"文件哈希不匹配，排除: {file_path}")
                                return False
                    except:
                        pass

            return False

        except Exception as e:
            logging.debug(f"检查文件失败 {file_path}: {e}")
            return False
    
    def clean_virus_file(self, file_path):
        """清理病毒文件"""
        try:
            # 删除病毒文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 恢复隐藏的文件夹
            if file_path.lower().endswith('.exe'):
                folder_name = os.path.basename(file_path)[:-4]
                folder_path = os.path.join(os.path.dirname(file_path), folder_name)
                
                if os.path.exists(folder_path):
                    try:
                        subprocess.run(
                            ['attrib', '-h', folder_path],
                            capture_output=True,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    except:
                        pass
            
        except Exception as e:
            logging.error(f"清理病毒文件失败 {file_path}: {e}")
    
    def finish_scan(self):
        """完成扫描"""
        self.scanning = False
        
        # 在主线程中关闭进度窗口
        def close_window():
            if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
                self.progress_window.grab_release()
                self.progress_window.destroy()
            
            # 显示结果
            self.show_scan_result()
        
        self.root.after(0, close_window)
    
    def show_scan_result(self):
        """显示扫描结果"""
        scanned = self.scan_stats["scanned"]
        virus_found = self.scan_stats["virus_found"]
        
        if virus_found > 0:
            message = f"扫描完成！\n\n" \
                     f"共扫描文件: {scanned} 个\n" \
                     f"发现并清理病毒: {virus_found} 个\n\n" \
                     f"详细日志已保存到：\n{LOG_FILE}"
            messagebox.showinfo("扫描完成", message)
        else:
            message = f"扫描完成！\n\n" \
                     f"共扫描文件: {scanned} 个\n" \
                     f"未发现病毒文件\n\n" \
                     f"详细日志已保存到：\n{LOG_FILE}"
            messagebox.showinfo("扫描完成", message)
    
    def show_error(self, error_msg):
        """显示错误"""
        if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        
        messagebox.showerror("扫描错误", error_msg)

if __name__ == "__main__":
    # 检查是否以管理员身份运行
    run_as_admin()

    # 如果以管理员身份运行，启动主程序
    root = Tk()
    app = YxPesticide(root)
    root.after(1100, update_program)
    root.mainloop()