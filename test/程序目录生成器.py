import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import string
import threading
import time
import subprocess

# 程序类文件类型配置（重点突出exe，包含不同大小特征）
PROGRAM_FILE_TYPES = {
    # 小型可执行文件 (100KB - 5MB)
    "small_exe": [".exe", ".com", ".bat", ".cmd"],
    # 大型可执行文件 (50MB - 200MB)
    "large_exe": [".exe", ".msi", ".dll"],
    # 程序辅助文件
    "helper": [".ini", ".cfg", ".log", ".dat", ".xml"]
}

# 程序类中文目录名称池
PROGRAM_FOLDER_NAMES = [
    "主程序", "运行库", "插件", "依赖文件", "配置文件",
    "日志文件", "临时文件", "安装包", "升级包", "备份程序",
    "64位程序", "32位程序", "驱动程序", "服务程序", "工具程序",
    "核心模块", "扩展模块", "调试工具", "卸载程序", "启动程序"
]

# 文件大小配置（字节）
SIZE_CONFIG = {
    "small_exe_min": 100 * 1024,          # 100KB
    "small_exe_max": 5 * 1024 * 1024,     # 5MB
    "large_exe_min": 50 * 1024 * 1024,    # 50MB
    "large_exe_max": 200 * 1024 * 1024,   # 200MB
    "helper_min": 1 * 1024,               # 1KB
    "helper_max": 100 * 1024              # 100KB
}

class ProgramDirGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("程序目录生成工具")
        self.root.geometry("650x450")
        self.root.resizable(False, False)
        
        # 初始化变量
        self.target_dir = tk.StringVar()
        self.total_size_str = tk.StringVar(value="1GB")  # 默认1GB
        self.total_size_bytes = 0
        self.generated_size = 0
        self.is_generating = False
        
        # 创建界面
        self.create_ui()
    
    def create_ui(self):
        # 1. 基础设置区域
        frame_base = ttk.LabelFrame(self.root, text="生成设置", padding="15")
        frame_base.pack(fill="x", padx=20, pady=10)
        
        # 总大小设置
        ttk.Label(frame_base, text="总生成大小（支持B/KB/MB/GB）：").grid(row=0, column=0, sticky="w", pady=8)
        size_entry = ttk.Entry(frame_base, textvariable=self.total_size_str, width=25)
        size_entry.grid(row=0, column=1, padx=10, pady=8)
        ttk.Label(frame_base, text="示例：500MB / 2GB").grid(row=0, column=2, sticky="w")
        
        # 生成目录设置
        ttk.Label(frame_base, text="生成目标目录：").grid(row=1, column=0, sticky="w", pady=8)
        dir_entry = ttk.Entry(frame_base, textvariable=self.target_dir, width=25)
        dir_entry.grid(row=1, column=1, padx=10, pady=8)
        ttk.Button(frame_base, text="浏览", command=self.select_dir).grid(row=1, column=2)
        
        # 2. 操作按钮区域
        frame_btn = ttk.Frame(self.root)
        frame_btn.pack(pady=10)
        
        self.gen_btn = ttk.Button(frame_btn, text="开始生成程序目录", command=self.start_generation)
        self.gen_btn.pack(side="left", padx=10)
        
        self.open_btn = ttk.Button(frame_btn, text="打开生成目录", command=self.open_dir, state="disabled")
        self.open_btn.pack(side="left", padx=10)
        
        # 3. 进度展示区域
        frame_progress = ttk.LabelFrame(self.root, text="生成进度", padding="15")
        frame_progress.pack(fill="x", padx=20, pady=10)
        
        # 精确进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            frame_progress,
            variable=self.progress_var,
            mode="determinate",
            length=550,
            maximum=100
        )
        self.progress_bar.pack(pady=5)
        
        # 进度百分比+状态显示
        frame_progress_detail = ttk.Frame(frame_progress)
        frame_progress_detail.pack(fill="x", pady=5)
        
        self.progress_label = ttk.Label(frame_progress_detail, text="0%")
        self.progress_label.pack(side="left")
        
        self.status_label = ttk.Label(frame_progress_detail, text="就绪", foreground="green")
        self.status_label.pack(side="right")
    
    def select_dir(self):
        """选择生成目录"""
        dir_path = filedialog.askdirectory(title="选择程序目录生成位置")
        if dir_path:
            self.target_dir.set(dir_path)
    
    def parse_size(self, size_str):
        """解析大小字符串为字节"""
        size_str = size_str.strip().upper()
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
        
        try:
            num = ""
            unit = ""
            for char in size_str:
                if char.isdigit() or char == ".":
                    num += char
                else:
                    unit += char
            
            num = float(num)
            unit = unit.strip()
            
            if unit not in units:
                raise ValueError(f"不支持的单位：{unit}")
            
            return int(num * units[unit])
        except Exception as e:
            messagebox.showerror("错误", f"大小解析失败：{str(e)}\n请输入如 100MB、2GB 这样的格式")
            return None
    
    def gen_random_name(self, length=8):
        """生成随机文件名/文件夹名"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def update_progress(self):
        """更新进度条和状态"""
        if self.total_size_bytes > 0:
            percent = (self.generated_size / self.total_size_bytes) * 100
            percent = min(percent, 100)
            self.progress_var.set(percent)
            self.progress_label.config(text=f"{percent:.1f}%")
            # 显示已生成大小
            gen_mb = self.generated_size / 1024 / 1024
            total_mb = self.total_size_bytes / 1024 / 1024
            self.status_label.config(text=f"已生成：{gen_mb:.1f}MB / 总计：{total_mb:.1f}MB")
    
    def create_program_file(self, base_path, file_type):
        """创建指定类型的程序文件"""
        try:
            # 确定文件大小范围
            if file_type == "small_exe":
                size_min = SIZE_CONFIG["small_exe_min"]
                size_max = SIZE_CONFIG["small_exe_max"]
                suffixes = PROGRAM_FILE_TYPES["small_exe"]
            elif file_type == "large_exe":
                size_min = SIZE_CONFIG["large_exe_min"]
                size_max = SIZE_CONFIG["large_exe_max"]
                suffixes = PROGRAM_FILE_TYPES["large_exe"]
            else:
                size_min = SIZE_CONFIG["helper_min"]
                size_max = SIZE_CONFIG["helper_max"]
                suffixes = PROGRAM_FILE_TYPES["helper"]
            
            # 随机生成文件大小
            file_size = random.randint(size_min, size_max)
            # 确保不超过剩余大小
            remaining = self.total_size_bytes - self.generated_size
            if file_size > remaining:
                file_size = remaining
            if file_size <= 0:
                return False
            
            # 生成文件名
            suffix = random.choice(suffixes)
            # 程序文件命名更贴近真实（如 setup_8a7b.exe、core_9f8d.dll）
            if suffix == ".exe":
                prefixes = ["setup", "install", "main", "core", "tool", "update", "uninstall"]
                file_name = f"{random.choice(prefixes)}_{self.gen_random_name(4)}{suffix}"
            else:
                file_name = f"{self.gen_random_name()}{suffix}"
            
            file_path = os.path.join(base_path, file_name)
            
            # 分块写入随机数据
            with open(file_path, 'wb') as f:
                chunk_size = 1024 * 1024  # 1MB/块
                remaining_file = file_size
                while remaining_file > 0 and self.is_generating:
                    write_size = min(chunk_size, remaining_file)
                    f.write(os.urandom(write_size))
                    remaining_file -= write_size
                    self.generated_size += write_size
                    # 更新进度
                    self.root.after(0, self.update_progress)
            
            return True
        except Exception as e:
            print(f"创建文件失败：{e}")
            return False
    
    def create_program_dirs(self, base_path, depth=0, max_depth=4):
        """创建多层程序目录结构"""
        if depth >= max_depth or not self.is_generating:
            return base_path
        
        # 每层创建2-4个子目录
        num_dirs = random.randint(2, 4)
        for _ in range(num_dirs):
            dir_name = random.choice(PROGRAM_FOLDER_NAMES) + "_" + self.gen_random_name(4)
            dir_path = os.path.join(base_path, dir_name)
            
            if not os.path.exists(dir_path) and self.is_generating:
                os.makedirs(dir_path)
            
            # 递归创建子目录
            self.create_program_dirs(dir_path, depth + 1, max_depth)
        
        return base_path
    
    def generate_program_files(self):
        """生成程序文件核心逻辑"""
        try:
            # 先创建目录结构
            self.create_program_dirs(self.target_dir.get())
            
            # 收集所有生成的目录
            all_dirs = []
            for root, dirs, _ in os.walk(self.target_dir.get()):
                all_dirs.extend([os.path.join(root, d) for d in dirs])
            
            if not all_dirs:
                all_dirs.append(self.target_dir.get())
            
            # 按比例生成不同类型文件（70%大型exe，20%小型exe，10%辅助文件）
            file_type_weights = ["large_exe"]*7 + ["small_exe"]*2 + ["helper"]*1
            
            # 持续生成直到达到总大小
            while self.generated_size < self.total_size_bytes and self.is_generating:
                # 随机选择存放目录
                target_dir = random.choice(all_dirs)
                # 随机选择文件类型（按权重）
                file_type = random.choice(file_type_weights)
                
                # 创建文件
                self.create_program_file(target_dir, file_type)
                
                # 短暂休眠降低CPU占用
                time.sleep(0.01)
            
            # 生成完成
            self.root.after(0, self.on_complete)
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成失败：{str(e)}"))
            self.root.after(0, self.on_error)
    
    def start_generation(self):
        """启动生成流程"""
        # 验证输入
        if not self.target_dir.get():
            messagebox.showwarning("警告", "请先选择生成目录！")
            return
        
        self.total_size_bytes = self.parse_size(self.total_size_str.get())
        if self.total_size_bytes is None or self.total_size_bytes <= 0:
            return
        
        # 初始化状态
        self.is_generating = True
        self.generated_size = 0
        self.gen_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.status_label.config(text="正在生成程序目录...", foreground="blue")
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        
        # 启动子线程
        gen_thread = threading.Thread(target=self.generate_program_files)
        gen_thread.daemon = True
        gen_thread.start()
    
    def on_complete(self):
        """生成完成处理"""
        self.is_generating = False
        self.progress_var.set(100)
        self.progress_label.config(text="100%")
        self.gen_btn.config(state="normal")
        self.open_btn.config(state="normal")
        
        gen_gb = self.generated_size / 1024 / 1024 / 1024
        self.status_label.config(
            text=f"生成完成！总大小：{gen_gb:.2f}GB",
            foreground="green"
        )
        messagebox.showinfo("完成", "程序目录及文件生成完毕！")
    
    def on_error(self):
        """生成错误处理"""
        self.is_generating = False
        self.gen_btn.config(state="normal")
        self.status_label.config(text="生成失败！", foreground="red")
    
    def open_dir(self):
        """打开生成目录"""
        dir_path = self.target_dir.get()
        if os.path.exists(dir_path):
            try:
                subprocess.run(['explorer', dir_path], check=True)
            except Exception as e:
                messagebox.showerror("错误", f"打开目录失败：{str(e)}")
        else:
            messagebox.showwarning("警告", "目录不存在！")

def main():
    """主函数"""
    root = tk.Tk()
    app = ProgramDirGenerator(root)
    root.mainloop()

if __name__ == "__main__":
    # Python 3.7+版本检测
    import sys
    if sys.version_info < (3, 7, 0):
        messagebox.showerror("版本错误", "请使用Python 3.7.0或更高版本运行！")
    else:
        main()