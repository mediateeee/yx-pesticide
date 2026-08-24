# -*- coding: utf-8 -*-
import logging
import os
import time
from tkinter import filedialog, messagebox
import threading

from ypMAIN import clean_virus_file, is_virus_file

#扫描目录获取大概信息
def scan_directory(controller, scan_path):
    try:
        logging.info("开始扫描目录: %s", scan_path)
        controller.root.after(0, lambda: controller.progress_label.config(text="正在统计文件数量..."))
        controller.total_files = count_files(controller, scan_path)
        controller.root.after(0, controller.switch_progress_mode)
        scan_stack = [scan_path]
        while scan_stack and controller.scanning:
            current_path = scan_stack.pop()
            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        if not controller.scanning:
                            break
                        try:
                            if entry.is_file(follow_symlinks=False):
                                controller.scan_stats["scanned"] += 1
                                if is_virus_file(entry.path):
                                    controller.scan_stats["virus_found"] += 1
                                    clean_virus_file(entry.path)
                                if time.time() - controller.last_ui_update >= 0.08:
                                    controller.last_ui_update = time.time()
                                    controller.queue_progress(current_path)
                            elif entry.is_dir(follow_symlinks=False):
                                scan_stack.append(entry.path)
                        except OSError as e:
                            logging.debug("无法访问 %s: %s", entry.path, e)
            except OSError as e:
                logging.warning("无法访问目录 %s: %s", current_path, e)
        controller.finish_scan()
    except Exception as e:
        logging.error("扫描过程中发生错误: %s", e)
        controller.root.after(0, lambda: controller.show_error(f"扫描失败: {str(e)[:100]}"))

#计算文件总数
def count_files(controller, root_path):
    total = 0
    stack = [root_path]
    while stack and controller.scanning:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if not controller.scanning:
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

#扫描查杀功能的界面
def choose_and_scan(controller):
    if not messagebox.askokcancel("扫描查杀", "请选择你要进行扫描的目录。\n\n是否继续？"):
        return
    scan_path = filedialog.askdirectory(title="请选择你要进行扫描的目录。")
    if not scan_path:
        return
    if not os.path.isdir(scan_path):
        messagebox.showerror("错误", "选择的目录不存在！")
        return
    controller.scan_stats = {"scanned": 0, "virus_found": 0}
    controller.total_files = 0
    controller.scanning = True
    controller.show_progress()
    threading.Thread(target=scan_directory, args=(controller, scan_path), daemon=True).start()
