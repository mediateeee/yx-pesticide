# -*- coding:utf-8 -*-
import hashlib
## 使用时更改VIRUS_FILE_PATH
VIRUS_FILE_PATH = r"C:\Users\MSI\Desktop\yx-pesticide\examples\Windows Explorer.exe"  # 病毒文件实际路径

HASH_READ_SIZE = 65536  # 前64KB

def get_file_head_hash(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read(HASH_READ_SIZE)
        md5_hash = hashlib.md5(data).hexdigest()
        print(f"病毒文件头部哈希（前64KB）：{md5_hash}")
        return md5_hash
    except Exception as e:
        print(f"计算失败：{e}")
        return ""

if __name__ == "__main__":
    get_file_head_hash(VIRUS_FILE_PATH)