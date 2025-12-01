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
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0'
        ]
        return random.choice(ua_list)
    
    def make_request(self, url, method='GET', headers=None, params=None, data=None, stream=False):
        """发送网络请求"""
        self._control_request_frequency()
        
        # 动态更新User-Agent
        if not headers:
            headers = self.headers.copy()
        headers['User-Agent'] = self._get_random_ua()
        
        for retry in range(5):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, headers=headers, params=params, 
                        cookies=self.cookies, stream=stream, proxies=self.proxies,
                        timeout=(5, 30)
                    )
                else:
                    response = self.session.post(
                        url, headers=headers, params=params, data=data,
                        cookies=self.cookies, stream=stream, proxies=self.proxies,
                        timeout=(5, 30)
                    )
                
                response.raise_for_status()
                
                # 随机延迟
                time.sleep(random.uniform(0.2, 0.8))
                
                if stream:
                    return response
                
                # 尝试解析JSON
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return response.json()
                elif response.content.strip().startswith(b'{') and response.content.strip().endswith(b'}'):
                     try:
                         return response.json()
                     except:
                         pass
                
                return response.content
                
            except Exception as e:
                logger.warning(f"请求失败: {url}, 重试 {retry+1}/5. 错误: {e}")
                time.sleep(random.uniform(1, 3))
                
                # 每次重试更换UA
                headers['User-Agent'] = self._get_random_ua()
        
        logger.error(f"请求最终失败: {url}")
        return None
    
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
    

