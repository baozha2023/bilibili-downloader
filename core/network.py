import requests
import logging
import time
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from fake_useragent import UserAgent

# 配置日志
logger = logging.getLogger('bilibili_core.network')

class NetworkManager:
    """
    负责网络请求、会话管理、代理和Headers
    """
    def __init__(self, use_proxy=False, cookies=None):
        # 使用fake_useragent生成随机User-Agent
        try:
            self.ua = UserAgent()
        except:
            self.ua = None
            logger.warning("无法初始化UserAgent，将使用默认User-Agent")
        
        self.headers = {
            'User-Agent': self._get_random_ua(),
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.bilibili.com'
        }
        
        # Cookie支持
        self.cookies = cookies
        
        # 代理设置
        self.use_proxy = use_proxy
        self.proxies = None
        if use_proxy:
            self.proxies = {
                'http': None, 
                'https': None
            }
        
        # 创建会话
        self.session = self._create_session()
        
        # 频率控制
        self.request_count = 0
        self.last_request_time = 0
    
    def _create_session(self):
        """创建会话对象，配置重试机制"""
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.timeout = (5, 30)
        return session
    
    def _get_random_ua(self):
        """获取随机User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except:
                pass
        
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        return random.choice(ua_list)
    
    def _update_proxies(self):
        """更新代理IP"""
        if not self.use_proxy:
            return
        logger.info("更新代理IP")
        # 实际逻辑待实现
    
    def _control_request_frequency(self):
        """控制请求频率"""
        current_time = time.time()
        if not hasattr(self, 'last_request_time'):
            self.last_request_time = current_time
            self.request_count = 1
            return
        
        time_diff = current_time - self.last_request_time
        if time_diff < 1.0 and self.request_count >= 2:
            wait_time = random.uniform(1.5, 3.0)
            logger.debug(f"请求过于频繁，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
            self.request_count = 1
        elif time_diff >= 1.0:
            self.request_count = 1
        else:
            self.request_count += 1
        self.last_request_time = time.time()
    
    def make_request(self, url, method='GET', params=None, data=None, stream=False, retry_count=0, max_retries=3, retry_delay=2):
        """发送HTTP请求"""
        self._control_request_frequency()
        
        if self.use_proxy and random.random() < 0.3:
            self._update_proxies()
        
        # 更新UA
        current_headers = self.headers.copy()
        current_headers['User-Agent'] = self._get_random_ua()
        
        kwargs = {
            'headers': current_headers,
            'cookies': self.cookies,
            'stream': stream
        }
        
        if params: kwargs['params'] = params
        if data: kwargs['data'] = data
        if self.use_proxy and self.proxies: kwargs['proxies'] = self.proxies
        
        logger.debug(f"发送{method}请求: {url}")
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(url, **kwargs)
            else:
                return None
            
            response.raise_for_status()
            
            # 如果是流式请求，直接返回响应对象
            if stream:
                return response
            
            # 尝试解析JSON
            try:
                json_data = response.json()
                if 'code' in json_data and json_data['code'] != 0:
                    error_msg = json_data.get('message', '未知错误')
                    logger.warning(f"API返回错误: {error_msg}，状态码: {json_data['code']}")
                    
                    # 特定错误码重试
                    if json_data['code'] in [412, 429] and retry_count < max_retries:
                        time.sleep(retry_delay * (2 ** retry_count))
                        return self.make_request(url, method, params, data, stream, retry_count + 1, max_retries, retry_delay)
                return json_data
            except ValueError:
                # 非JSON响应，返回原始内容或None
                return response.content
                
        except (requests.exceptions.RequestException) as e:
            logger.error(f"请求出错: {e}")
            if retry_count < max_retries:
                time.sleep(retry_delay * (2 ** retry_count))
                return self.make_request(url, method, params, data, stream, retry_count + 1, max_retries, retry_delay)
        
        return None
