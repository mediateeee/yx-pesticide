# 银杏杀虫剂
一款针对某种特定的文件夹病毒 **Windows Explorer.exe** 的查杀工具。

因大多数杀毒软件都不能很好地查杀这个病毒，故我根据已掌握的信息借助 AI 编写了这款工具。

## 运行原理
* 检查电脑

    结束已知病毒进程，校验并删除 `%AppData%\Roaming` 下的病毒本体及附属文件，清理注册表启动项。

* 扫描查杀

    扫描选定的目录。判定同时满足：

    1. 与同名隐藏文件夹配套的 `.exe`（或已知样本文件名）；
    2. 文件头部特征与已知样本一致（体积 + 头 64KB MD5），或 0 字节残留（U 盘空间不足时的残缺复制）。

* 检查更新

    使用 Gitee API 获取最新发布。下载后检查 PE 文件头；若发布说明中含 `SHA256: <64位哈希>`，还会校验完整文件。

## 目录结构
- yx-pesticide.py      - 主程序
- requirements.txt     - Python 依赖
- example              - 本软件所针对查杀的病毒样本说明
- test                 - 测试辅助工具
- version.txt          - 打包成 exe 时的版本信息（须与程序内 VERSION 一致）

## 运行与打包
为了适配 Windows7 ，软件是以 Python3.8.0 为基础编写的，理论上可以在>=3.8.0版本的 Python 上运行
```text
pip install -r requirements.txt
python yx-pesticide.py
```

打包命令见 `How to pyinstaller.txt`。

## 病毒信息
详见 `example` 文件夹。

## 问题反馈
本应用程序开发时间短，还有很多问题没有被考虑和解决。若在使用过程中发现问题，请提交 issue；如有必要请联系 mediateeee@foxmail.com
