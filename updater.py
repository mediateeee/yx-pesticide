import os
import requests
import json
import sys
import shutil
import logging  # 用于日志记录
from tkinter import Tk, messagebox  # 用于弹出提示框

# Gitee API 信息
GITEE_OWNER = "mediateeee"  # Gitee 用户名
GITEE_REPO = "yx-pesticide"  # 仓库名
GITEE_API_URL = f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/latest"

# 动态获取主程序名称和路径
MAIN_PROGRAM_NAME = os.path.basename(sys.executable)  # 主程序文件名
MAIN_PROGRAM_PATH = sys.executable  # 主程序完整路径

# 临时下载路径
TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_download")
TEMP_DOWNLOAD_FILE = os.path.join(TEMP_DOWNLOAD_DIR, "yx-pesticide.exe")  # 下载的文件名

# 日志文件路径
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last-updater.log")

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # 输出到文件
        logging.StreamHandler(sys.stdout)  # 输出到控制台
    ]
)

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
        assets = release_info.get("assets", [])

        # 查找可执行文件的下载链接
        download_url = None
        for asset in assets:
            if asset["name"] == "yx-pesiticide.exe":  # 检查文件名
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            logging.error("未找到可执行文件的下载链接")
            return None

        return latest_version, download_url
    except Exception as e:
        logging.error(f"检查更新失败：{e}")
        return None

def download_update(download_url):
    """下载最新版本"""
    try:
        # 创建临时下载目录
        if not os.path.exists(TEMP_DOWNLOAD_DIR):
            os.makedirs(TEMP_DOWNLOAD_DIR)

        # 下载文件
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            logging.error(f"下载失败，状态码：{response.status_code}")
            return False

        with open(TEMP_DOWNLOAD_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        logging.error(f"下载失败：{e}")
        return False

def apply_update():
    """应用更新"""
    try:
        # 删除旧版本程序
        if os.path.exists(MAIN_PROGRAM_PATH):
            os.remove(MAIN_PROGRAM_PATH)

        # 将下载的文件重命名为用户原来的文件名
        shutil.move(TEMP_DOWNLOAD_FILE, MAIN_PROGRAM_PATH)

        # 删除临时目录
        if os.path.exists(TEMP_DOWNLOAD_DIR):
            shutil.rmtree(TEMP_DOWNLOAD_DIR)

        logging.info("更新成功！请手动重启程序。")
        return True
    except Exception as e:
        logging.error(f"更新失败：{e}")
        return False

def update_program():
    """更新程序主逻辑"""
    # 检查更新
    update_info = check_for_updates()
    if not update_info:
        return

    latest_version, download_url = update_info

    # 弹出提示框询问用户是否更新
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    confirm = messagebox.askyesno("更新", f"发现新版本 {latest_version}，是否立即更新？")
    root.destroy()  # 关闭 Tk 窗口

    if not confirm:
        logging.info("用户取消更新。")
        return

    # 下载更新
    if not download_update(download_url):
        return

    # 应用更新
    if apply_update():
        # 提示用户手动重启
        root = Tk()
        root.withdraw()
        messagebox.showinfo("更新成功", "更新成功！请手动重启程序。")
        root.destroy()

if __name__ == "__main__":
    update_program()