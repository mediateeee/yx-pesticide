# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import winreg
from tkinter import messagebox

from ypMAIN import (
    CREATE_NO_WINDOW, KNOWN_VIRUS_EXES, LOG_FILE, ROAMING_COMPANION_FILES,
    RUN_VALUE_NAME, VIRUS_PROCESS_NAME, clean_virus_file, is_virus_file,
)

#结束病毒进程
def kill_virus_process():
    try:
        result = subprocess.run(["taskkill", "/f", "/im", VIRUS_PROCESS_NAME], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
        if result.returncode == 0:
            logging.info("已结束进程: %s", VIRUS_PROCESS_NAME)
            return True
        if result.returncode == 128:
            logging.info("%s 未运行，无需结束。", VIRUS_PROCESS_NAME)
            return False
        logging.error("结束进程失败，返回码 %s: %s", result.returncode, (result.stderr or "").strip())
        return False
    except OSError as e:
        logging.error("检查进程时发生异常: %s", e)
        return False

#删除病毒启动项
def delete_run_value(value_name=RUN_VALUE_NAME):
    run_keys = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM\\Wow6432Node"),
    )
    deleted = False
    for root_key, sub_key, location in run_keys:
        try:
            with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, value_name)
            logging.info("已删除启动项: %s\\Run\\%s", location, value_name)
            deleted = True
        except FileNotFoundError:
            logging.info("启动项不存在: %s\\Run\\%s", location, value_name)
        except OSError as e:
            logging.error("删除启动项失败 %s\\Run\\%s: %s", location, value_name, e)
    return deleted

#“安全的”删除某些文件
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

#查找 Roaming 目录下的已知病毒文件、伴随文件
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

#检查电脑功能的界面
def check_computer():
    if not messagebox.askokcancel("检查电脑", "即将进行检查电脑功能！\n\n本功能将尝试检查并删除计算机中的病毒文件与启动项。\n\n是否继续？"):
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
        if delete_run_value("HideFileExt"):
            actions += 1
        messagebox.showinfo("完成", ("发现病毒痕迹并已处理！" if actions else "未发现病毒。") + f"\n\n日志文件：{LOG_FILE}")
    except Exception as e:
        logging.error("检查电脑失败: %s", e)
        messagebox.showerror("错误", f"操作失败: {e}")
