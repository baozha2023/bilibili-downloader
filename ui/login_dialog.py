import sys
import os
import json
import time
import logging
import requests
import qrcode   
from io import BytesIO
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTabWidget, QCheckBox, 
                             QGroupBox, QMessageBox, QStackedWidget, QFileDialog, QGridLayout, QFrame)
from PyQt5.QtGui import QPixmap, QIcon, QImage, QPainter, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QSize, QPropertyAnimation, QEasingCurve, QRect

# 配置日志
logger = logging.getLogger('login_dialog')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class QRCodeLoginThread(QThread):
    """处理二维码登录的线程"""
    update_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.session = requests.Session()
        # 设置User-Agent防止412错误
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        })
        
    def run(self):
        try:
            # 获取二维码
            qr_data = self.get_login_qr()
            if not qr_data or 'data' not in qr_data:
                self.update_signal.emit({"status": "error", "message": "获取二维码失败，请检查网络连接"})
                return
            
            # 检查返回的状态码
            if qr_data.get('code') != 0:
                error_msg = qr_data.get('message', '未知错误')
                logger.error(f"获取二维码失败: {error_msg}")
                self.update_signal.emit({"status": "error", "message": f"获取二维码失败: {error_msg}"})
                return
                
            # 检查必要字段
            if 'data' not in qr_data or 'url' not in qr_data['data'] or 'qrcode_key' not in qr_data['data']:
                logger.error(f"二维码响应缺少必要字段: {qr_data}")
                self.update_signal.emit({"status": "error", "message": "获取二维码失败: 响应数据格式错误"})
                return

            qr_url = qr_data['data']['url']
            qr_key = qr_data['data']['qrcode_key']
            
            logger.info(f"获取到二维码URL: {qr_url[:30]}... 和二维码Key: {qr_key[:5]}...")
            
            # 生成二维码并通知主线程
            qr_img = self.generate_qr_code(qr_url)
            
            if qr_img is None:
                self.update_signal.emit({
                    "status": "error", 
                    "message": "生成二维码图像失败，请重试"
                })
                return
                
            self.update_signal.emit({
                "status": "qr_ready", 
                "message": "请使用哔哩哔哩APP扫描二维码登录", 
                "data": {"qr_img": qr_img, "qr_key": qr_key}
            })
            
            # 检查扫码状态
            check_interval = 2
            total_wait_time = 180  # 总等待时间，3分钟
            elapsed_time = 0
            
            while self.is_running and elapsed_time < total_wait_time:
                status = self.check_qr_status(qr_key)
                if not status:
                    # 检查状态失败，等待后重试
                    time.sleep(check_interval)
                    elapsed_time += check_interval
                    continue
                
                code = status.get('data', {}).get('code', 0)
                
                if code == 0:  # 已扫码并确认登录
                    cookies = self.session.cookies.get_dict()
                    self.update_signal.emit({
                        "status": "success", 
                        "message": "登录成功！", 
                        "data": {"cookies": cookies}
                    })
                    break
                elif code == 86038:  # 二维码已失效
                    self.update_signal.emit({
                        "status": "expired", 
                        "message": "二维码已失效，请重新获取"
                    })
                    break
                elif code == 86090:  # 已扫描，等待确认
                    self.update_signal.emit({
                        "status": "scanned", 
                        "message": "已扫描，请在手机上确认登录"
                    })
                elif code == 86101:  # 未扫描
                    # 已经显示过二维码，不需要再次通知
                    pass
                else:  # 其他状态
                    self.update_signal.emit({
                        "status": "waiting", 
                        "message": f"等待扫码，状态码: {code}"
                    })
                
                time.sleep(check_interval)
                elapsed_time += check_interval
            
            if elapsed_time >= total_wait_time:
                self.update_signal.emit({
                    "status": "timeout", 
                    "message": "二维码登录超时，请重试"
                })
                
        except Exception as e:
            logger.error(f"二维码登录出错：{str(e)}")
            self.update_signal.emit({
                "status": "error", 
                "message": f"登录过程出错: {str(e)}"
            })
    
    def stop(self):
        """停止线程"""
        self.is_running = False
        
    def get_login_qr(self):
        """获取登录二维码URL"""
        try:
            # 使用新版API
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
            logger.info(f"正在请求二维码URL: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"二维码URL获取成功: {result.get('code')}")
            return result
        except Exception as e:
            logger.error(f"获取登录二维码失败: {str(e)}")
            return None
            
    def check_qr_status(self, qr_key):
        """检查二维码扫描状态"""
        try:
            # 使用新版API
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
            params = {
                "qrcode_key": qr_key
            }
            logger.info(f"正在检查二维码状态: {url}, key={qr_key[:5]}...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            logger.info(f"二维码状态: code={result.get('data', {}).get('code', '未知')}")
            return result
        except Exception as e:
            logger.error(f"检查二维码状态失败: {str(e)}")
            return None
            
    def generate_qr_code(self, url):
        """生成二维码图片"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # 增大二维码尺寸以便于扫描
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 将PIL图像转换为QPixmap
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # 添加错误处理以防转换失败
            image_data = buffer.getvalue()
            if not image_data:
                logger.error("生成的二维码图像数据为空")
                return None
                
            image = QImage.fromData(image_data)
            if image.isNull():
                logger.error("QImage转换失败，图像为空")
                return None
                
            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                logger.error("QPixmap转换失败，图像为空")
                return None
                
            # 缩放以适应控件大小，保持清晰度
            # 确保图片是正方形，如果不是，进行裁剪或填充
            if pixmap.width() != pixmap.height():
                size = min(pixmap.width(), pixmap.height())
                pixmap = pixmap.copy(0, 0, size, size)
            
            if pixmap.width() > 350:
                pixmap = pixmap.scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
            logger.info(f"二维码生成成功，尺寸: {pixmap.width()}x{pixmap.height()}")
            return pixmap
        except Exception as e:
            logger.error(f"生成二维码时出错: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

class VIPCheckThread(QThread):
    """检查用户会员状态的线程"""
    update_signal = pyqtSignal(dict)
    
    def __init__(self, cookies):
        super().__init__()
        self.cookies = cookies
        
    def run(self):
        try:
            self.update_signal.emit({
                "status": "info", 
                "message": "正在检查会员状态..."
            })
            
            # 模拟检查会员状态
            time.sleep(1.5)
            
            # 这里实际应该调用B站API检查会员状态
            # 由于是演示，直接返回固定结果
            is_vip = False
            vip_type = 0
            vip_expire = 0
            
            # 判断是否是会员
            if "SESSDATA" in self.cookies and len(self.cookies["SESSDATA"]) > 10:
                # 演示: 随机判定是否为会员
                import random
                if random.random() > 0.5:
                    is_vip = True
                    vip_type = 2  # 年度大会员
                    vip_expire = int(time.time()) + 30 * 24 * 3600  # 30天后过期
            
            self.update_signal.emit({
                "status": "success", 
                "message": "会员状态检查完成", 
                "data": {
                    "is_vip": is_vip,
                    "vip_type": vip_type,
                    "vip_expire": vip_expire
                }
            })
            
        except Exception as e:
            logger.error(f"检查会员状态出错：{str(e)}")
            self.update_signal.emit({
                "status": "error", 
                "message": f"检查会员状态出错: {str(e)}"
            })

class BilibiliLoginWindow(QMainWindow):
    """B站登录窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # 保存用户信息
        self.user_info = None
        self.cookies = None
        self.qr_login_thread = None
        self.password_login_thread = None
        self.vip_check_thread = None
        
        # 登录完成信号（用于通知主窗口）
        self.finished_signal = None
        
        # 加载配置 - 统一使用 bilibili_data/config
        self.data_dir = 'bilibili_data'
        self.config_dir = os.path.join(self.data_dir, 'config')
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        self.config_file = os.path.join(self.config_dir, "login_config.json")
        self.load_config()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("哔哩哔哩账号登录")
        self.setMinimumSize(450, 600)
        self.setFixedSize(450, 600)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QGroupBox {
                border: none;
                font-weight: bold;
                color: #fb7299;
                font-size: 24px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QPushButton {
                border-radius: 20px;
                font-weight: bold;
                font-size: 23px;
                padding: 10px 20px;
            }
            QLabel {
                color: #333333;
                font-size: 22px;
            }
        """)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(25)
        
        # 顶部标题
        title_label = QLabel("扫码登录")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 34px; font-weight: bold; color: #fb7299;")
        main_layout.addWidget(title_label)
        
        # 二维码区域容器 (卡片式设计)
        qr_card = QFrame()
        qr_card.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 12px;
                border: 1px solid #eeeeee;
            }
        """)
        qr_card_layout = QVBoxLayout(qr_card)
        qr_card_layout.setContentsMargins(25, 25, 25, 25)
        
        # 二维码显示
        self.qr_label = QLabel("请点击获取二维码")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(220, 220)  # 保持正方形
        self.qr_label.setScaledContents(True)
        self.qr_label.setStyleSheet("background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px;")
        
        # 居中显示二维码
        qr_container = QHBoxLayout()
        qr_container.addStretch()
        qr_container.addWidget(self.qr_label)
        qr_container.addStretch()
        qr_card_layout.addLayout(qr_container)
        
        self.qr_status_label = QLabel("等待获取二维码...")
        self.qr_status_label.setAlignment(Qt.AlignCenter)
        self.qr_status_label.setStyleSheet("color: #666666; margin-top: 12px; font-size: 22px; border: none;")
        # 用户要求移除该组件显示，因为它挡住了二维码
        # qr_card_layout.addWidget(self.qr_status_label) 
        
        main_layout.addWidget(qr_card)
        
        # 操作说明
        self.info_text = QLabel("请使用哔哩哔哩APP扫码")
        self.info_text.setAlignment(Qt.AlignCenter)
        self.info_text.setStyleSheet("color: #333333; font-size: 22px; line-height: 1.6; font-weight: bold;")
        main_layout.addWidget(self.info_text)
        
        # 按钮区域
        button_layout = QVBoxLayout()
        button_layout.setSpacing(18)
        
        # 保存账号信息勾选框
        self.save_info_check = QCheckBox("保存账号信息(下次自动登录)")
        self.save_info_check.setChecked(True)
        self.save_info_check.setCursor(Qt.PointingHandCursor)
        self.save_info_check.setStyleSheet("""
            QCheckBox {
                color: #666666; 
                font-size: 22px;
            }
            QCheckBox::indicator {
                width: 24px;
                height: 24px;
            }
            QCheckBox::indicator:checked {
                image: url(resource/checkbox_checked.png);
            }
        """)
        # 由于可能没有自定义图标，这里先使用默认样式或者简单的颜色样式
        self.save_info_check.setStyleSheet("QCheckBox { color: #666666; font-size: 22px; }")
        button_layout.addWidget(self.save_info_check, alignment=Qt.AlignCenter)
        
        self.get_qr_btn = QPushButton("获取二维码")
        self.get_qr_btn.setCursor(Qt.PointingHandCursor)
        self.get_qr_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299; 
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.get_qr_btn.setFixedHeight(45)
        self.get_qr_btn.clicked.connect(self.start_qr_login)
        button_layout.addWidget(self.get_qr_btn)
        
        self.close_btn = QPushButton("取消")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0; 
                color: #666666;
                border: none;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        self.close_btn.setFixedHeight(45)
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        
        # 状态栏
        self.statusBar().hide() # 隐藏状态栏，使用自定义提示
        
    def start_qr_login(self):
        """开始二维码登录流程"""
        # 禁用按钮，防止重复操作
        self.get_qr_btn.setEnabled(False)
        self.get_qr_btn.setText("正在获取...")
        self.qr_status_label.setText("正在获取二维码...")
        
        # 如果有旧的线程，先停止
        if self.qr_login_thread and self.qr_login_thread.isRunning():
            self.qr_login_thread.stop()
            self.qr_login_thread.wait()
            
        # 创建并启动新线程
        self.qr_login_thread = QRCodeLoginThread()
        self.qr_login_thread.update_signal.connect(self.update_qr_status)
        self.qr_login_thread.start()
        
    def update_qr_status(self, data):
        """更新二维码状态"""
        status = data.get("status")
        message = data.get("message", "")
        
        # 更新状态文本
        # self.qr_status_label.setText(message)
        
        if status == "qr_ready":
            # 显示二维码
            qr_img = data.get("data", {}).get("qr_img")
            if qr_img and not qr_img.isNull():
                # 直接设置pixmap，不需要再次缩放，因为已经设置了setScaledContents(True)
                self.qr_label.setPixmap(qr_img)
                logger.info(f"已显示二维码，尺寸: {qr_img.width()}x{qr_img.height()}")
                self.get_qr_btn.setText("刷新二维码")
                self.info_text.setText("请使用哔哩哔哩APP扫码")
                self.info_text.setStyleSheet("color: #333333; font-size: 22px; line-height: 1.6; font-weight: bold;")
                
                # 添加简单的淡入动画效果 (模拟)
                self.qr_label.setGraphicsEffect(None) # 清除旧效果
            else:
                logger.error("二维码图像无效，无法显示")
                self.info_text.setText("获取二维码失败，请重试")
                self.info_text.setStyleSheet("color: #ff4d4f; font-size: 22px; line-height: 1.6;")
                self.get_qr_btn.setEnabled(True)
                self.get_qr_btn.setText("获取二维码")
        elif status == "scanned":
            # 二维码已扫描
            self.info_text.setText("已扫描，请在手机上确认登录")
            self.info_text.setStyleSheet("color: #1890ff; font-size: 22px; line-height: 1.6; font-weight: bold;")
        elif status == "success":
            # 登录成功
            self.info_text.setText("登录成功！")
            self.info_text.setStyleSheet("color: #52c41a; font-size: 24px; line-height: 1.6; font-weight: bold;")
            
            # 保存cookies
            self.cookies = data.get("data", {}).get("cookies", {})
            
            # 保存配置
            if self.cookies:
                if self.save_info_check.isChecked():
                    self.save_config()
                else:
                    self.clear_saved_config()
                
            # 通知主窗口登录状态变化
            if self.finished_signal:
                try:
                    self.finished_signal()
                except Exception as e:
                    logger.error(f"调用登录完成信号时出错: {str(e)}")
                    
            # 延迟一小段时间后关闭窗口，让用户看到成功提示
            QTimer.singleShot(1000, self.close)
        elif status == "expired":
            # 二维码过期
            self.info_text.setText("二维码已过期，请重新获取")
            self.info_text.setStyleSheet("color: #ff4d4f; font-size: 22px; line-height: 1.6;")
            self.get_qr_btn.setEnabled(True)
            self.get_qr_btn.setText("刷新二维码")
        elif status == "timeout":
            # 登录超时
            self.info_text.setText("登录超时，请重试")
            self.info_text.setStyleSheet("color: #ff4d4f; font-size: 22px; line-height: 1.6;")
            self.get_qr_btn.setEnabled(True)
            self.get_qr_btn.setText("刷新二维码")
        elif status == "error":
            # 登录出错
            self.info_text.setText(f"登录出错：{message}")
            self.info_text.setStyleSheet("color: #ff4d4f; font-size: 22px; line-height: 1.6;")
            self.get_qr_btn.setEnabled(True)
            self.get_qr_btn.setText("重试")
    
    def check_vip_status(self):
        """检查会员状态"""
        if not self.cookies:
            return
            
        # 创建并启动线程
        self.vip_check_thread = VIPCheckThread(self.cookies)
        self.vip_check_thread.update_signal.connect(self.update_vip_status)
        self.vip_check_thread.start()
        
    def update_vip_status(self, data):
        """更新会员状态"""
        # 这里保留方法结构，但实际上因为自动关闭，可能不会用到，或者仅用于后台更新
        pass

    def refresh_user_info(self):
        """刷新用户信息"""
        pass
            
    def logout(self):
        """注销登录"""
        pass
            
    def save_config(self):
        """保存配置"""
        if not self.cookies:
            return
            
        try:
            config = {
                "cookies": self.cookies,
                "timestamp": int(time.time())
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f)
                
            logger.info("配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")

    def clear_saved_config(self):
        """清除保存的配置"""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
                logger.info("已清除保存的配置")
        except Exception as e:
            logger.error(f"清除配置失败: {str(e)}")
            
    def load_config(self):
        """加载配置"""
        if not os.path.exists(self.config_file):
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            timestamp = config.get("timestamp", 0)
            current_time = int(time.time())
            
            # 检查配置是否过期 (30天)
            if current_time - timestamp > 30 * 24 * 3600:
                logger.info("配置已过期，需要重新登录")
                return
                
            # 加载cookies
            self.cookies = config.get("cookies", {})
            
            # 更新UI
            if self.cookies:
                self.refresh_user_info()
                self.check_vip_status()
                
            logger.info("配置已加载")
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            
    def get_cookies(self):
        """获取cookies，供外部调用"""
        return self.cookies
            
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止所有线程
        if self.qr_login_thread and self.qr_login_thread.isRunning():
            self.qr_login_thread.stop()
            self.qr_login_thread.wait()
            
        # 保存配置
        if self.cookies:
            self.save_config()
        
        # 通知主窗口登录状态变化
        if self.finished_signal:
            try:
                self.finished_signal()
            except Exception as e:
                logger.error(f"调用登录完成信号时出错: {str(e)}")
            
        event.accept()
