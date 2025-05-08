"""
番茄小说下载器 - Gunicorn 配置文件
Copyright (C) 2024 fanqie-novel-downloader

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import multiprocessing

# 绑定的IP和端口
bind = "0.0.0.0:5000"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "gevent"

# 超时时间
timeout = 300

# 最大请求数
max_requests = 1000
max_requests_jitter = 50

# 访问日志和错误日志
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 进程名称
proc_name = "tomato-novel-downloader"

# 守护进程模式
daemon = True

# 预加载应用
preload_app = True 