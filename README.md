# 番茄小说下载器 Flask 版本

这是一个基于 [Tomato-Novel-Downloader-Lite](https://github.com/Dlmily/Tomato-Novel-Downloader-Lite) 项目修改的 Flask Web 应用版本。

## 项目说明

本项目是原始命令行工具的 Web 版本，提供了以下功能：

- 通过 Web 界面下载番茄小说
- 支持异步下载和进度跟踪
- 支持暂停/恢复下载
- 自动清理过期文件
- 完整的错误处理和日志系统

## 安装说明

1. 克隆项目：
```bash
git clone https://github.com/XY2006DATE/fanqie-novel-downloader.git
cd fanqie-novel-downloader
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行应用：
```bash
python app.py
```

或者使用 gunicorn（推荐用于生产环境）：
```bash
gunicorn -c gunicorn_config.py app:app
```

## 使用说明

1. 打开浏览器访问 `http://localhost:5000`
2. 输入番茄小说 ID（从小说详情页 URL 获取）
3. 点击下载按钮开始下载
4. 可以随时查看下载进度，暂停或恢复下载

## 注意事项

- 请确保遵守相关法律法规
- 下载的小说仅供个人阅读使用
- 请勿将下载的内容用于商业用途
- 请勿频繁请求，以免对服务器造成压力

## 许可证

本项目基于 GNU General Public License v3.0 许可证发布。

原始项目版权归 Dlmily 所有。
修改版本版权归 XY2006DATE 所有。

## 致谢

- 感谢 [Dlmily](https://github.com/Dlmily) 的原始项目
- 感谢所有 API 提供者
- 感谢所有贡献者

## 免责声明

本程序仅供学习交流使用，请勿用于任何商业用途。使用本程序产生的任何后果由使用者自行承担。 