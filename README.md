# 番茄小说下载器

一个基于Flask的番茄小说下载工具，支持异步下载、断点续传、进度显示等功能。

## 功能特点

- 🚀 异步并发下载，提高下载速度
- 📥 支持断点续传，可随时暂停和继续下载
- 📊 实时显示下载进度
- 🔄 自动重试失败的章节
- 📝 自动格式化小说内容
- 🔒 支持官方API和备用API
- 📱 响应式Web界面
- 📋 支持下载小说信息（书名、作者、简介）

## 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/fanqie-novel-downloader.git
cd fanqie-novel-downloader
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行应用
```bash
python app.py
```

## 使用方法

1. 打开浏览器访问 `http://localhost:5000`
2. 在输入框中输入番茄小说ID（从小说页面URL中获取）
3. 点击"开始下载"按钮
4. 等待下载完成，然后点击"下载文件"获取小说文件

## 配置说明

在 `app.py` 中可以修改以下配置：

```python
CONFIG = {
    "max_workers": 20,  # 并发下载数
    "max_retries": 3,   # 最大重试次数
    "request_timeout": 15,  # 请求超时时间
    "chunk_size": 20,   # 每批处理的章节数
    # ... 其他配置
}
```

## 项目结构

```
fanqie-novel-downloader/
├── app.py              # 主程序
├── requirements.txt    # 依赖列表
├── templates/          # HTML模板
├── static/            # 静态文件
├── downloads/         # 下载文件存储目录
└── logs/             # 日志文件目录
```

## 注意事项

- 请合理使用，不要频繁请求
- 下载的小说仅供个人学习使用
- 请遵守番茄小说的使用条款
- 建议使用Python 3.7+版本

## 依赖库

- Flask
- aiohttp
- beautifulsoup4
- fake-useragent
- pycryptodome
- tqdm
- 其他依赖见 requirements.txt

## 许可证

本项目采用 GNU General Public License v3.0 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 免责声明

本项目仅供学习和研究使用，请勿用于商业用途。使用本项目产生的任何后果由使用者自行承担。 