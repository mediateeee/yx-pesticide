# -*- coding: utf-8 -*-
import os
import re
import logging
import subprocess
import ctypes
import sys
import hashlib
import time
import requests
import winreg
import threading
import tkinter as tk
from tkinter import Tk, Button, Label, messagebox, filedialog, ttk

CREATE_NO_WINDOW = 0x08000000
NO_PROXY = {"http": None, "https": None}
SHA256_IN_TEXT = re.compile(r"(?:sha-?256)[:\s=]+([a-fA-F0-9]{64})", re.IGNORECASE)

if getattr(sys, "frozen", False):
    PROGRAM_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(PROGRAM_DIR, "银杏杀虫软件.log")
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
DOWNLOAD_FILE = os.path.join(DESKTOP_DIR, "更新版本的银杏杀虫软件.exe")
GITEE_API_URL = "https://gitee.com/api/v5/repos/mediateeee/yx-pesticide/releases/latest"
UPDATE_ASSET_NAME = "yx-pesticide.exe"

VERSION = "26.8.22.0"

VIRUS_SIZE = 9376256
VIRUS_HEAD_HASH = "134f9b0d2a51fd14e9ebdcbc56d63e11"
HASH_READ_SIZE = 65536

KNOWN_VIRUS_EXES = {
    "windows explorer.exe",
    "system volume information.exe",
    ".exe",
}
ROAMING_COMPANION_FILES = ("360se_dump.db", "googlechrome.log")
RUN_VALUE_NAME = "Windows Explorer"
VIRUS_PROCESS_NAME = "Windows Explorer.exe"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("银杏杀虫软件 %s", VERSION)
    logging.info("程序路径: %s", PROGRAM_DIR)
    logging.info("Python 版本: %s", sys.version)
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        ) as key:
            product_name = winreg.QueryValueEx(key, "ProductName")[0]
            current_build = winreg.QueryValueEx(key, "CurrentBuild")[0]
        logging.info("Windows 详细版本: %s (Build %s)", product_name, current_build)
    except OSError as e:
        logging.debug("获取 Windows 详细版本失败: %s", e)
    logging.info("当前用户: %s", os.environ.get("USERNAME", "Unknown"))
    logging.info("计算机名: %s", os.environ.get("COMPUTERNAME", "Unknown"))
    logging.info("=" * 60)


def get_file_head_hash(file_path):
    try:
        if not os.path.isfile(file_path):
            return ""
        with open(file_path, "rb") as f:
            data = f.read(HASH_READ_SIZE)
        return hashlib.md5(data).hexdigest()
    except OSError as e:
        logging.debug("计算文件哈希失败 %s: %s", file_path, e)
        return ""


def sha256_file(file_path):
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def looks_like_pe(file_path):
    try:
        with open(file_path, "rb") as f:
            return f.read(2) == b"MZ"
    except OSError:
        return False


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def quote_arg(arg):
    if not arg:
        return '""'
    if any(ch in arg for ch in ' \t"'):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def run_as_admin():
    if is_admin():
        return
    if getattr(sys, "frozen", False):
        params = " ".join(quote_arg(a) for a in sys.argv[1:])
    else:
        params = " ".join(quote_arg(a) for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)


def sibling_folder_path(file_path):
    name = os.path.basename(file_path)
    stem, ext = os.path.splitext(name)
    if ext.lower() != ".exe" or not stem:
        return None
    folder_path = os.path.join(os.path.dirname(file_path), stem)
    if os.path.isdir(folder_path):
        return folder_path
    return None


def matches_virus_payload(file_path):
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return False
    if size != VIRUS_SIZE:
        return False
    return get_file_head_hash(file_path) == VIRUS_HEAD_HASH


def is_virus_file(file_path):
    """
    判定规则：
    1. 已知样本文件名（忽略大小写）：完整样本须哈希匹配；0 字节且旁有同名文件夹视为复制失败残留。
    2. 其它 .exe：必须同时有同名文件夹，且（哈希匹配，或 0 字节残留）。
    """
    try:
        if not os.path.isfile(file_path):
            return False
        name_l = os.path.basename(file_path).lower()
        if not name_l.endswith(".exe"):
            return False

        try:
            size = os.path.getsize(file_path)
        except OSError:
            return False

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

        if folder and matches_virus_payload(file_path):
            return True
        return False
    except OSError as e:
        logging.debug("检查文件失败 %s: %s", file_path, e)
        return False


def unhide_folder(folder_path):
    try:
        subprocess.run(
            ["attrib", "-h", "-s", folder_path],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
    except OSError as e:
        logging.debug("取消隐藏失败 %s: %s", folder_path, e)


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


def format_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} TB"


def parse_expected_sha256(text):
    if not text:
        return None
    match = SHA256_IN_TEXT.search(text)
    return match.group(1).lower() if match else None


def kill_virus_process():
    try:
        result = subprocess.run(
            ["taskkill", "/f", "/im", VIRUS_PROCESS_NAME],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            logging.info("已结束进程: %s", VIRUS_PROCESS_NAME)
            return True
        if result.returncode == 128:
            logging.info("%s 未运行，无需结束。", VIRUS_PROCESS_NAME)
            return False
        logging.error(
            "结束进程失败，返回码 %s: %s",
            result.returncode,
            (result.stderr or "").strip(),
        )
        return False
    except OSError as e:
        logging.error("检查进程时发生异常: %s", e)
        return False


def delete_run_value(value_name=RUN_VALUE_NAME):
    run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, value_name)
        logging.info("已删除启动项: HKCU\\...\\Run\\%s", value_name)
        return True
    except FileNotFoundError:
        logging.info("启动项不存在: %s", value_name)
        return False
    except OSError as e:
        logging.error("删除启动项失败: %s", e)
        return False


def safe_remove(path):
    try:
        os.remove(path)
        logging.info("已删除: %s", path)
        return True
    except FileNotFoundError:
        logging.info("文件不存在: %s", path)
        return False
    except OSError as e:
        logging.error("删除失败 %s: %s", path, e)
        return False


def find_roaming_virus_exes(roaming_dir):
    found = []
    try:
        for entry in os.listdir(roaming_dir):
            if entry.lower() not in KNOWN_VIRUS_EXES:
                continue
            full_path = os.path.join(roaming_dir, entry)
            if os.path.isfile(full_path) and is_virus_file(full_path):
                found.append(full_path)
    except OSError as e:
        logging.error("无法读取 Roaming 目录: %s", e)
    return found


def check_computer():
    confirm = messagebox.askokcancel(
        "检查电脑",
        "即将进行检查电脑功能！\n\n本功能将尝试检查并删除计算机中的病毒文件与启动项。\n\n是否继续？",
    )
    if not confirm:
        return

    try:
        actions = 0
        kill_virus_process()

        roaming_dir = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming")
        virus_exes = find_roaming_virus_exes(roaming_dir)
        for file_path in virus_exes:
            if clean_virus_file(file_path):
                actions += 1

        if virus_exes:
            for name in ROAMING_COMPANION_FILES:
                if safe_remove(os.path.join(roaming_dir, name)):
                    actions += 1
        else:
            logging.info("Roaming 下未发现符合特征的病毒本体，跳过附属文件删除。")

        if delete_run_value():
            actions += 1

        if actions > 0:
            messagebox.showinfo("完成", "发现病毒痕迹并已处理！\n\n日志文件：{}".format(LOG_FILE))
        else:
            messagebox.showinfo("完成", "未发现病毒。\n\n日志文件：{}".format(LOG_FILE))
    except Exception as e:
        logging.error("检查电脑失败: %s", e)
        messagebox.showerror("错误", f"操作失败: {e}")


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


def open_log_file():
    if not os.path.exists(LOG_FILE):
        messagebox.showerror("错误", f"日志文件不存在：\n{LOG_FILE}")
        return
    try:
        os.startfile(LOG_FILE)
        logging.info("已打开日志文件")
        return
    except OSError as e:
        logging.warning("直接打开日志失败: %s", e)
    try:
        subprocess.run(["notepad.exe", LOG_FILE], check=True, creationflags=CREATE_NO_WINDOW)
        logging.info("已使用记事本打开日志文件")
        return
    except (OSError, subprocess.CalledProcessError) as e:
        logging.error("记事本打开日志失败: %s", e)
    log_dir = os.path.dirname(LOG_FILE)
    try:
        os.startfile(log_dir)
        messagebox.showinfo("提示", f"无法打开日志文件，已打开所在目录：\n{log_dir}")
    except OSError as e:
        messagebox.showerror("错误", f"无法打开日志或目录：{e}")


def check_for_updates(parent=None):
    try:
        response = requests.get(GITEE_API_URL, timeout=10, proxies=NO_PROXY)
        if response.status_code != 200:
            logging.error("无法获取发布信息，状态码：%s", response.status_code)
            messagebox.showerror("检查更新失败", f"服务器响应错误：{response.status_code}", parent=parent)
            return None

        release_info = response.json()
        latest_version = release_info.get("tag_name", "")
        update_log = release_info.get("body", "暂无更新说明")

        if not compare_versions(VERSION, latest_version):
            logging.info("当前版本 %s 已是最新，无需更新", VERSION)
            messagebox.showinfo("检查更新", f"当前版本 {VERSION} 已是最新", parent=parent)
            return None

        download_url = None
        for asset in release_info.get("assets", []):
            if asset.get("name") == UPDATE_ASSET_NAME:
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            logging.error("没能找到更新文件的下载链接")
            messagebox.showerror("检查更新失败", "未找到更新文件下载链接", parent=parent)
            return None

        expected_sha256 = parse_expected_sha256(update_log)
        return latest_version, download_url, update_log, expected_sha256
    except Exception as e:
        logging.error("检查更新失败：%s", e)
        error_msg = str(e)
        if "ProxyError" in error_msg:
            msg = "检查更新失败\n\n网络代理错误，请检查网络连接后重试"
        elif "Timeout" in error_msg:
            msg = "检查更新失败\n\n连接超时，请检查网络后重试"
        elif "Connection" in error_msg:
            msg = "检查更新失败\n\n无法连接服务器，请检查网络后重试"
        else:
            msg = f"检查更新失败\n\n错误：{error_msg[:200]}\n\n请检查网络后重试"
        messagebox.showerror("检查更新失败", msg, parent=parent)
        return None


def verify_downloaded_update(file_path, expected_sha256=None):
    if not os.path.isfile(file_path) or os.path.getsize(file_path) < 1024:
        return False, "下载文件过小或损坏"
    if not looks_like_pe(file_path):
        return False, "下载文件不是有效的 Windows 程序"
    actual = sha256_file(file_path)
    logging.info("更新包 SHA256: %s", actual)
    if expected_sha256:
        if actual != expected_sha256:
            return False, "更新包校验失败，已删除不可信文件"
        logging.info("更新包 SHA256 与发布说明一致")
    else:
        logging.warning("发布说明中未找到 SHA256，仅校验了 PE 文件头")
    return True, actual


def download_update(download_url, parent=None, expected_sha256=None):
    download_window = None
    progress = None
    download_label = None
    temp_path = DOWNLOAD_FILE + ".part"

    try:
        download_window = tk.Toplevel(parent) if parent else tk.Toplevel()
        download_window.title("下载更新")
        download_window.geometry("400x150")
        if parent:
            download_window.transient(parent)
        download_window.grab_set()
        download_window.protocol("WM_DELETE_WINDOW", lambda: None)

        download_window.update_idletasks()
        width = download_window.winfo_width()
        height = download_window.winfo_height()
        x = (download_window.winfo_screenwidth() // 2) - (width // 2)
        y = (download_window.winfo_screenheight() // 2) - (height // 2)
        download_window.geometry(f"{width}x{height}+{x}+{y}")

        progress = ttk.Progressbar(download_window, orient="horizontal", length=300, mode="determinate")
        progress.pack(pady=10)
        download_label = tk.Label(download_window, text="正在连接服务器...", font=("微软雅黑", 12))
        download_label.pack(pady=10)
        download_window.update()

        response = requests.get(download_url, stream=True, timeout=30, proxies=NO_PROXY)
        if response.status_code != 200:
            download_label.config(text=f"下载失败，状态码：{response.status_code}")
            download_window.update()
            time.sleep(2)
            logging.error("下载失败，状态码：%s", response.status_code)
            return False

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()
        last_ui = 0

        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if now - last_ui < 0.1:
                    continue
                last_ui = now
                elapsed = max(now - start_time, 0.001)
                speed = (downloaded / elapsed) / 1024
                if total_size > 0:
                    percent = min((downloaded / total_size) * 100, 100)
                    progress["value"] = percent
                    download_label.config(
                        text=f"已下载: {format_size(downloaded)} / {format_size(total_size)}\n"
                        f"下载速度: {speed:.2f} KB/s\n"
                        f"进度: {percent:.1f}%"
                    )
                else:
                    download_label.config(
                        text=f"已下载: {format_size(downloaded)}\n下载速度: {speed:.2f} KB/s"
                    )
                download_window.update()

        ok, detail = verify_downloaded_update(temp_path, expected_sha256)
        if not ok:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            download_label.config(text=detail)
            download_window.update()
            time.sleep(2)
            logging.error("更新校验失败: %s", detail)
            return False

        os.replace(temp_path, DOWNLOAD_FILE)
        progress["value"] = 100
        download_label.config(text="下载完成！\n请稍后...")
        download_window.update()
        time.sleep(0.6)
        return True

    except requests.exceptions.Timeout:
        logging.error("下载超时")
        return False
    except requests.exceptions.ConnectionError:
        logging.error("网络连接失败")
        return False
    except Exception as e:
        logging.error("下载失败：%s", e)
        return False
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        if download_window is not None:
            try:
                if download_window.winfo_exists():
                    download_window.grab_release()
                    download_window.destroy()
            except tk.TclError:
                pass


def update_program(parent=None):
    update_info = check_for_updates(parent)
    if not update_info:
        return

    latest_version, download_url, update_log, expected_sha256 = update_info
    integrity_hint = (
        "发布说明含 SHA256，下载后将校验。"
        if expected_sha256
        else "发布说明未提供 SHA256，将只检查文件是否为有效程序。建议在发布说明中加入 SHA256: <64位哈希>。"
    )
    confirm = messagebox.askyesno(
        "检查到更新",
        f"当前版本: {VERSION}\n最新版本: {latest_version}\n\n"
        f"{integrity_hint}\n\n"
        "若点击下载后没反应，请查看桌面是否已有“更新版本的银杏杀虫软件.exe”，"
        "如有请先改名或删掉再试。\n\n"
        f"更新日志：\n{update_log}",
        parent=parent,
    )
    if not confirm:
        logging.info("用户取消更新。")
        return

    if download_update(download_url, parent=parent, expected_sha256=expected_sha256):
        messagebox.showinfo(
            "下载完毕",
            "下载完毕！新版应用程序已放置在桌面上，请使用新版并删除旧版。",
            parent=parent,
        )


class YxPesticide:
    def __init__(self, root):
        self.root = root
        self.root.title("银杏杀虫软件")
        self.root.geometry("600x650")

        self.welcome = Label(root, text="欢迎使用银杏杀虫软件 {}".format(VERSION), font=("微软雅黑", 28))
        self.welcome.pack(pady=10)

        self.choose = Label(root, text="请选择功能：", font=("微软雅黑", 16))
        self.choose.pack(pady=10)

        Button(root, text="检查电脑", command=check_computer, font=("微软雅黑", 14)).pack(pady=10)
        Button(root, text="扫描查杀", command=self.scan_and_clean, font=("微软雅黑", 14)).pack(pady=10)
        Button(root, text="关于病毒", command=show_about, font=("微软雅黑", 14)).pack(pady=10)
        Button(root, text="检查更新", command=lambda: update_program(self.root), font=("微软雅黑", 14)).pack(pady=10)
        Button(root, text="打开日志", command=open_log_file, font=("微软雅黑", 14)).pack(pady=10)

        Label(
            root,
            text="若您是第一次使用，请先进行“检查电脑”，再进行“扫描查杀”",
            font=("微软雅黑", 12),
        ).pack(pady=10)
        Label(root, text="有任何问题，欢迎联系：mediateeee@foxmail.com", font=("微软雅黑", 12)).pack(pady=10)
        Label(
            root,
            text="开放源代码：https://gitee.com/mediateeee/yx-pesticide",
            font=("微软雅黑", 12),
        ).pack(pady=10)

        self.scanning = False
        self.scan_stats = {"scanned": 0, "virus_found": 0}
        self.total_files = 0
        self.progress_window = None
        self.last_ui_update = 0

    def scan_and_clean(self):
        confirm = messagebox.askokcancel("扫描查杀", "请选择你要进行扫描的目录。\n\n是否继续？")
        if not confirm:
            return

        scan_path = filedialog.askdirectory(title="请选择你要进行扫描的目录。")
        if not scan_path:
            return
        if not os.path.isdir(scan_path):
            messagebox.showerror("错误", "选择的目录不存在！")
            return

        self.scan_stats = {"scanned": 0, "virus_found": 0}
        self.total_files = 0
        self.scanning = True
        self.show_progress()
        threading.Thread(target=self.scan_directory, args=(scan_path,), daemon=True).start()

    def show_progress(self):
        if self.progress_window is not None:
            try:
                self.progress_window.destroy()
            except tk.TclError:
                pass

        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("扫描进度")
        self.progress_window.geometry("450x180")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        self.progress_window.protocol("WM_DELETE_WINDOW", self.cancel_scanning)

        self.progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 180) // 2
        self.progress_window.geometry(f"450x180+{x}+{y}")

        tk.Label(self.progress_window, text="正在扫描...", font=("微软雅黑", 16, "bold")).pack(pady=10)
        self.progress_bar = ttk.Progressbar(
            self.progress_window, length=400, mode="indeterminate", orient="horizontal"
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar.start(10)

        self.progress_label = tk.Label(self.progress_window, text="正在准备扫描...", font=("微软雅黑", 11))
        self.progress_label.pack(pady=5)
        self.stats_label = tk.Label(
            self.progress_window,
            text="已扫描: 0 个文件 | 发现病毒: 0 个 | 进度: --",
            font=("微软雅黑", 9),
        )
        self.stats_label.pack(pady=5)
        tk.Button(
            self.progress_window,
            text="取消扫描",
            command=self.cancel_scanning,
            font=("微软雅黑", 10),
            width=12,
        ).pack(pady=5)

    def cancel_scanning(self):
        self.scanning = False
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_label.config(text="正在停止扫描...")
        logging.info("用户取消扫描")

    def update_progress(self, folder_path, scanned, virus_found):
        if not self.progress_window or not self.progress_window.winfo_exists():
            return
        folder_name = os.path.basename(folder_path) or folder_path
        self.progress_label.config(text=f"正在扫描: {folder_name}...")
        if self.total_files > 0:
            percent = min(round((scanned / self.total_files) * 100, 1), 100)
            self.progress_bar["value"] = percent
            percent_text = f"{percent}%"
        else:
            percent_text = "--"
        self.stats_label.config(
            text=f"已扫描: {scanned} 个文件 | 发现病毒: {virus_found} 个 | 进度: {percent_text}"
        )

    def count_files(self, root_path):
        total = 0
        stack = [root_path]
        while stack and self.scanning:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if not self.scanning:
                            break
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total += 1
                            elif entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                        except OSError:
                            continue
            except OSError:
                continue
        return total

    def scan_directory(self, scan_path):
        try:
            logging.info("开始扫描目录: %s", scan_path)
            self.root.after(0, lambda: self.progress_label.config(text="正在统计文件数量..."))
            self.total_files = self.count_files(scan_path)

            def switch_determinate():
                if self.progress_window and self.progress_window.winfo_exists():
                    self.progress_bar.stop()
                    self.progress_bar.config(mode="determinate", maximum=100, value=0)

            self.root.after(0, switch_determinate)

            scan_stack = [scan_path]
            while scan_stack and self.scanning:
                current_path = scan_stack.pop()
                try:
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            if not self.scanning:
                                break
                            try:
                                if entry.is_file(follow_symlinks=False):
                                    self.scan_stats["scanned"] += 1
                                    if is_virus_file(entry.path):
                                        self.scan_stats["virus_found"] += 1
                                        if clean_virus_file(entry.path):
                                            logging.info("发现并清理病毒文件: %s", entry.path)
                                    now = time.time()
                                    if now - self.last_ui_update >= 0.08:
                                        self.last_ui_update = now
                                        scanned = self.scan_stats["scanned"]
                                        found = self.scan_stats["virus_found"]
                                        folder = current_path
                                        self.root.after(
                                            0,
                                            lambda f=folder, s=scanned, v=found: self.update_progress(f, s, v),
                                        )
                                elif entry.is_dir(follow_symlinks=False):
                                    scan_stack.append(entry.path)
                            except OSError as e:
                                logging.debug("无法访问 %s: %s", entry.path, e)
                except OSError as e:
                    logging.warning("无法访问目录 %s: %s", current_path, e)

            self.finish_scan()
        except Exception as e:
            logging.error("扫描过程中发生错误: %s", e)
            self.root.after(0, lambda: self.show_error(f"扫描失败: {str(e)[:100]}"))

    def finish_scan(self):
        self.scanning = False

        def close_window():
            if self.progress_window and self.progress_window.winfo_exists():
                self.progress_bar.stop()
                self.progress_window.grab_release()
                self.progress_window.destroy()
            self.show_scan_result()

        self.root.after(0, close_window)

    def show_scan_result(self):
        scanned = self.scan_stats["scanned"]
        virus_found = self.scan_stats["virus_found"]
        if virus_found > 0:
            message = (
                f"扫描完成！\n\n共扫描文件: {scanned} 个\n"
                f"发现并清理病毒: {virus_found} 个\n\n详细日志：\n{LOG_FILE}"
            )
        else:
            message = (
                f"扫描完成！\n\n共扫描文件: {scanned} 个\n未发现病毒文件\n\n详细日志：\n{LOG_FILE}"
            )
        messagebox.showinfo("扫描完成", message)

    def show_error(self, error_msg):
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_bar.stop()
            self.progress_window.destroy()
        messagebox.showerror("扫描错误", error_msg)


if __name__ == "__main__":
    run_as_admin()
    setup_logging()
    root = Tk()
    app = YxPesticide(root)
    root.after(1200, lambda: update_program(app.root))
    root.mainloop()
