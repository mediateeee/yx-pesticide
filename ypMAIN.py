# -*- coding: utf-8 -*-
import os
import re
import logging
import subprocess
import ctypes
import sys
import hashlib
import winreg


#让 Windows 按真实像素显示程序，避免高分屏下界面模糊。
def enable_dpi_awareness():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass


enable_dpi_awareness()

VERSION = "26.8.24.3"                      #定义当前版本号
CREATE_NO_WINDOW = 0x08000000              #使子进程运行时不弹黑框
NO_PROXY = {"http": None, "https": None}   #避免因为代理导致无法访问码云
#定义 程序目录、日志文件路径、桌面路径、下载更新的文件路径、更新的API地址
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROGRAM_DIR, "银杏杀虫软件.log")
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
DOWNLOAD_FILE = os.path.join(DESKTOP_DIR, "更新版本的银杏杀虫软件.exe")
GITEE_API_URL = "https://gitee.com/api/v5/repos/mediateeee/yx-pesticide/releases/latest"
#定义 病毒文件大小、病毒文件头部哈希值、读取哈希的字节数
VIRUS_SIZE = 9376256
VIRUS_HEAD_MD5 = "134f9b0d2a51fd14e9ebdcbc56d63e11"
HASH_READ_SIZE = 65536
#定义已知病毒文件名、Roaming目录下的伴随文件、注册表启动项名称、病毒进程名称
#设置这些变量是为了便利以后的维护，若病毒演变了新的文件名或行为，只需修改这些变量即可
KNOWN_VIRUS_EXES = {"windows explorer.exe", "system volume information.exe", ".exe"}
ROAMING_COMPANION_FILES = ("360se_dump.db", "googlechrome.log")
RUN_VALUE_NAME = "Windows Explorer"
VIRUS_PROCESS_NAME = "Windows Explorer.exe"

#初始化日志记录器
def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"), logging.StreamHandler(sys.stdout)])
    logging.info("Hello")
    logging.info("银杏杀虫软件 %s", VERSION)
    logging.info("程序路径: %s", PROGRAM_DIR)
    logging.info("Python 版本: %s", sys.version)
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            product_name = winreg.QueryValueEx(key, "ProductName")[0]
            current_build = winreg.QueryValueEx(key, "CurrentBuild")[0]
        logging.info("Windows 详细版本: %s (Build %s)", product_name, current_build)
    except OSError as e:
        logging.debug("获取 Windows 详细版本失败: %s", e)
    logging.info("当前用户: %s", os.environ.get("USERNAME", "Unknown"))
    logging.info("计算机名: %s", os.environ.get("COMPUTERNAME", "Unknown"))
    logging.info("=" * 60)

#计算文件的前 HASH_READ_SIZE 字节的 MD5 哈希值
def get_file_head_hash(file_path):
    try:
        if not os.path.isfile(file_path):
            return ""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read(HASH_READ_SIZE)).hexdigest()
    except OSError as e:
        logging.debug("计算文件哈希失败 %s: %s", file_path, e)
        return ""

#检查下载到的更新文件是否是可执行的 Windows 程序（PE文件）
def look_if_runnable(file_path):
    try:
        with open(file_path, "rb") as f:
            return f.read(2) == b"MZ"
    except OSError:
        return False

#检查是不是以管理员权限运行
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

#确保以管理员身份重启程序时，原来的参数不会丢失或被错误拆开
def quote_arg(arg):
    if not arg:
        return '""'
    if any(ch in arg for ch in ' \t"'):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg

#若不是以管理员权限运行，则重新以管理员权限运行
def run_as_admin():
    if is_admin():
        return
    params = " ".join(quote_arg(a) for a in (sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv))
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)

#查找某个 .exe 文件旁边且同名的文件夹
def sibling_folder_path(file_path):
    name = os.path.basename(file_path)
    stem, ext = os.path.splitext(name)
    if ext.lower() != ".exe" or not stem:
        return None
    folder_path = os.path.join(os.path.dirname(file_path), stem)
    return folder_path if os.path.isdir(folder_path) else None


#通过文件大小和文件头部 MD5 哈希值判断文件内容是否匹配病毒特征
def matches_virus_payload(file_path):
    try:
        if os.path.getsize(file_path) != VIRUS_SIZE:
            return False
    except OSError:
        return False
    return get_file_head_hash(file_path) == VIRUS_HEAD_MD5


#综合文件名、文件大小、同名文件夹和病毒特征判断是否为病毒文件
def is_virus_file(file_path):
    try:
        if not os.path.isfile(file_path):
            return False
        name_l = os.path.basename(file_path).lower()
        if not name_l.endswith(".exe"):
            return False
        size = os.path.getsize(file_path)
        folder = sibling_folder_path(file_path)
        known = name_l in KNOWN_VIRUS_EXES
        incomplete_copy = size == 0 and folder is not None
        if known:
            if incomplete_copy:
                logging.info("认定 0 字节已知样本残留: %s", file_path)
                return True
            if matches_virus_payload(file_path):
                return True
            logging.info("已知文件名但特征不匹配，跳过: %s", file_path)
            return False
        if incomplete_copy:
            logging.info("认定 0 字节文件夹伪装残留: %s", file_path)
            return True
        return bool(folder and matches_virus_payload(file_path))
    except OSError as e:
        logging.debug("检查文件失败 %s: %s", file_path, e)
        return False


#取消同名文件夹的隐藏和系统属性，方便用户查看和使用
def unhide_folder(folder_path):
    try:
        subprocess.run(["attrib", "-h", "-s", folder_path], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
    except OSError as e:
        logging.debug("取消隐藏失败 %s: %s", folder_path, e)


#删除病毒文件，并恢复其同名文件夹的正常显示属性
def clean_virus_file(file_path):
    folder_path = sibling_folder_path(file_path)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        if folder_path:
            unhide_folder(folder_path)
    except OSError as e:
        logging.error("清理病毒文件失败 %s: %s", file_path, e)
        return False
    return True


#比较当前版本和最新版本，判断是否需要更新
def compare_versions(current_version, latest_version):
    try:
        current_parts = list(map(int, current_version.split(".")))
        latest_parts = list(map(int, latest_version.split(".")))
        current_parts += [0] * (4 - len(current_parts))
        latest_parts += [0] * (4 - len(latest_parts))
        return latest_parts[:4] > current_parts[:4]
    except (TypeError, ValueError) as e:
        logging.error("版本号比较失败: %s", e)
        return False


 #把字节数转换为 B、KB、MB 或 GB 等易读的文件大小
def format_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} TB"


#打开主界面
def start():
    from ypUI import YxPesticide
    from tkinter import Tk
    run_as_admin()
    setup_logging()
    root = Tk()
    app = YxPesticide(root)
    root.after(1200, lambda: app.update_program())
    root.mainloop()


if __name__ == "__main__":
    start()
