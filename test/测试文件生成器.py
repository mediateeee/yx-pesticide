import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import string
import threading
import time
import subprocess 

# 文件类型配置（文件名后缀和模拟的文件特征）
FILE_TYPES = {
    "document": [".txt", ".docx", ".pdf", ".xlsx", ".pptx"],
    "executable": [".exe", ".msi", ".bat", ".cmd"],
    "mobile": [".apk", ".ipa"],
    "media": [".jpg", ".png", ".mp4", ".mp3"],
    "archive": [".zip", ".rar", ".7z"]
}

# 中文文件夹名称池（恢复原有中文）
FOLDER_NAMES = [
    "文档资料", "安装程序", "手机应用", "多媒体文件", "压缩包",
    "工作文件", "备份数据", "临时文件", "下载内容", "项目文件",
    "个人文件", "系统文件", "程序文件", "资源文件", "数据文件",
    "日志文件", "配置文件", "资产文件", "示例文件", "模板文件"
]

class FileGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件批量生成工具")
        self.root.geometry("650x420")
        self.root.resizable(False, False)
        
        # 初始化变量
        self.target_dir = tk.StringVar()
        self.total_size_str = tk.StringVar()
        self.total_size_bytes = 0
        self.generated_size = 0
        self.is_generating = False
        
        # 创建界面元素
        self.create_widgets()
    
    def create_widgets(self):
        # 1. 大小输入区域
        frame_size = ttk.LabelFrame(self.root, text="生成设置", padding="10")
        frame_size.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(frame_size, text="总生成大小（支持单位：B, KB, MB, GB）:").grid(row=0, column=0, sticky="w", pady=5)
        size_entry = ttk.Entry(frame_size, textvariable=self.total_size_str, width=30)
        size_entry.grid(row=0, column=1, padx=10, pady=5)
        ttk.Label(frame_size, text="示例：100MB 或 1GB").grid(row=0, column=2, sticky="w")
        
        # 2. 目录选择区域
        ttk.Label(frame_size, text="生成目录:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(frame_size, textvariable=self.target_dir, width=30).grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(frame_size, text="浏览", command=self.select_directory).grid(row=1, column=2)
        
        # 3. 操作按钮
        frame_buttons = ttk.Frame(self.root)
        frame_buttons.pack(pady=10)
        
        self.generate_btn = ttk.Button(frame_buttons, text="开始生成", command=self.start_generation)
        self.generate_btn.pack(side="left", padx=10)
        
        self.open_btn = ttk.Button(frame_buttons, text="打开目录", command=self.open_directory, state="disabled")
        self.open_btn.pack(side="left", padx=10)
        
        # 4. 进度条区域（精确模式，显示百分比）
        frame_progress = ttk.LabelFrame(self.root, text="生成进度", padding="10")
        frame_progress.pack(fill="x", padx=20, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            frame_progress, 
            variable=self.progress_var, 
            mode="determinate",  # 精确进度模式
            length=500,
            maximum=100  # 按百分比显示
        )
        self.progress_bar.pack(pady=5)
        
        # 进度百分比显示标签
        self.progress_label = ttk.Label(frame_progress, text="0%")
        self.progress_label.pack(pady=5)
        
        # 5. 状态提示
        self.status_label = ttk.Label(self.root, text="就绪", foreground="green")
        self.status_label.pack(pady=10)
    
    def select_directory(self):
        """选择生成文件的目标目录"""
        dir_path = filedialog.askdirectory(title="选择生成目录")
        if dir_path:
            self.target_dir.set(dir_path)
    
    def parse_size(self, size_str):
        """解析用户输入的大小字符串，转换为字节数"""
        size_str = size_str.strip().upper()
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
        
        try:
            # 提取数字和单位
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
            messagebox.showerror("错误", f"大小格式解析失败：{str(e)}\n请使用正确格式，如：100MB 或 1GB")
            return None
    
    def generate_random_name(self, length=8):
        """生成随机文件名/文件夹名"""
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for _ in range(length))
    
    def update_progress(self):
        """实时更新进度条和百分比显示"""
        if self.total_size_bytes > 0:
            # 计算已生成的百分比
            progress_percent = (self.generated_size / self.total_size_bytes) * 100
            # 确保进度不超过100%
            progress_percent = min(progress_percent, 100)
            self.progress_var.set(progress_percent)
            self.progress_label.config(text=f"{progress_percent:.1f}%")
    
    def create_random_file(self, base_path, file_size):
        """在指定路径创建指定大小的随机文件"""
        try:
            # 随机选择文件类型和后缀
            file_type = random.choice(list(FILE_TYPES.keys()))
            suffix = random.choice(FILE_TYPES[file_type])
            file_name = self.generate_random_name() + suffix
            file_path = os.path.join(base_path, file_name)
            
            # 生成指定大小的文件（分块写入，避免内存溢出）
            with open(file_path, 'wb') as f:
                chunk_size = 1024 * 1024  # 每次写入1MB
                remaining = file_size
                while remaining > 0 and self.is_generating:
                    write_size = min(chunk_size, remaining)
                    f.write(os.urandom(write_size))  # 写入随机字节
                    remaining -= write_size
                    self.generated_size += write_size
                    
                    # 实时更新进度（通过after确保UI线程安全）
                    self.root.after(0, self.update_progress)
            
            return True
        except Exception as e:
            print(f"创建文件失败：{e}")
            return False
    
    def create_folder_structure(self, base_path, depth=0, max_depth=3):
        """创建多层中文随机文件夹结构"""
        if depth >= max_depth:
            return base_path
        
        # 随机创建1-3个子文件夹
        num_folders = random.randint(1, 3)
        for _ in range(num_folders):
            # 中文文件夹名 + 4位随机字符（增强唯一性）
            folder_name = random.choice(FOLDER_NAMES) + "_" + self.generate_random_name(4)
            folder_path = os.path.join(base_path, folder_name)
            
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            
            # 递归创建子文件夹，形成多层结构
            self.create_folder_structure(folder_path, depth + 1, max_depth)
        
        return base_path
    
    def generate_files(self):
        """文件生成核心逻辑（在子线程执行）"""
        try:
            # 先创建多层文件夹结构
            self.create_folder_structure(self.target_dir.get())
            
            # 持续生成文件直到达到目标大小
            while self.generated_size < self.total_size_bytes and self.is_generating:
                # 收集所有可用文件夹，随机选择存放位置
                all_folders = []
                for root, dirs, _ in os.walk(self.target_dir.get()):
                    all_folders.extend([os.path.join(root, d) for d in dirs])
                
                # 若无子文件夹则使用根目录
                target_folder = random.choice(all_folders) if all_folders else self.target_dir.get()
                
                # 随机生成单个文件大小（100KB ~ 50MB），避免文件过大/过小
                file_size = random.randint(100 * 1024, 50 * 1024 * 1024)
                # 最后一个文件适配剩余大小，避免超出总目标
                remaining = self.total_size_bytes - self.generated_size
                if file_size > remaining:
                    file_size = remaining
                
                # 生成文件（确保还有剩余空间且生成未终止）
                if file_size > 0 and self.is_generating:
                    self.create_random_file(target_folder, file_size)
                
                # 短暂休眠，降低CPU占用
                time.sleep(0.01)
            
            # 生成完成，更新UI状态
            self.root.after(0, self.on_generation_complete)
        
        except Exception as e:
            # 捕获异常并提示用户
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成过程出错：{str(e)}"))
            self.root.after(0, self.on_generation_error)
    
    def start_generation(self):
        """启动文件生成流程"""
        # 输入验证
        if not self.target_dir.get():
            messagebox.showwarning("警告", "请先选择生成目录！")
            return
        
        self.total_size_bytes = self.parse_size(self.total_size_str.get())
        if self.total_size_bytes is None or self.total_size_bytes <= 0:
            return
        
        # 初始化生成状态
        self.is_generating = True
        self.generated_size = 0
        self.generate_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.status_label.config(text="正在生成文件...", foreground="blue")
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        
        # 启动子线程执行生成任务，避免UI卡死
        generate_thread = threading.Thread(target=self.generate_files)
        generate_thread.daemon = True  # 主线程退出时子线程自动终止
        generate_thread.start()
    
    def on_generation_complete(self):
        """生成完成后的UI更新"""
        self.is_generating = False
        self.progress_var.set(100)
        self.progress_label.config(text="100%")
        self.generate_btn.config(state="normal")
        self.open_btn.config(state="normal")
        # 显示实际生成大小（转换为MB更易读）
        generated_mb = self.generated_size / 1024 / 1024
        self.status_label.config(
            text=f"生成完成！实际生成大小：{generated_mb:.2f} MB",
            foreground="green"
        )
        messagebox.showinfo("完成", "文件生成完毕！")
    
    def on_generation_error(self):
        """生成出错后的UI更新"""
        self.is_generating = False
        self.generate_btn.config(state="normal")
        self.status_label.config(text="生成失败！", foreground="red")
    
    def open_directory(self):
        """打开生成目录（适配Windows系统）"""
        dir_path = self.target_dir.get()
        if os.path.exists(dir_path):
            try:
                # 调用Windows资源管理器打开目录
                subprocess.run(['explorer', dir_path], check=True)
            except Exception as e:
                messagebox.showerror("错误", f"打开目录失败：{str(e)}")
        else:
            messagebox.showwarning("警告", "目录不存在！")

def main():
    """程序主入口"""
    root = tk.Tk()
    app = FileGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    # Python 3.7版本检测
    import sys
    if sys.version_info < (3, 7 , 0):
        messagebox.showerror("版本错误", "请使用Python 3.7.0或更高版本运行此程序！")
    else:
        main()