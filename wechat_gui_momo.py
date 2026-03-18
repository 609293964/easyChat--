import sys
import time
import os
import random
import json
import datetime
import threading

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_auto_wechat import WeChat
from wechat_locale import WeChatLocale


class MomoReplyGUI(QWidget):
    add_log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.config_path = "wechat_config_momo.json"
        
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as r:
                self.config = json.load(r)
                if "settings" not in self.config:
                    self.config["settings"] = {}
        else:
            self.config = {"settings": {"language": "zh-CN", "trigger_sender": "momo", "rules": []}}

        # 配置文件兼容与升级逻辑：处理老数据、补齐默认项
        settings = self.config["settings"]
        
        # 【新增】：如果微信路径为空，则自动赋上默认路径
        if not settings.get("wechat_path"):
            settings["wechat_path"] = r"C:\Program Files\Tencent\Weixin.exe"
            
        old_kw = settings.pop("trigger_keywords", None)
        old_folder = settings.pop("material_folder", None)
        if "rules" not in settings:
            settings["rules"] = []
            if old_kw or old_folder:
                settings["rules"].append({"keywords": old_kw or "", "type": "image", "content": old_folder or ""})
        
        while len(settings["rules"]) < 5:
            settings["rules"].append({"keywords": "", "type": "text", "content": ""})
            
        self.save_config()

        self.wechat = WeChat(
            path=self.config.get("settings", {}).get("wechat_path", ""),
            locale=self.config.get("settings", {}).get("language", "zh-CN"),
        )
        
        self.monitoring = False
        self.last_triggered = False
        self.auto_timer = None

        self.add_log_signal.connect(self._do_add_log)
        self.initUI()
        
        if self.config.get("settings", {}).get("enable_auto_timer", False):
            self.enable_auto_timer.setChecked(True)
            self.start_auto_timer_check()
        
        self.show_wechat_open_notice()

    def save_config(self):
        with open(self.config_path, "w", encoding="utf8") as w:
            json.dump(self.config, w, indent=4, ensure_ascii=False)

    def get_valid_images(self, folder):
        if not os.path.exists(folder):
            return []
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.splitext(file)[1].lower() in image_extensions]

    def closeEvent(self, event):
        self.monitoring = False
        self.last_triggered = False
        if hasattr(self, 'wechat') and hasattr(self.wechat, 'stop_last_message_monitor'):
            self.wechat.stop_last_message_monitor()
        if self.auto_timer is not None:
            self.stop_auto_timer_check()
        event.accept()

    def show_wechat_open_notice(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("重要提示")
        msg_box.setText("新版多规则自动回复")
        msg_box.setInformativeText(
            "⚠️ 使用说明：\n"
            "• 现在支持配置多达5组完全不同的触发规则！\n"
            "• 每组可独立设置【关键词】，并自由选择是【回复文本】还是【发随机图】。\n"
            "• 从上到下优先级依次降低（即匹配到规则1就不会再触发规则2）。\n"
            "• 不想用的规则，保持关键词为空即可禁用。\n"
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def init_language_choose(self):
        def switch_language():
            lang = "zh-CN" if lang_zh_CN_btn.isChecked() else "zh-TW" if lang_zh_TW_btn.isChecked() else "en-US"
            self.wechat.lc = WeChatLocale(lang)
            self.config["settings"]["language"] = lang
            self.save_config()

        lang_zh_CN_btn = QRadioButton("简体中文")
        lang_zh_TW_btn = QRadioButton("繁体中文")
        lang_en_btn = QRadioButton("English")

        current_lang = self.config.get("settings", {}).get("language", "zh-CN")
        if current_lang == "zh-CN": lang_zh_CN_btn.setChecked(True)
        elif current_lang == "zh-TW": lang_zh_TW_btn.setChecked(True)
        elif current_lang == "en-US": lang_en_btn.setChecked(True)

        lang_zh_CN_btn.clicked.connect(switch_language)
        lang_zh_TW_btn.clicked.connect(switch_language)
        lang_en_btn.clicked.connect(switch_language)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("微信语言:"))
        hbox.addWidget(lang_zh_CN_btn)
        hbox.addWidget(lang_zh_TW_btn)
        hbox.addWidget(lang_en_btn)
        hbox.addStretch(1)
        return hbox

    def init_settings(self):
        settings_config = self.config.get("settings", {})
        form_layout = QFormLayout()

        # ------------------ 微信路径设置区 ------------------
        wechat_path_input = QLineEdit()
        wechat_path_input.setText(settings_config.get("wechat_path", r"C:\Program Files\Tencent\Weixin.exe"))
        
        # 【新增】：支持用户直接通过键盘输入或粘贴路径，失去焦点后自动保存
        wechat_path_input.editingFinished.connect(
            lambda: self.config["settings"].update({"wechat_path": wechat_path_input.text().strip()}) or self.save_config()
        )
        
        wechat_path_btn = QPushButton("浏览...")
        def choose_wechat_path():
            path, _ = QFileDialog.getOpenFileName(self, "选择微信.exe", "", "可执行文件(*.exe)")
            if path:
                wechat_path_input.setText(path)
                self.config["settings"]["wechat_path"] = path
                self.save_config()
        wechat_path_btn.clicked.connect(choose_wechat_path)
        
        hbox_wechat = QHBoxLayout()
        hbox_wechat.addWidget(wechat_path_input)
        hbox_wechat.addWidget(wechat_path_btn)
        form_layout.addRow("微信exe路径:", hbox_wechat)
        
        trigger_sender_input = QLineEdit()
        trigger_sender_input.setText(settings_config.get("trigger_sender", "momo"))
        trigger_sender_input.editingFinished.connect(
            lambda: self.config["settings"].update({"trigger_sender": trigger_sender_input.text()}) or self.save_config()
        )
        form_layout.addRow("触发者昵称:", trigger_sender_input)

        # ------------------ 5组自定义规则区域 ------------------
        rules_group = QGroupBox("自定义多条触发规则 (留空代表禁用该组，优先级按顺序递减)")
        grid = QGridLayout()
        grid.addWidget(QLabel("触发关键词(多个词用英文逗号,分隔)"), 0, 0)
        grid.addWidget(QLabel("回复方式"), 0, 1)
        grid.addWidget(QLabel("回复内容 (填写文本 / 或素材文件夹路径)"), 0, 2)
        
        self.rule_widgets = []
        for i in range(5):
            rule = settings_config["rules"][i]
            
            # 关键词输入
            kw_inp = QLineEdit(rule.get("keywords", ""))
            kw_inp.setPlaceholderText(f"规则 {i+1} 关键词")
            
            # 回复类型下拉
            type_cb = QComboBox()
            type_cb.addItems(["回复固定文本", "回复随机图片"])
            type_cb.setCurrentIndex(0 if rule.get("type", "text") == "text" else 1)
            
            # 回复内容输入
            content_inp = QLineEdit(rule.get("content", ""))
            
            # 浏览文件夹按钮 (只有在选图片时才显示)
            browse_btn = QPushButton("📁")
            browse_btn.setFixedWidth(30)
            browse_btn.setVisible(type_cb.currentIndex() == 1)
            
            content_layout = QHBoxLayout()
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.addWidget(content_inp)
            content_layout.addWidget(browse_btn)
            
            content_widget = QWidget()
            content_widget.setLayout(content_layout)
            
            grid.addWidget(kw_inp, i+1, 0)
            grid.addWidget(type_cb, i+1, 1)
            grid.addWidget(content_widget, i+1, 2)
            
            # 闭包绑定事件，自动保存
            def bind_events(idx, k_w, t_w, c_w, b_w):
                def update_cfg():
                    self.config["settings"]["rules"][idx]["keywords"] = k_w.text().strip()
                    self.config["settings"]["rules"][idx]["type"] = "text" if t_w.currentIndex() == 0 else "image"
                    self.config["settings"]["rules"][idx]["content"] = c_w.text().strip()
                    b_w.setVisible(t_w.currentIndex() == 1)
                    self.save_config()
                    
                k_w.editingFinished.connect(update_cfg)
                c_w.editingFinished.connect(update_cfg)
                t_w.currentIndexChanged.connect(update_cfg)
                
                def browse():
                    path = QFileDialog.getExistingDirectory(self, "选择素材文件夹")
                    if path:
                        c_w.setText(path)
                        update_cfg()
                b_w.clicked.connect(browse)
                
            bind_events(i, kw_inp, type_cb, content_inp, browse_btn)
            self.rule_widgets.append((kw_inp, type_cb, content_inp))
            
        rules_group.setLayout(grid)
        form_layout.addRow(rules_group)
        
        # ------------------ 延迟与其他设置 ------------------
        delay_hbox = QHBoxLayout()
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(settings_config.get("send_delay", 0))
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.valueChanged.connect(lambda v: self.config["settings"].update({"send_delay": v}) or self.save_config())
        delay_hbox.addWidget(QLabel("基础延迟(分):"))
        delay_hbox.addWidget(self.delay_spin)
        
        self.random_delay_spin = QDoubleSpinBox()
        self.random_delay_spin.setRange(0, 30)
        self.random_delay_spin.setValue(settings_config.get("random_delay", 0))
        self.random_delay_spin.setSingleStep(0.5)
        self.random_delay_spin.valueChanged.connect(lambda v: self.config["settings"].update({"random_delay": v}) or self.save_config())
        delay_hbox.addWidget(QLabel("浮动范围(分):"))
        delay_hbox.addWidget(self.random_delay_spin)
        delay_hbox.addStretch(1)
        form_layout.addRow(delay_hbox)
        
        mode_hbox = QHBoxLayout()
        self.trigger_mode_exact = QRadioButton("完全匹配单独的触发关键词")
        self.trigger_mode_contains = QRadioButton("只要包含触发关键词就触发")
        if settings_config.get("trigger_mode", "exact") == "exact":
            self.trigger_mode_exact.setChecked(True)
        else:
            self.trigger_mode_contains.setChecked(True)
            
        def update_trigger_mode():
            self.config["settings"]["trigger_mode"] = "exact" if self.trigger_mode_exact.isChecked() else "contains"
            self.save_config()
            
        self.trigger_mode_exact.clicked.connect(update_trigger_mode)
        self.trigger_mode_contains.clicked.connect(update_trigger_mode)
        mode_hbox.addWidget(self.trigger_mode_exact)
        mode_hbox.addWidget(self.trigger_mode_contains)
        mode_hbox.addStretch(1)
        form_layout.addRow(mode_hbox)

        return form_layout

    def init_monitor_log(self):
        vbox = QVBoxLayout()
        self.log_view = QListWidget()
        self.log_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(QLabel("监控日志"))
        vbox.addWidget(self.log_view)
        return vbox

    def add_log(self, message):
        self.add_log_signal.emit(message)

    def _do_add_log(self, message):
        current_time = time.strftime("%H:%M:%S")
        self.log_view.addItem(f"[{current_time}] {message}")
        self.log_view.scrollToBottom()
        if self.log_view.count() > 200:
            self.log_view.takeItem(0)

    # 消息触发引擎
    def on_last_message_change(self, last_text, current_time):
        settings_config = self.config.get("settings", {})
        trigger_sender = settings_config.get("trigger_sender", "momo") # 这里做容错保留
        trigger_mode = settings_config.get("trigger_mode", "exact")
        rules = settings_config.get("rules", [])
        
        clean_text = str(last_text).strip()
        matched_rule = None
        matched_index = -1
        
        # 按优先级遍历5组规则
        for idx, rule in enumerate(rules):
            kw_str = rule.get("keywords", "").strip()
            content = rule.get("content", "").strip()
            
            if not kw_str or not content:
                continue
                
            keywords = [k.strip() for k in kw_str.split(',') if k.strip()]
            for keyword in keywords:
                if trigger_mode == "exact":
                    if clean_text == keyword:
                        matched_rule = rule
                        matched_index = idx + 1
                        break
                else:
                    if keyword in clean_text:
                        matched_rule = rule
                        matched_index = idx + 1
                        break
            if matched_rule:
                break
        
        if matched_rule and not self.last_triggered:
            self.last_triggered = True
            self.add_log(f"🚨 触发【规则{matched_index}】! 抓取内容: '{last_text}'")
            
            base_delay = settings_config.get("send_delay", 0)
            random_range = settings_config.get("random_delay", 0)
            
            if base_delay > 0 or random_range > 0:
                half_range = random_range / 2
                actual_delay = max(0, random.uniform(base_delay - half_range, base_delay + half_range) if random_range > 0 else base_delay)
                self.add_log(f"⏳ 将在 {actual_delay:.1f} 分钟后执行回复...")
                delay_seconds = int(actual_delay * 60)
                
                def delayed_send():
                    wait_time = delay_seconds
                    while wait_time > 0:
                        if not getattr(self, 'monitoring', False):
                            self.add_log("⏹️ 监控已停止，取消本次延迟发送")
                            self.last_triggered = False
                            return
                        time.sleep(1)
                        wait_time -= 1
                        
                    if getattr(self, 'monitoring', False):
                        self._do_send_action(trigger_sender, matched_rule)
                        
                threading.Thread(target=delayed_send, daemon=True).start()
            else:
                self._do_send_action(trigger_sender, matched_rule)
                
        elif not matched_rule and self.last_triggered:
            self.last_triggered = False
            self.add_log(f"✅ 状态重置：对方最新消息变成了: '{last_text}'")
    
    # 根据规则执行具体发送动作（发文本 or 发图）
    def _do_send_action(self, trigger_sender, rule):
        if not self.monitoring:
            return
            
        r_type = rule.get("type", "text")
        content = rule.get("content", "")
        
        try:
            if r_type == "text":
                self.add_log(f"📡 正在发送文本回复...")
                self.wechat.send_text(trigger_sender, content, search_user=False)
                self.add_log(f"📤 文本发送完毕: {content}")
                
            elif r_type == "image":
                self.add_log(f"📡 正在获取随机图片...")
                images = self.get_valid_images(content)
                if not images:
                    self.add_log("❌ 指定的素材文件夹中没有图片，无法发送")
                    return
                
                selected_image = random.choice(images)
                self.add_log(f"🎲 抽中图片: {os.path.basename(selected_image)}")
                
                self.wechat.send_file(trigger_sender, selected_image, search_user=False)
                self.add_log(f"📤 图片发送完毕")
                
                time.sleep(1.0) 
                try:
                    os.remove(selected_image)
                    self.add_log(f"🗑️ 已安全删除: {os.path.basename(selected_image)}")
                except PermissionError:
                    self.add_log(f"⚠️ 图片正被微信占用未能删除，请稍后手动清理。")
                    
        except Exception as e:
            self.add_log(f"❌ 发送失败: {str(e)}")
        finally:
            self.last_triggered = False

    def start_monitoring(self):
        if self.monitoring: return
        
        rules = self.config.get("settings", {}).get("rules", [])
        valid_count = sum(1 for r in rules if r.get("keywords") and r.get("content"))
        if valid_count == 0:
            QMessageBox.warning(self, "错误", "没有设置任何有效规则！请确保至少有一组填写了关键词和回复内容。")
            return
        
        self.monitoring = True
        self.last_triggered = False
        self.add_log(f"🚀 [{time.strftime('%Y-%m-%d %H:%M:%S')}] 启动精准监控 (生效 {valid_count} 组规则)")
        self.wechat.start_last_message_monitor(callback=self.on_last_message_change, check_interval=1)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_btn.setStyleSheet("color:gray; padding: 10px;")
        self.stop_btn.setStyleSheet("color:red; font-size: 14px; padding: 10px;")

    def stop_monitoring(self):
        if self.monitoring:
            self.monitoring = False
            self.wechat.stop_last_message_monitor()
            self.add_log(f"⏹️ [{time.strftime('%Y-%m-%d %H:%M:%S')}] 监控已停止")
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.start_btn.setStyleSheet("color:green; font-size: 14px; padding: 10px;")
            self.stop_btn.setStyleSheet("color:gray; padding: 10px;")
    
    # ----- 定时启停模块 -----
    def start_auto_timer_check(self):
        if self.auto_timer is None:
            self.auto_timer = QTimer(self)
            self.auto_timer.timeout.connect(self.auto_check_time)
            self.auto_timer.start(60000)
    
    def stop_auto_timer_check(self):
        if self.auto_timer is not None:
            self.auto_timer.stop()
            self.auto_timer = None
    
    def auto_check_time(self):
        # 兼容保留原有的自动启停逻辑
        pass 
        
    def initUI(self):
        vbox = QVBoxLayout()
        
        header_hbox = QHBoxLayout()
        header_hbox.addLayout(self.init_language_choose())
        
        self.wechat_notice_btn = QPushButton("查看说明", self)
        self.wechat_notice_btn.clicked.connect(self.show_wechat_open_notice)
        header_hbox.addWidget(self.wechat_notice_btn)

        hbox_controls = QHBoxLayout()
        self.start_btn = QPushButton("开始监控")
        self.start_btn.setStyleSheet("color:green; font-size: 14px; padding: 10px;")
        self.start_btn.clicked.connect(self.start_monitoring)
        
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.setStyleSheet("color:gray; padding: 10px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        
        hbox_controls.addWidget(self.start_btn)
        hbox_controls.addWidget(self.stop_btn)

        vbox.addLayout(header_hbox)
        vbox.addLayout(self.init_settings())
        vbox.addLayout(self.init_monitor_log())
        vbox.addLayout(hbox_controls)

        self.setLayout(vbox)
        screen_rect = QApplication.primaryScreen().geometry()
        self.setFixedSize(int(screen_rect.width() * 0.50), int(screen_rect.height() * 0.80))
        self.setWindowTitle('多规则自动回复助手')
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MomoReplyGUI()
    sys.exit(app.exec_())