"""
番茄小说下载器 Flask 版本
基于 Tomato-Novel-Downloader-Lite 项目修改

原始项目版权信息：
Copyright (C) 2024 Dlmily (Tomato-Novel-Downloader-Lite)

修改版本版权信息：
Copyright (C) 2025 XY2006DATE (fanqie-novel-downloader)

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

修改说明：
- 将原始命令行工具转换为 Flask Web 应用
- 添加了异步下载功能
- 添加了进度跟踪和任务管理
- 添加了文件管理和清理功能
- 添加了日志系统
- 优化了错误处理
- 添加了 Web 界面

修改日期：2025-05-08
修改作者：XY2006DATE
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import asyncio
import aiohttp
import aiofiles
from threading import Thread
from queue import Queue
import time
from typing import Optional, Dict, List
import requests
import bs4
import re
import random
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from fake_useragent import UserAgent
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
import gzip
from urllib.parse import urlencode
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建日志目录
if not os.path.exists('logs'):
    os.makedirs('logs')

# 配置文件日志处理器
file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024*1024, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# 禁用SSL证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()

app = Flask(__name__)

# 全局配置
CONFIG = {
    "max_workers": 20,  # 增加并发数
    "max_retries": 3,
    "request_timeout": 15,
    "status_file": "chapter.json",
    "request_rate_limit": 0,  # 降低请求间隔
    "chunk_size": 20,  # 每批处理的章节数
    "api_endpoints": [
        "https://api.cenguigui.cn/api/tomato/content.php?item_id={chapter_id}",
        "https://lsjk.zyii.xyz:3666/content?item_id={chapter_id}"
    ],
    "official_api": {
        "install_id": "4427064614339001",
        "server_device_id": "4427064614334905",
        "aid": "1967",
        "update_version_code": "62532"
    }
}

# 下载任务队列
download_tasks = {}
download_controls = {}  # 用于控制下载任务
download_progress = {}  # 用于存储下载进度

# 清理过期任务的时间间隔（秒）
CLEANUP_INTERVAL = 3600  # 1小时

def cleanup_old_tasks():
    """清理过期的下载任务"""
    current_time = time.time()
    expired_tasks = []
    
    for task_id, task in download_tasks.items():
        # 如果任务完成超过24小时，则删除
        if task.get('status') in ['completed', 'error'] and \
           current_time - task.get('created_at', 0) > 86400:  # 24小时
            expired_tasks.append(task_id)
    
    for task_id in expired_tasks:
        # 删除任务文件
        task = download_tasks[task_id]
        if 'file_path' in task and os.path.exists(task['file_path']):
            try:
                os.remove(task['file_path'])
            except Exception as e:
                logger.error(f"删除文件失败: {str(e)}")
        
        # 删除任务记录
        del download_tasks[task_id]

# 启动清理任务
def start_cleanup_task():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        cleanup_old_tasks()

cleanup_thread = Thread(target=start_cleanup_task, daemon=True)
cleanup_thread.start()

# 保持原有的FqCrypto和FqVariable类不变
okp = [
    "ac25", "c67d", "dd8f", "38c1", 
    "b37a", "2348", "828e", "222e"
]

def grk():
    return "".join(okp)

class FqCrypto:
    def __init__(self, key):
        self.key = bytes.fromhex(key)
        if len(self.key) != 16:
            raise ValueError(f"Key length mismatch! key: {self.key.hex()}")
        self.cipher_mode = AES.MODE_CBC

    def encrypt(self, data, iv):
        cipher = AES.new(self.key, self.cipher_mode, iv)
        ct_bytes = cipher.encrypt(pad(data, AES.block_size))
        return ct_bytes

    def decrypt(self, data):
        iv = data[:16]
        ct = data[16:]
        cipher = AES.new(self.key, self.cipher_mode, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt

    def new_register_key_content(self, server_device_id, str_val):
        if not str_val.isdigit() or not server_device_id.isdigit():
            raise ValueError(f"Parse failed\nserver_device_id: {server_device_id}\nstr_val:{str_val}")
        combined_bytes = int(server_device_id).to_bytes(8, byteorder='little') + int(str_val).to_bytes(8, byteorder='little')
        iv = get_random_bytes(16)
        enc_data = self.encrypt(combined_bytes, iv)
        combined_bytes = iv + enc_data
        return base64.b64encode(combined_bytes).decode('utf-8')

class FqVariable:
    def __init__(self, install_id, server_device_id, aid, update_version_code):
        self.install_id = install_id
        self.server_device_id = server_device_id
        self.aid = aid
        self.update_version_code = update_version_code

class FqReq:
    def __init__(self, var):
        self.var = var
        self.session = requests.Session()

    def batch_get(self, item_ids, download=False):
        headers = {
            "Cookie": f"install_id={self.var.install_id}"
        }
        url = "https://api5-normal-sinfonlineb.fqnovel.com/reading/reader/batch_full/v"
        params = {
            "item_ids": item_ids,
            "req_type": "0" if download else "1",
            "aid": self.var.aid,
            "update_version_code": self.var.update_version_code
        }
        response = self.session.get(url, headers=headers, params=params, verify=False)
        response.raise_for_status()
        ret_arr = response.json()
        return ret_arr

    def get_register_key(self):
        headers = {
            "Cookie": f"install_id={self.var.install_id}",
            "Content-Type": "application/json"
        }
        url = "https://api5-normal-sinfonlineb.fqnovel.com/reading/crypt/registerkey"
        params = {
            "aid": self.var.aid
        }
        crypto = FqCrypto(grk())
        payload = json.dumps({
            "content": crypto.new_register_key_content(self.var.server_device_id, "0"),
            "keyver": 1
        }).encode('utf-8')
        response = self.session.post(url, headers=headers, params=params, data=payload, verify=False)
        response.raise_for_status()
        ret_arr = response.json()
        key_str = ret_arr['data']['key']
        byte_key = crypto.decrypt(base64.b64decode(key_str))
        return byte_key.hex()

    def get_decrypt_contents(self, res_arr):
        key = self.get_register_key()
        crypto = FqCrypto(key)
        for item_id, content in res_arr['data'].items():
            byte_content = crypto.decrypt(base64.b64decode(content['content']))
            s = gzip.decompress(byte_content).decode('utf-8')
            res_arr['data'][item_id]['originContent'] = s
        return res_arr

    def __del__(self):
        self.session.close()

async def async_get_headers() -> Dict[str, str]:
    """异步生成随机请求头"""
    browsers = ['chrome', 'edge']
    browser = random.choice(browsers)
    
    if browser == 'chrome':
        user_agent = UserAgent().chrome
    else:
        user_agent = UserAgent().edge
    
    return {
        "User-Agent": user_agent,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://fanqienovel.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

async def async_down_text(session: aiohttp.ClientSession, chapter_id: str, headers: Dict[str, str], book_id: Optional[str] = None):
    """异步下载章节内容"""
    try:
        # 使用官方API
        var = FqVariable(
            CONFIG["official_api"]["install_id"],
            CONFIG["official_api"]["server_device_id"],
            CONFIG["official_api"]["aid"],
            CONFIG["official_api"]["update_version_code"]
        )
        client = FqReq(var)
        
        # 获取解密密钥
        key = client.get_register_key()
        crypto = FqCrypto(key)
        
        # 获取章节内容
        batch_res_arr = await asyncio.to_thread(client.batch_get, chapter_id, False)
        res = await asyncio.to_thread(client.get_decrypt_contents, batch_res_arr)
        
        for k, v in res['data'].items():
            content = v['originContent']
            chapter_title = v['title']
            
            # 处理标题和内容
            if chapter_title and re.match(r'^第[0-9]+章', chapter_title):
                chapter_title = re.sub(r'^第[0-9]+章\s*', '', chapter_title)
            
            content = re.sub(r'<header>.*?</header>', '', content, flags=re.DOTALL)
            content = re.sub(r'<footer>.*?</footer>', '', content, flags=re.DOTALL)
            content = re.sub(r'</?article>', '', content)
            content = re.sub(r'<p[^>]*>', '\n    ', content)
            content = re.sub(r'</p>', '', content)
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'\\u003c|\\u003e', '', content)
            
            if chapter_title and content.startswith(chapter_title):
                content = content[len(chapter_title):].lstrip()
            
            content = re.sub(r'\n{3,}', '\n\n', content).strip()
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            formatted_content = '\n'.join(['    ' + line for line in lines])
            
            return chapter_title, formatted_content
            
    except Exception as e:
        logger.error(f"官方API请求失败: {str(e)}")
        
        # 尝试备用API
        for api_endpoint in CONFIG["api_endpoints"]:
            try:
                url = api_endpoint.format(chapter_id=chapter_id)
                async with session.get(url, headers=headers, timeout=CONFIG["request_timeout"], ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("data", {}).get("content", "")
                        chapter_title = data.get("data", {}).get("title", "")
                        
                        if content:
                            # 处理内容
                            content = re.sub(r'<header>.*?</header>', '', content, flags=re.DOTALL)
                            content = re.sub(r'<footer>.*?</footer>', '', content, flags=re.DOTALL)
                            content = re.sub(r'</?article>', '', content)
                            content = re.sub(r'<p[^>]*>', '\n    ', content)
                            content = re.sub(r'</p>', '', content)
                            content = re.sub(r'<[^>]+>', '', content)
                            content = re.sub(r'\\u003c|\\u003e', '', content)
                            
                            if chapter_title and content.startswith(chapter_title):
                                content = content[len(chapter_title):].lstrip()
                            
                            content = re.sub(r'\n{3,}', '\n\n', content).strip()
                            lines = [line.strip() for line in content.split('\n') if line.strip()]
                            formatted_content = '\n'.join(['    ' + line for line in lines])
                            
                            return chapter_title, formatted_content
                            
            except Exception as e:
                logger.error(f"备用API请求失败: {str(e)}")
                continue
                
        return None, None

async def async_get_chapters(session: aiohttp.ClientSession, book_id: str, headers: Dict[str, str]) -> List[Dict]:
    """异步获取章节列表"""
    url = f"https://fanqienovel.com/api/reader/directory/detail?bookId={book_id}"
    try:
        async with session.get(url, headers=headers, timeout=CONFIG["request_timeout"], ssl=False) as response:
            if response.status != 200:
                return None
                
            data = await response.json()
            if data.get("code") != 0:
                return None
                
            chapters = []
            chapter_ids = data.get("data", {}).get("allItemIds", [])
            
            for idx, chapter_id in enumerate(chapter_ids):
                if not chapter_id:
                    continue
                    
                chapters.append({
                    "id": chapter_id,
                    "title": f"第{idx+1}章",
                    "index": idx
                })
            
            return chapters
            
    except Exception as e:
        logger.error(f"获取章节列表失败: {str(e)}")
        return None

async def async_get_book_info(session: aiohttp.ClientSession, book_id: str, headers: Dict[str, str]):
    """异步获取书籍信息"""
    url = f'https://fanqienovel.com/page/{book_id}'
    try:
        async with session.get(url, headers=headers, timeout=CONFIG["request_timeout"], ssl=False) as response:
            if response.status != 200:
                return None, None, None
                
            html = await response.text()
            soup = bs4.BeautifulSoup(html, 'html.parser')
            
            name = "未知书名"
            name_element = soup.find('h1')
            if name_element:
                name = name_element.text
            
            author_name = "未知作者"
            author_name_element = soup.find('div', class_='author-name')
            if author_name_element:
                author_name_span = author_name_element.find('span', class_='author-name-text')
                if author_name_span:
                    author_name = author_name_span.text
            
            description = "无简介"
            description_element = soup.find('div', class_='page-abstract-content')
            if description_element:
                description_p = description_element.find('p')
                if description_p:
                    description = description_p.text
            
            return name, author_name, description
            
    except Exception as e:
        logger.error(f"获取书籍信息失败: {str(e)}")
        return None, None, None

def stop_download(task_id: str):
    """停止下载任务"""
    if task_id in download_controls:
        download_controls[task_id]['stop'] = True
        logger.info(f"任务 {task_id} 已停止")
        return True
    return False

def save_progress(book_id: str, progress: dict):
    """保存下载进度"""
    progress_file = os.path.join('downloads', f"{book_id}_progress.json")
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存进度失败: {str(e)}")

def load_progress(book_id: str) -> dict:
    """加载下载进度"""
    progress_file = os.path.join('downloads', f"{book_id}_progress.json")
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                # 检查进度文件是否在24小时内
                if time.time() - progress.get('timestamp', 0) < 86400:  # 24小时
                    return progress
        except Exception as e:
            logger.error(f"加载进度失败: {str(e)}")
    return None

async def async_download_chapters(session: aiohttp.ClientSession, chapters: List[Dict], headers: Dict[str, str], 
                                output_file: str, task_id: str, book_id: str):
    """异步下载章节"""
    total_chapters = len(chapters)
    downloaded = 0
    
    # 加载之前的进度
    progress = load_progress(book_id)
    if progress:
        downloaded = progress.get('downloaded', 0)
        chapters = chapters[downloaded:]  # 跳过已下载的章节
        logger.info(f"从第 {downloaded + 1} 章继续下载")
    
    # 将章节分成多个批次
    for i in range(0, len(chapters), CONFIG["chunk_size"]):
        # 检查是否需要停止
        if task_id in download_controls and download_controls[task_id]['stop']:
            logger.info(f"任务 {task_id} 被用户停止")
            # 保存当前进度
            save_progress(book_id, {
                'downloaded': downloaded,
                'timestamp': time.time()
            })
            download_tasks[task_id].update({
                'status': 'stopped',
                'message': '下载已停止'
            })
            return
            
        chunk = chapters[i:i + CONFIG["chunk_size"]]
        tasks = []
        
        for chapter in chunk:
            task = asyncio.create_task(async_down_text(session, chapter["id"], headers))
            tasks.append((chapter, task))
        
        # 等待所有任务完成
        for chapter, task in tasks:
            try:
                chapter_title, content = await task
                if content:
                    async with aiofiles.open(output_file, 'a', encoding='utf-8') as f:
                        if chapter_title:
                            await f.write(f'{chapter["title"]} {chapter_title}\n')
                        else:
                            await f.write(f'{chapter["title"]}\n')
                        await f.write(content + '\n\n')
                    
                    downloaded += 1
                    progress = int((downloaded / total_chapters) * 100)
                    download_tasks[task_id].update({
                        'progress': progress,
                        'message': f'正在下载: {downloaded}/{total_chapters} 章'
                    })
                else:
                    logger.error(f"章节 {chapter['title']} 下载失败")
            except Exception as e:
                logger.error(f"处理章节失败: {str(e)}")

async def async_download_novel(book_id: str, task_id: str):
    """异步下载小说"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = await async_get_headers()
            
            # 获取章节列表
            chapters = await async_get_chapters(session, book_id, headers)
            if not chapters:
                download_tasks[task_id].update({
                    'status': 'error',
                    'message': '未找到任何章节，请检查小说ID是否正确。'
                })
                return
                
            # 获取书籍信息
            name, author_name, description = await async_get_book_info(session, book_id, headers)
            if not name:
                name = f"未知小说_{book_id}"
                author_name = "未知作者"
                description = "无简介"
            
            # 创建下载目录
            save_path = os.path.join('downloads', book_id)
            os.makedirs(save_path, exist_ok=True)
            
            # 准备下载
            output_file = os.path.join(save_path, f"{name}.txt")
            
            # 检查是否需要继续下载
            progress = load_progress(book_id)
            if not progress:
                # 写入书籍信息
                async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                    await f.write(f"小说名: {name}\n作者: {author_name}\n内容简介: {description}\n\n")
            
            # 下载章节
            await async_download_chapters(session, chapters, headers, output_file, task_id, book_id)
            
            # 更新任务状态
            if task_id in download_controls and download_controls[task_id]['stop']:
                return
                
            download_tasks[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': '下载完成',
                'file_path': output_file
            })
            
            # 下载完成后删除进度文件
            progress_file = os.path.join('downloads', f"{book_id}_progress.json")
            if os.path.exists(progress_file):
                os.remove(progress_file)
            
    except Exception as e:
        logger.error(f"下载小说失败: {str(e)}")
        download_tasks[task_id].update({
            'status': 'error',
            'message': f'下载出错: {str(e)}'
        })

def download_novel(book_id: str, task_id: str):
    """启动异步下载任务"""
    download_controls[task_id] = {'stop': False}
    asyncio.run(async_download_novel(book_id, task_id))

@app.route('/')
def home():
    return render_template('index.html', task=None)

@app.route('/start_download', methods=['POST'])
def start_download():
    book_id = request.form.get('book_id')
    if not book_id:
        return jsonify({'error': '请输入小说ID'}), 400
    
    # 创建下载任务
    task_id = str(int(time.time()))
    download_tasks[task_id] = {
        'status': 'running',
        'progress': 0,
        'message': '开始下载...',
        'book_id': book_id,
        'created_at': time.time()
    }
    
    # 启动下载线程
    thread = Thread(target=download_novel, args=(book_id, task_id))
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/download_status/<task_id>')
def download_status(task_id):
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(download_tasks[task_id])

@app.route('/download_file/<task_id>')
def download_file(task_id):
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = download_tasks[task_id]
    if task['status'] != 'completed':
        return jsonify({'error': '下载尚未完成'}), 400
    
    file_path = task.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='text/plain; charset=utf-8'
        )
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        return jsonify({'error': '文件下载失败'}), 500

@app.route('/stop_download/<task_id>', methods=['POST'])
def stop_download_route(task_id):
    """停止下载的路由"""
    if stop_download(task_id):
        return jsonify({'status': 'success', 'message': '下载已停止'})
    return jsonify({'status': 'error', 'message': '任务不存在'}), 404

@app.route('/resume_download/<task_id>', methods=['POST'])
def resume_download_route(task_id):
    """继续下载的路由"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
        
    task = download_tasks[task_id]
    if task['status'] != 'stopped':
        return jsonify({'error': '任务状态不正确'}), 400
        
    # 重新启动下载
    book_id = task['book_id']
    download_controls[task_id]['stop'] = False
    download_tasks[task_id].update({
        'status': 'running',
        'message': '继续下载...'
    })
    
    # 启动下载线程
    thread = Thread(target=download_novel, args=(book_id, task_id))
    thread.start()
    
    return jsonify({'status': 'success', 'message': '继续下载'})

@app.route('/download_partial/<task_id>')
def download_partial_file(task_id):
    """下载已完成章节的路由"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
        
    task = download_tasks[task_id]
    book_id = task['book_id']
    
    # 获取进度文件
    progress = load_progress(book_id)
    if not progress:
        return jsonify({'error': '未找到下载进度'}), 404
    
    # 获取已下载的文件
    save_path = os.path.join('downloads', book_id)
    if not os.path.exists(save_path):
        return jsonify({'error': '下载目录不存在'}), 404
        
    # 查找最新的txt文件
    txt_files = [f for f in os.listdir(save_path) if f.endswith('.txt')]
    if not txt_files:
        return jsonify({'error': '未找到下载文件'}), 404
        
    # 使用最新的文件
    file_path = os.path.join(save_path, txt_files[-1])
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='text/plain; charset=utf-8'
        )
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        return jsonify({'error': '文件下载失败'}), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs('downloads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=False) 