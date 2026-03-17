import sys
import time
import os
import random
import json
import gc
import threading

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from ui_auto_wechat import WeChat

class MomoReplyGUI(QWidget):
    add_log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.config_path = "wechat_config_momo.json"
        
        # 读取或初始化配置
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as r:
                self.config = json.load(r)
        else:
            self.config = {
                "settings": {
                    "material_folder": "",
                    "target_window": "momo", # 默认窗口名称，可更改
                    "trigger_keywords": "!,！"
                }
            }
            self.save_config()

        self.wechat = WeChat()
        
        self.monitoring = False
        self.last_triggered = False
        
        # 绑定日志信号，确保线程安全
        self.add_log_signal.connect(self._do_add_log)
        self.initUI()

    def save_config(self):
        with open(self.config_path, "w", encoding="utf8") as w:
            json.dump(self.config, w, indent=4, ensure_ascii=False)

    def closeEvent(self, event):
        self.stop_monitoring()
        QApplication.quit()
        event.accept()

    def init_settings(self):
        form_layout = QFormLayout()

        # 1. 动态目标窗口选择
        self.target_window_input = QLineEdit()
        self.target_window_input.setText(self.config["settings"].get("target_window", "momo"))
        self.target_window_input.textChanged.connect(
            lambda: self.config["settings"].update({"target_window": self.target_window_input.text()}) or self.save_config()
        )
        form_layout.addRow("目标窗口/联系人名称:", self.target_window_input)

        # 2. 触发关键词
        self.trigger_keywords_input = QLineEdit()
        self.trigger_keywords_input.setText(self.config["settings"].get("trigger_keywords", "!,！"))
        self.trigger_keywords_input.textChanged.connect(
            lambda: self.config["settings"].update({"trigger_keywords": self.trigger_keywords_input.text()}) or self.save_config()
        )
        form_layout.addRow("触发关键词(用逗号分隔):", self.trigger_keywords_input)

        # 3. 素材文件夹
        self.material_folder_input = QLineEdit()
        self.material_folder_input.setText(self.config["settings"].get("material_folder", ""))
        folder_btn = QPushButton("浏览...")
        folder_btn.clicked.connect(self.choose_folder)
        
        hbox = QHBoxLayout()
        hbox.addWidget(self.material_folder_input)
        hbox.addWidget(folder_btn)
        form_layout.addRow("素材文件夹:", hbox)

        return form_layout

    def choose_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择素材文件夹")
        if folder_path:
            self.material_folder_input.setText(folder_path)
            self.config["settings"]["material_folder"] = folder_path
            self.save_config()

    def init_monitor_log(self):
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("监控日志"))
        self.log_view = QListWidget()
        vbox.addWidget(self.log_view)
        return vbox

    def add_log(self, message):
        self.add_log_signal.emit(message)

    def _do_add_log(self, message):
        current_time = time.strftime("%H:%M:%S")
        self.log_view.addItem(f"[{current_time}] {message}")
        self.log_view.scrollToBottom()
        if self.log_view.count() > 100:
            self.log_view.takeItem(0)

    # 核心监控逻辑
    def on_last_message_change(self, last_text, current_time):
        trigger_keywords = self.config["settings"].get("trigger_keywords", "!,！")
        keywords = [k.strip() for k in trigger_keywords.split(',') if k.strip()]
        
        clean_text = str(last_text).strip()
        triggered = any(kw in clean_text for kw in keywords)

        if triggered and not self.last_triggered:
            self.last_triggered = True
            self.add_log(f"🚨 触发警报！收到关键词: '{last_text}'")
            
            # 异步发送，避免阻塞监控主线程
            threading.Thread(target=self._do_send_image, daemon=True).start()
            
        elif not triggered and self.last_triggered:
            self.last_triggered = False
            self.add_log(f"✅ 警报解除：内容变为 '{last_text}'")

    def _do_send_image(self):
        folder = self.config["settings"].get("material_folder", "")
        target_window = self.config["settings"].get("target_window", "momo")
        
        if not os.path.exists(folder):
            self.add_log("❌ 素材文件夹不存在")
            self.last_triggered = False
            return
            
        images = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if not images:
            self.add_log("❌ 文件夹中无图片")
            self.last_triggered = False
            return

        selected_image = random.choice(images)
        try:
            # 向指定的目标窗口发送图片
            self.wechat.send_file(target_window, selected_image, search_user=False)
            self.add_log("📤 图片发送成功")
            
            # 彻底删除源图片，不留缓存
            os.remove(selected_image)
            self.add_log(f"🗑️ 已彻底删除原始图片，无缓存保留")
            
            # 强制内存垃圾回收，避免图片对象堆积
            gc.collect()
            
        except Exception as e:
            self.add_log(f"❌ 发送失败: {str(e)}")
        finally:
            self.last_triggered = False

    def start_monitoring(self):
        if self.monitoring: return
        self.add_log("🚀 启动监控 (检测间隔: 60秒)")
        self.last_triggered = False
        
        # 设定检测间隔为 60 秒（1分钟）
        self.wechat.start_last_message_monitor(callback=self.on_last_message_change, check_interval=60)
        
        self.monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_btn.setStyleSheet("color:gray")
        self.stop_btn.setStyleSheet("color:red")

    def stop_monitoring(self):
        if not self.monitoring: return
        self.wechat.stop_last_message_monitor()
        self.add_log("⏹️ 监控已停止")
        
        self.monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start_btn.setStyleSheet("color:green")
        self.stop_btn.setStyleSheet("color:gray")

    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addLayout(self.init_settings())
        vbox.addLayout(self.init_monitor_log())

        hbox = QHBoxLayout()
        self.start_btn = QPushButton("开始监控")
        self.start_btn.setStyleSheet("color:green; font-size: 14px; padding: 10px;")
        self.start_btn.clicked.connect(self.start_monitoring)
        
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.setStyleSheet("color:gray; padding: 10px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        
        hbox.addWidget(self.start_btn)
        hbox.addWidget(self.stop_btn)
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        self.setWindowTitle('自动回复助手')
        self.resize(500, 450)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MomoReplyGUI()
    sys.exit(app.exec_())