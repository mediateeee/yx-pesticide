import os
import winreg
import logging
import subprocess
import ctypes
import sys
import requests
import json
import shutil
from tkinter import Tk, Button, Label, messagebox, filedialog

# 获取程序运行目录
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROGRAM_DIR, 'Last-Yx-Pesticide.log')
UPDATER_LOG_FILE = os.path.join(PROGRAM_DIR, "updater.log")

# 动态获取主程序名称和路径
MAIN_PROGRAM_NAME = os.path.basename(sys.executable)  # 主程序文件名
MAIN_PROGRAM_PATH = sys.executable  # 主程序完整路径

# 临时下载路径
TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_download")
TEMP_DOWNLOAD_FILE = os.path.join(TEMP_DOWNLOAD_DIR, "yx-pesticide.exe")  # 下载的文件名

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # 输出到主日志文件
        logging.FileHandler(UPDATER_LOG_FILE),  # 输出到更新日志文件
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

class YxPesticide:
    def __init__(self, root):
        self.root = root
        self.root.title("银杏杀虫剂")
        self.root.geometry("600x500")

        # 界面组件
        self.welcome = Label(root, text="欢迎使用银杏杀虫剂", font=("Arial", 28))
        self.welcome.pack(pady=10)

        self.choose = Label(root, text="请选择功能：", font=("Arial", 16))
        self.choose.pack(pady=10)

        self.button_symlink = Button(root, text="设置防护", command=self.create_symlink, font=("Arial", 14))
        self.button_symlink.pack(pady=10)

        self.button_scan = Button(root, text="扫描查杀", command=self.scan_and_clean, font=("Arial", 14))
        self.button_scan.pack(pady=10)

        self.button_about = Button(root, text="关于病毒", command=self.show_about, font=("Arial", 14))
        self.button_about.pack(pady=10)

        self.button_update = Button(root, text="检查更新", command=update_program, font=("Arial", 14))
        self.button_update.pack(pady=10)

        self.about = Label(root, text="Made by mediateeee & DeepSeek. \n AIs actually changed the way we think and use tools, \n so what will the world be many yrs ago?", font=("Arial", 12))
        self.about.pack(pady=10)

        self.about = Label(root, text="A open-sourced project on Gitee.com/mediateeee/yx-pestiside", font=("Arial", 12))
        self.about.pack(pady=10)

    def create_symlink(self):
        """设置防护：创建符号链接、设置文件权限并清理注册表"""
        # 提示用户
        confirm = messagebox.askokcancel(
            "设置防护",
            "即将进行设置防护功能！\n\n设置防护将删除计算机中的病毒文件并保护你的计算机不被二次感染。\n\n是否继续？"
        )
        if not confirm:
            return

        try:
            # 1. 创建空文件 "%USERPROFILE%\AppData\Windows Explorer.exe"
            target_file = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Windows Explorer.exe')
            with open(target_file, 'w') as f:
                pass
            logging.info(f"已创建空文件: {target_file}")

            # 2. 创建符号链接
            source_file = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Windows Explorer.exe')
            if not os.path.exists(source_file):
                logging.warning(f"源文件不存在: {source_file}")
                return

            # 删除已存在的符号链接
            if os.path.exists(target_file):
                os.remove(target_file)

            # 创建符号链接
            subprocess.run(f'mklink "{target_file}" "{source_file}"', shell=True, check=True)
            logging.info(f"已创建符号链接: {target_file} -> {source_file}")

            # 3. 设置文件权限
            subprocess.run(f'icacls "{source_file}" /remove *S-1-1-0', shell=True, check=True)
            logging.info(f"已设置文件权限: {source_file}")

            # 4. 删除符号链接
            os.remove(target_file)
            logging.info(f"已删除符号链接: {target_file}")

            # 5. 扫描并清理注册表
            for startup_path in STARTUP_PATHS:
                self.scan_registry(startup_path)

            messagebox.showinfo("完成", f"设置防护完成！\n\nLOG文件已保存在：{LOG_FILE}")
        except Exception as e:
            logging.error(f"操作失败: {e}")
            messagebox.showerror("错误", f"操作失败: {e}")

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

    def scan_registry(self, startup_path):
        """扫描注册表启动项"""
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_path)
            for i in range(winreg.QueryInfoKey(reg_key)[1]):
                name, value, _ = winreg.EnumValue(reg_key, i)
                if self.is_virus_file(value):
                    logging.warning(f"发现病毒启动项: {name} - {value}")
                    self.delete_registry_value(reg_key, name)
            winreg.CloseKey(reg_key)
        except Exception as e:
            logging.error(f"扫描注册表失败: {startup_path} - {e}")

    def delete_registry_value(self, reg_key, value_name):
        """删除注册表值"""
        try:
            winreg.DeleteValue(reg_key, value_name)
            logging.info(f"已删除注册表值: {value_name}")
        except Exception as e:
            logging.error(f"删除注册表值失败: {value_name} - {e}")

    def show_about(self):
        """关于病毒：显示病毒信息"""
        about_text = """
        病毒名称：“文件夹病毒 Mincosoft Windows Explorer.exe”
        行为特征：
        1. 将U盘中的文件夹隐藏并替换为恶意可执行文件。
        2. 复制自身到系统目录（如 AppData\Roaming）。
        3. 修改注册表实现开机自启。
        4. 通过U盘传播。
        5. 看似不会危害计算机系统，但是恶心人。
        """
        messagebox.showinfo("关于病毒", about_text)

if __name__ == "__main__":
    # 检查是否以管理员身份运行
    run_as_admin()

    # 如果以管理员身份运行，启动主程序
    root = Tk()
    app = YxPesticide(root)
    root.mainloop()