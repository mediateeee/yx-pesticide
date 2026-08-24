# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import time
import tkinter as tk
import requests
from tkinter import messagebox, ttk

from ypMAIN import (
    DOWNLOAD_FILE, GITEE_API_URL, NO_PROXY, VERSION,
    compare_versions, format_size, look_if_runnable
)

#检查更新功能
def check_for_updates(parent=None):
    try:
        response = requests.get(GITEE_API_URL, timeout=10, proxies=NO_PROXY)
        if response.status_code != 200:
            messagebox.showerror("检查更新失败", f"服务器响应错误：{response.status_code}", parent=parent)
            return None
        release_info = response.json()
        latest_version = release_info.get("tag_name", "")
        update_log = release_info.get("body", "暂无更新说明")
        if not compare_versions(VERSION, latest_version):
            logging.info("当前版本 %s 已是最新，无需更新", VERSION)
            messagebox.showinfo("检查更新", f"当前版本 {VERSION} 已是最新", parent=parent)
            return None
        download_url = next((asset.get("browser_download_url") for asset in release_info.get("assets", []) if asset.get("name") == "yx-pesticide.exe"), None)
        if not download_url:
            messagebox.showerror("检查更新失败", "未找到更新文件下载链接", parent=parent)
            return None
        return latest_version, download_url, update_log
    except Exception as e:
        logging.error("检查更新失败：%s", e)
        messagebox.showerror("检查更新失败", f"检查更新失败\n\n错误：{str(e)[:200]}\n\n请检查网络后重试", parent=parent)
        return None

#验证下载的更新文件
def verify_downloaded_update(file_path):
    if not os.path.isfile(file_path) or os.path.getsize(file_path) < 1024:
        return False, "下载文件过小或损坏"
    if not look_if_runnable(file_path):
        return False, "下载文件不是有效的 Windows 程序"
    return True, ""

#下载更新界面
def download_update(download_url, parent=None):
    window = None
    temp_path = DOWNLOAD_FILE + ".part"
    try:
        window = tk.Toplevel(parent) if parent else tk.Toplevel()
        window.title("下载更新")
        window.geometry("400x150")
        window.configure(bg="#eef3f1")
        if parent:
            window.transient(parent)
        window.grab_set()
        window.protocol("WM_DELETE_WINDOW", lambda: None)
        progress = ttk.Progressbar(window, orient="horizontal", length=300, mode="determinate")
        progress.pack(pady=10)
        label = tk.Label(window, text="正在连接服务器...", bg="#eef3f1", fg="#284b43", font=("微软雅黑", 12))
        label.pack(pady=10)
        window.update()
        response = requests.get(download_url, stream=True, timeout=30, proxies=NO_PROXY)
        if response.status_code != 200:
            return False
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()
        with open(temp_path, "wb") as output:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    output.write(chunk)
                    downloaded += len(chunk)
                    percent = min((downloaded / total_size) * 100, 100) if total_size else 0
                    progress["value"] = percent
                    speed = downloaded / max(time.time() - start_time, 0.001) / 1024
                    label.config(text=f"已下载: {format_size(downloaded)}\n下载速度: {speed:.2f} KB/s\n进度: {percent:.1f}%")
                    window.update()
        ok, detail = verify_downloaded_update(temp_path)
        if not ok:
            label.config(text=detail)
            window.update()
            time.sleep(2)
            return False
        os.replace(temp_path, DOWNLOAD_FILE)
        return True
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logging.error("下载失败: %s", e)
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
        if window is not None and window.winfo_exists():
            window.grab_release()
            window.destroy()

#更新程序界面
def update_program(parent=None):
    update_info = check_for_updates(parent)
    if not update_info:
        return
    latest_version, download_url, update_log = update_info
    confirm = messagebox.askyesno("检查到更新", f"当前版本: {VERSION}\n最新版本: {latest_version}\n\n更新日志：\n{update_log}", parent=parent)
    if confirm and download_update(download_url, parent):
        messagebox.showinfo("下载完毕", "下载完毕！新版应用程序已放置在桌面上，请使用新版并删除旧版。", parent=parent)
