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
    # [新增] 发送图片后实时更新UI信号，传参为被触发的规则索引
    update_img_count_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.config_path = "wechat_config_momo.json"
        
        default_material_folder = os.path.join(os.path.expanduser("~"), "Desktop", "素材")
        
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as r:
                self.config = json.load(r)
                if "settings" not in self.config:
                    self.config["settings"] = {}
                if "rules" not in self.config:
                    self.config["rules"] = []
        else:
            self.config = {
                "settings": {
                    "wechat_path": "",
                    "language": "zh-CN",
                    "trigger_sender": "momo",
                    "active_rules_count": 1
                },
                "rules": [
                    {"keywords": "!,！", "reply_type": "image", "folder": default_material_folder, "reply_text": "", "mode": "exact"}
                ]
            }
            self.save_config()

        while len(self.config.get("rules", [])) < 5:
            self.config["rules"].append({"keywords": "", "reply_type": "image", "folder": default_material_folder, "reply_text": "", "mode": "contains"})

        self.wechat = WeChat(
            path=self.config.get("settings", {}).get("wechat_path", ""),
            locale=self.config.get("settings", {}).get("language", "zh-CN"),
        )
        
        self.monitoring = False
        self.monitor_thread = None
        self.last_triggered = False
        self.auto_timer = None
        self.rule_img_count_labels = {} # 用于存储各个规则的图片数量Label引用

        self.add_log_signal.connect(self._do_add_log)
        self.update_img_count_signal.connect(self._do_update_img_count)
        
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
        images = []
        for file in os.listdir(folder):
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                images.append(os.path.join(folder, file))
        return images

    def closeEvent(self, event):
        if self.monitoring:
            self.stop_monitoring()
        if self.auto_timer is not None:
            self.stop_auto_timer_check()
        QApplication.quit()
        event.accept()

    def show_wechat_open_notice(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("重要提示")
        msg_box.setText("微信自动化操作说明")
        msg_box.setInformativeText(
            "⚠️ 使用说明：\n"
            "• 支持将聊天窗口单独拖出，只要填对【目标对话/触发者昵称】即可\n"
            "• 可自由选择回复类型：【发送素材图片】或【发送指定文本】\n"
            "• 图片发送后，会自动从文件夹中删除并实时刷新图片数量\n"
            "• 日志超长时会自动备份到本地并清理，避免卡死\n"
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def init_language_choose(self):
        def switch_language():
            if lang_zh_CN_btn.isChecked():
                self.wechat.lc = WeChatLocale("zh-CN")
                self.config["settings"]["language"] = "zh-CN"
            elif lang_zh_TW_btn.isChecked():
                self.wechat.lc = WeChatLocale("zh-TW")
                self.config["settings"]["language"] = "zh-TW"
            elif lang_en_btn.isChecked():
                self.wechat.lc = WeChatLocale("en-US")
                self.config["settings"]["language"] = "en-US"
            self.save_config()

        lang_group = QGroupBox("系统语言设置")
        lang_layout = QHBoxLayout()
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

        lang_layout.addWidget(lang_zh_CN_btn)
        lang_layout.addWidget(lang_zh_TW_btn)
        lang_layout.addWidget(lang_en_btn)
        lang_group.setLayout(lang_layout)
        return lang_group

    def init_settings(self):
        settings_config = self.config.get("settings", {})
        main_layout = QVBoxLayout()
        
        # --- 基础设置 ---
        base_group = QGroupBox("基础设置")
        base_layout = QFormLayout()
        wechat_path_input = QLineEdit(settings_config.get("wechat_path", ""))
        wechat_path_btn = QPushButton("浏览...")
        wechat_path_btn.clicked.connect(lambda: wechat_path_input.setText(QFileDialog.getOpenFileName(self, "选择微信.exe", "", "可执行文件(*.exe)")[0] or wechat_path_input.text()) or self.config["settings"].update({"wechat_path": wechat_path_input.text()}) or self.save_config())
        
        hbox_wechat = QHBoxLayout()
        hbox_wechat.addWidget(wechat_path_input)
        hbox_wechat.addWidget(wechat_path_btn)
        base_layout.addRow("微信exe路径:", hbox_wechat)

        trigger_sender_input = QLineEdit(settings_config.get("trigger_sender", "momo"))
        trigger_sender_input.setPlaceholderText("填入聊天窗口的名字(如: momo)")
        trigger_sender_input.editingFinished.connect(lambda: self.config["settings"].update({"trigger_sender": trigger_sender_input.text()}) or self.save_config())
        base_layout.addRow("目标对话/触发者昵称:", trigger_sender_input)
        base_group.setLayout(base_layout)
        main_layout.addWidget(base_group)

        # --- 多规则配置 ---
        rule_group = QGroupBox("触发与回复规则设置")
        rule_layout = QVBoxLayout()
        
        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("启用的规则数量 (1~5):"))
        self.rule_count_combo = QComboBox()
        self.rule_count_combo.addItems(["1", "2", "3", "4", "5"])
        self.rule_count_combo.setCurrentIndex(settings_config.get("active_rules_count", 1) - 1)
        combo_layout.addWidget(self.rule_count_combo)
        combo_layout.addStretch()
        rule_layout.addLayout(combo_layout)

        self.rules_tabs = QTabWidget()
        self.rule_img_count_labels = {} # 字典，用于索引每个 Tab 的数量Label
        
        for i in range(5):
            tab = QWidget()
            tab_layout = QFormLayout()
            rule_data = self.config["rules"][i]

            kw_input = QLineEdit(rule_data.get("keywords", ""))
            kw_input.setPlaceholderText("用英文逗号分隔，例如: !,！")
            kw_input.editingFinished.connect(lambda idx=i, edit=kw_input: self.config["rules"][idx].update({"keywords": edit.text()}) or self.save_config())
            tab_layout.addRow("触发关键词:", kw_input)
            
            # [新增] 回复类型下拉框
            type_combo = QComboBox()
            type_combo.addItems(["发送素材图片", "发送指定文本"])
            
            # 图片设置组件
            folder_w = QWidget()
            folder_layout = QHBoxLayout(folder_w)
            folder_layout.setContentsMargins(0,0,0,0)
            folder_input = QLineEdit(rule_data.get("folder", ""))
            folder_btn = QPushButton("浏览...")
            folder_layout.addWidget(folder_input)
            folder_layout.addWidget(folder_btn)
            folder_info = QLabel("图片数量: 0")
            self.rule_img_count_labels[i] = folder_info  # 绑定记录
            
            # 文本设置组件
            text_w = QWidget()
            text_layout = QHBoxLayout(text_w)
            text_layout.setContentsMargins(0,0,0,0)
            text_input = QLineEdit(rule_data.get("reply_text", ""))
            text_input.setPlaceholderText("填入触发后需要回复的文本内容")
            text_layout.addWidget(text_input)

            tab_layout.addRow("回复类型:", type_combo)
            tab_layout.addRow("图片目录:", folder_w)
            tab_layout.addRow("", folder_info)
            tab_layout.addRow("回复文本:", text_w)
            
            # 逻辑函数
            def update_visibility(idx, cb, fw, cl, tw):
                is_img = cb.currentIndex() == 0
                fw.setVisible(is_img)
                cl.setVisible(is_img)
                tw.setVisible(not is_img)
                self.config["rules"][idx]["reply_type"] = "image" if is_img else "text"
                self.save_config()

            def make_folder_browser(idx, f_input, f_info):
                def browse():
                    d = QFileDialog.getExistingDirectory(self, f"选择规则 {idx+1} 的素材")
                    if d:
                        f_input.setText(d)
                        self.config["rules"][idx]["folder"] = d
                        self.save_config()
                        imgs = self.get_valid_images(d)
                        f_info.setText(f"图片数量: {len(imgs)}")
                return browse

            def update_count(idx, f_input, f_info):
                self.config["rules"][idx]["folder"] = f_input.text()
                self.save_config()
                imgs = self.get_valid_images(f_input.text())
                f_info.setText(f"图片数量: {len(imgs)}")
                
            def update_text(idx, edit):
                self.config["rules"][idx]["reply_text"] = edit.text()
                self.save_config()
            
            # 信号连接
            type_combo.currentIndexChanged.connect(lambda _, idx=i, cb=type_combo, fw=folder_w, cl=folder_info, tw=text_w: update_visibility(idx, cb, fw, cl, tw))
            folder_btn.clicked.connect(make_folder_browser(i, folder_input, folder_info))
            folder_input.editingFinished.connect(lambda idx=i, f_in=folder_input, f_inf=folder_info: update_count(idx, f_in, f_inf))
            text_input.editingFinished.connect(lambda idx=i, edit=text_input: update_text(idx, edit))
            
            # 初始状态渲染
            curr_type = rule_data.get("reply_type", "image")
            type_combo.setCurrentIndex(0 if curr_type == "image" else 1)
            update_visibility(i, type_combo, folder_w, folder_info, text_w)
            update_count(i, folder_input, folder_info)

            # 匹配模式
            mode_layout = QHBoxLayout()
            rb_exact = QRadioButton("只匹配单独关键词(精确)")
            rb_contains = QRadioButton("包含关键词即可触发(模糊)")
            if rule_data.get("mode", "exact") == "exact": rb_exact.setChecked(True)
            else: rb_contains.setChecked(True)
            def update_mode(idx, exact_btn):
                self.config["rules"][idx]["mode"] = "exact" if exact_btn.isChecked() else "contains"
                self.save_config()
            rb_exact.clicked.connect(lambda checked, idx=i, btn=rb_exact: update_mode(idx, btn))
            rb_contains.clicked.connect(lambda checked, idx=i, btn=rb_exact: update_mode(idx, btn))
            mode_layout.addWidget(rb_exact)
            mode_layout.addWidget(rb_contains)
            tab_layout.addRow("匹配模式:", mode_layout)
            
            tab.setLayout(tab_layout)
            self.rules_tabs.addTab(tab, f"规则 {i+1}")

        def on_rule_count_changed():
            count = int(self.rule_count_combo.currentText())
            self.config["settings"]["active_rules_count"] = count
            self.save_config()
            for i in range(5):
                self.rules_tabs.setTabEnabled(i, i < count)
                
        self.rule_count_combo.currentIndexChanged.connect(on_rule_count_changed)
        on_rule_count_changed()
        
        rule_layout.addWidget(self.rules_tabs)
        rule_group.setLayout(rule_layout)
        main_layout.addWidget(rule_group)

        # --- 延迟和定时 ---
        time_group = QGroupBox("延迟及自动启停")
        time_layout = QFormLayout()
        
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 60); self.delay_spin.setValue(settings_config.get("send_delay", 0)); self.delay_spin.setSingleStep(0.5)
        self.delay_spin.valueChanged.connect(lambda: self.config["settings"].update({"send_delay": self.delay_spin.value()}) or self.save_config())
        
        self.random_delay_spin = QDoubleSpinBox()
        self.random_delay_spin.setRange(0, 30); self.random_delay_spin.setValue(settings_config.get("random_delay", 0)); self.random_delay_spin.setSingleStep(0.5)
        self.random_delay_spin.valueChanged.connect(lambda: self.config["settings"].update({"random_delay": self.random_delay_spin.value()}) or self.save_config())
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("基础延迟(分):")); delay_layout.addWidget(self.delay_spin)
        delay_layout.addWidget(QLabel("随机浮动(分):")); delay_layout.addWidget(self.random_delay_spin)
        time_layout.addRow(delay_layout)

        start_hbox = QHBoxLayout()
        self.start_hour = QSpinBox(); self.start_hour.setRange(0, 23); self.start_hour.setValue(settings_config.get("auto_start_hour", 10))
        self.start_minute = QSpinBox(); self.start_minute.setRange(0, 59); self.start_minute.setValue(settings_config.get("auto_start_minute", 0))
        self.end_hour = QSpinBox(); self.end_hour.setRange(0, 23); self.end_hour.setValue(settings_config.get("auto_end_hour", 12))
        self.end_minute = QSpinBox(); self.end_minute.setRange(0, 59); self.end_minute.setValue(settings_config.get("auto_end_minute", 0))
        
        def update_time():
            self.config["settings"].update({"auto_start_hour": self.start_hour.value(), "auto_start_minute": self.start_minute.value(), "auto_end_hour": self.end_hour.value(), "auto_end_minute": self.end_minute.value()})
            self.save_config()
            
        for w in [self.start_hour, self.start_minute, self.end_hour, self.end_minute]: w.valueChanged.connect(update_time)

        start_hbox.addWidget(QLabel("每日开始:")); start_hbox.addWidget(self.start_hour); start_hbox.addWidget(QLabel("时")); start_hbox.addWidget(self.start_minute); start_hbox.addWidget(QLabel("分"))
        start_hbox.addWidget(QLabel(" | 结束:")); start_hbox.addWidget(self.end_hour); start_hbox.addWidget(QLabel("时")); start_hbox.addWidget(self.end_minute); start_hbox.addWidget(QLabel("分"))
        time_layout.addRow(start_hbox)

        self.enable_auto_timer = QCheckBox("启用每日定时自动启停监控")
        self.enable_auto_timer.setChecked(settings_config.get("enable_auto_timer", False))
        def toggle_auto_timer(state):
            self.config["settings"]["enable_auto_timer"] = (state == Qt.Checked)
            self.save_config()
            if state == Qt.Checked: self.start_auto_timer_check()
            else: self.stop_auto_timer_check()
        self.enable_auto_timer.stateChanged.connect(toggle_auto_timer)
        time_layout.addRow(self.enable_auto_timer)
        
        time_group.setLayout(time_layout)
        main_layout.addWidget(time_group)

        return main_layout

    def init_monitor_log(self):
        vbox = QVBoxLayout()
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("监控运行日志"))
        export_btn = QPushButton("保存日志并清空面板")
        export_btn.setStyleSheet("padding: 2px 10px; font-size: 11px;")
        export_btn.clicked.connect(lambda: self.export_logs(manual=True))
        info_layout.addStretch()
        info_layout.addWidget(export_btn)
        self.log_view = QListWidget()
        self.log_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addLayout(info_layout)
        vbox.addWidget(self.log_view)
        return vbox

    def export_logs(self, manual=False):
        if self.log_view.count() == 0:
            if manual: QMessageBox.information(self, "提示", "当前没有日志可以导出。")
            return
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(log_dir, f"momo_log_{timestamp}.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for i in range(self.log_view.count()):
                    f.write(self.log_view.item(i).text() + "\n")
            self.log_view.clear()
            msg = f"已将历史日志保存至 {filename} 并释放内存"
            self.add_log(f"🧹 {msg}")
            if manual: QMessageBox.information(self, "清理成功", msg)
        except Exception as e:
            if manual: QMessageBox.warning(self, "导出失败", str(e))

    def add_log(self, message):
        self.add_log_signal.emit(message)

    def _do_add_log(self, message):
        current_time = time.strftime("%H:%M:%S")
        self.log_view.addItem(f"[{current_time}] {message}")
        self.log_view.scrollToBottom()
        if self.log_view.count() > 300:
            self.export_logs(manual=False)

    # [新增] 接收到子线程刷新信号后，主线程安全地更新图片数量显示
    def _do_update_img_count(self, rule_idx):
        if rule_idx in self.rule_img_count_labels:
            folder = self.config["rules"][rule_idx].get("folder", "")
            imgs = self.get_valid_images(folder)
            self.rule_img_count_labels[rule_idx].setText(f"图片数量: {len(imgs)}")

    def on_last_message_change(self, last_text, current_time):
        settings_config = self.config.get("settings", {})
        trigger_sender = settings_config.get("trigger_sender", "momo")
        active_count = settings_config.get("active_rules_count", 1)
        
        clean_text = str(last_text).strip()
        matched_rule_idx = -1
        
        for i in range(active_count):
            rule = self.config["rules"][i]
            keywords = [k.strip() for k in rule.get("keywords", "").split(',') if k.strip()]
            mode = rule.get("mode", "exact")
            
            for keyword in keywords:
                if mode == "exact" and clean_text == keyword:
                    matched_rule_idx = i
                    break
                elif mode == "contains" and keyword in clean_text:
                    matched_rule_idx = i
                    break
            if matched_rule_idx != -1:
                break
        
        if matched_rule_idx != -1 and not self.last_triggered:
            self.last_triggered = True
            
            self.add_log(f"🚨 【警报触发】命中规则 {matched_rule_idx+1}，内容: '{last_text}'")
            
            base_delay = settings_config.get("send_delay", 0)
            random_range = settings_config.get("random_delay", 0)
            
            if base_delay > 0 or random_range > 0:
                half_range = random_range / 2
                actual_delay = max(0, random.uniform(base_delay - half_range, base_delay + half_range) if random_range > 0 else base_delay)
                self.add_log(f"⏳ 延迟 {actual_delay:.1f} 分钟后开始发送...")
                delay_seconds = int(actual_delay * 60)
                
                # 传入命中的 rule_idx
                def delayed_send(rule_idx):
                    import ctypes
                    ctypes.windll.ole32.CoInitialize(None)
                    wait_time = delay_seconds
                    while wait_time > 0:
                        if not self.monitoring:
                            self.add_log("⏹️ 监控已停止，取消发送")
                            self.last_triggered = False
                            ctypes.windll.ole32.CoUninitialize()
                            return
                        time.sleep(1)
                        wait_time -= 1
                    if self.monitoring:
                        # 执行实际发送
                        self._do_send_action(trigger_sender, rule_idx)
                    ctypes.windll.ole32.CoUninitialize()
                        
                threading.Thread(target=delayed_send, args=(matched_rule_idx,), daemon=True).start()
            else:
                self._do_send_action(trigger_sender, matched_rule_idx)
                
        elif matched_rule_idx == -1 and self.last_triggered:
            self.last_triggered = False
            self.add_log(f"✅ 警报解除：最后一条消息变成了: '{last_text}'。")
    
    # [重构] 包含图片和文本的处理中心
    def _do_send_action(self, trigger_sender, rule_idx):
        rule = self.config["rules"][rule_idx]
        reply_type = rule.get("reply_type", "image")
        
        self.add_log(f"📡 开始执行发送机制...")
        
        try:
            if reply_type == "image":
                material_folder = rule.get("folder", "")
                images = self.get_valid_images(material_folder)
                
                if len(images) == 0:
                    self.add_log("❌ 指定素材文件夹中没有图片可发")
                    return
                
                selected_image = random.choice(images)
                self.add_log(f"🎲 已抽取图片: {os.path.basename(selected_image)}")
                
                self.wechat.send_file(trigger_sender, selected_image, search_user=False)
                self.add_log(f"📤 图片发送成功")
                
                # 发送完就移除
                os.remove(selected_image)
                self.add_log(f"🗑️ 已删除源文件: {os.path.basename(selected_image)}")
                
                # [核心] 向主线程发出信号，实时刷新对应的 UI 图片数量！
                self.update_img_count_signal.emit(rule_idx)
                
            elif reply_type == "text":
                reply_text = rule.get("reply_text", "")
                if not reply_text:
                    self.add_log("❌ 规则未配置回复文本，无法发送")
                    return
                
                self.add_log(f"📝 准备发送文本...")
                self.wechat.send_msg(trigger_sender, text=reply_text, search_user=False)
                self.add_log(f"📤 文本发送成功")
                
        except Exception as e:
            self.add_log(f"❌ 发送异常: {str(e)}")
        finally:
            self.last_triggered = False

    def start_monitoring(self):
        if self.monitoring:
            QMessageBox.information(self, "提示", "监控已经在运行中！")
            return
        
        start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.add_log(f"🚀 [{start_time}] 启动精准多重规则监控")
        
        self.last_triggered = False
        trigger_sender = self.config.get("settings", {}).get("trigger_sender", "momo")
        self.wechat.start_last_message_monitor(target_name=trigger_sender, callback=self.on_last_message_change, check_interval=1)
        
        self.monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_btn.setStyleSheet("color:gray")
        self.stop_btn.setStyleSheet("color:red")
        
    def stop_monitoring(self):
        if self.monitoring:
            self.wechat.stop_last_message_monitor()
            self.add_log(f"⏹️ 消息监控已手动停止")
            self.monitoring = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.start_btn.setStyleSheet("color:green")
            self.stop_btn.setStyleSheet("color:gray")
    
    def start_auto_timer_check(self):
        if self.auto_timer is None:
            self.auto_timer = QTimer(self)
            self.auto_timer.timeout.connect(self.auto_check_time)
            self.auto_timer.start(60000)
            self.add_log("⏰ 自动定时启停检查已就绪")
    
    def stop_auto_timer_check(self):
        if self.auto_timer is not None:
            self.auto_timer.stop()
            self.auto_timer = None
            self.add_log("⏹️ 自动定时启停已被关闭")
    
    def auto_check_time(self):
        now = datetime.datetime.now()
        settings_config = self.config.get("settings", {})
        start_h = settings_config.get("auto_start_hour", 10)
        start_m = settings_config.get("auto_start_minute", 0)
        end_h = settings_config.get("auto_end_hour", 12)
        end_m = settings_config.get("auto_end_minute", 0)
        
        current_total = now.hour * 60 + now.minute
        start_total = start_h * 60 + start_m
        end_total = end_h * 60 + end_m
        should_be_monitoring = start_total <= current_total < end_total
        
        if should_be_monitoring and not self.monitoring:
            self.add_log(f"🤖 到达设定区间，自动启动监控")
            self.start_monitoring()
        elif not should_be_monitoring and self.monitoring:
            self.add_log(f"🤖 离开设定区间，自动停止监控")
            self.stop_monitoring()

    def initUI(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_widget = QWidget()
        vbox = QVBoxLayout(main_widget)

        lang = self.init_language_choose()
        settings = self.init_settings()
        monitor_log = self.init_monitor_log()

        hbox_controls = QHBoxLayout()
        self.start_btn = QPushButton("▶ 开始监控")
        self.start_btn.setStyleSheet("color:green; font-size: 14px; font-weight: bold; padding: 12px;")
        self.start_btn.clicked.connect(self.start_monitoring)
        
        self.stop_btn = QPushButton("■ 停止监控")
        self.stop_btn.setStyleSheet("color:gray; font-size: 14px; padding: 12px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        
        hbox_controls.addWidget(self.start_btn)
        hbox_controls.addWidget(self.stop_btn)

        vbox.addWidget(lang)
        vbox.addLayout(settings)
        vbox.addLayout(monitor_log)
        vbox.addLayout(hbox_controls)

        scroll_area.setWidget(main_widget)
        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll_area)

        desktop = QApplication.desktop()
        screenRect = desktop.screenGeometry()
        self.setLayout(outer_layout)
        self.resize(int(screenRect.width() * 0.4), int(screenRect.height() * 0.8))
        self.setWindowTitle('EasyChat 规则自定化发图机器人 (增强版)')
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MomoReplyGUI()
    sys.exit(app.exec_())