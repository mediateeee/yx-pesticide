# -*- coding:utf-8 -*-
import os
import winreg
import logging
import subprocess
import ctypes
import sys
import requests
import json
import psutil
from tkinter import Tk, Button, Label, messagebox, filedialog

# 获取程序运行目录
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROGRAM_DIR, '我是主程序LOG.log')

# 定义应用程序版本
VERSION = '25.6.1.1'

# 下载路径
DOWNLOAD_FILE = os.path.join(PROGRAM_DIR, "更新版本的银杏杀虫剂.exe")  # 下载的文件

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
GITEE_OWNER = "mediateeee"  # Gitee 用户名
GITEE_REPO = "yx-pesticide"  # 仓库名
GITEE_API_URL = f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/latest"

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
    版本号格式为: 主版本号.次版本号.修订号.构建号 (例如: 25.3.16.7)
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

        return latest_version, download_url
    except Exception as e:
        logging.error(f"检查更新失败：{e}")
        return None

def download_update(download_url):
    """下载最新版本"""
    try:
        # 下载文件
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            logging.error(f"下载失败，状态码：{response.status_code}")
            return False

        with open(DOWNLOAD_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        logging.error(f"下载失败：{e}")
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
    confirm = messagebox.askyesno("检查到更新", 
                                f"当前版本: {VERSION}\n最新版本: {latest_version}\n\n是否立即更新？\n\n若选择更新，应用程序会提示“未响应”，请耐心等待，不要关闭应用程序。")
    root.destroy()  # 关闭 Tk 窗口

    if not confirm:
        logging.info("用户取消更新。")
        return

    # 下载更新
    if not download_update(download_url):
        return

    # 提示完成
    if download_update(download_url):
        # 提示用户手动重启
        root = Tk()
        root.withdraw()
        messagebox.showinfo("下载完毕", "下载完毕！新版应用程序已放置在本程序目录下，请使用新版应用程序并删除旧版。")
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
        self.root.geometry("600x650")

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

        self.about = Label(self.root, text="任何操作完成后都会提示“完成”，如果没有提示，那一定是出现了问题，\n此时请你将LOG文件发送与我，以供我进一步进行分析。", font=("微软雅黑", 12))
        self.about.pack(pady=10)

        self.about = Label(self.root, text="A open-sourced project on Gitee.com/mediateeee/yx-pestiside", font=("微软雅黑", 12))
        self.about.pack(pady=10)

    def check_computer(self):
        """设置防护：创建符号链接、设置文件权限并清理注册表"""
        # 提示用户
        confirm = messagebox.askokcancel(
            "检查电脑",
            "即将进行检查电脑功能！\n\n本功能将删除计算机中的病毒文件，因目前仍不能完全阻止病毒感染计算机，故只有删除的功能。如果你感觉计算机被感染了，可以尝试本功能。\n\n是否继续？"
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
        # 提示用户
        confirm = messagebox.askokcancel(
            "扫描查杀",
            "由于病毒仅感染移动存储设备（目前来看），请选择移动存储设备的根目录。\n\n是否继续？"
        )
        if not confirm:
            return

        # 弹出文件夹选择窗口，让用户选择磁盘根目录
        scan_path = filedialog.askdirectory(title="选择磁盘根目录")
        if not scan_path:
            return

        logging.info(f"正在扫描目录: {scan_path}")

        # 扫描文件系统
        if os.path.exists(scan_path):
            for root, dirs, files in os.walk(scan_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_folder_virus(file_path):
                        logging.info(f"发现病毒文件: {file_path}")
                        self.clean_folder_virus(file_path)

        target_file = os.path.join(scan_path, ".exe")
        if os.path.exists(target_file):
            try:
                os.remove(target_file)
                logging.info(f"已删除病毒文件: {target_file}")
                virus_found = True
            except Exception as e:
                logging.error(f"删除文件失败: {target_file} - {e}")
                messagebox.showerror("错误", f"无法删除文件 {target_file}\n错误信息: {e}")

        else:
            logging.warning(f"目录不存在: {scan_path}")

        messagebox.showinfo("完成", f"扫描和清理完成！\n\nLOG文件已保存在：{LOG_FILE}")

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
            return bool(os.stat(folder_path).st_file_attributes & HIDDEN_FOLDER_ATTRIB)
        except Exception as e:
            logging.error(f"检查隐藏文件夹失败: {folder_path} - {e}")
            return False

    def restore_hidden_folder(self, folder_path):
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
    #run_as_admin()

    # 如果以管理员身份运行，启动主程序
    root = Tk()
    app = YxPesticide(root)
    root.mainloop()