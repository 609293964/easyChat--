import time
import pyautogui
import pyperclip
import threading
import re
from ctypes import windll

class WeChatMonitor:
    def __init__(self):
        self.monitoring = False
        self.message_callback = None
        self.last_messages = set()
        self.user32 = windll.user32
        
    def set_message_callback(self, callback):
        """设置消息回调函数"""
        self.message_callback = callback
        
    def get_clipboard_text(self):
        """获取剪贴板文本"""
        try:
            return pyperclip.paste()
        except:
            return ""
            
    def set_clipboard_text(self, text):
        """设置剪贴板文本"""
        try:
            pyperclip.copy(text)
        except:
            pass
            
    def get_wechat_window(self):
        """获取微信窗口句柄"""
        try:
            hwnd = self.user32.FindWindowW("WeChatMainWndForPC", None)
            return hwnd
        except:
            return None
            
    def is_wechat_active(self):
        """检查微信是否在前台"""
        try:
            foreground_hwnd = self.user32.GetForegroundWindow()
            wechat_hwnd = self.get_wechat_window()
            return foreground_hwnd == wechat_hwnd
        except:
            return False
            
    def copy_selected_text(self):
        """复制选中的文本"""
        # 保存当前剪贴板内容
        old_clip = self.get_clipboard_text()
        
        try:
            # 发送Ctrl+C复制
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            # 获取新的剪贴板内容
            new_text = self.get_clipboard_text()
            # 恢复原来的剪贴板内容
            self.set_clipboard_text(old_clip)
            return new_text.strip()
        except:
            # 恢复原来的剪贴板内容
            self.set_clipboard_text(old_clip)
            return ""
            
    def select_all_messages(self):
        """全选当前聊天窗口的消息"""
        try:
            # 先点击消息区域
            pyautogui.click(pyautogui.size()[0]//2, pyautogui.size()[1]//2 - 100)
            time.sleep(0.1)
            # 发送Ctrl+A全选
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
        except:
            pass
            
    def parse_messages(self, text):
        """解析复制的消息文本"""
        if not text:
            return []
            
        messages = []
        # 按行分割
        lines = text.split('\n')
        current_sender = None
        current_time = None
        current_content = []
        
        # 匹配时间格式，比如 "2026/3/13 23:30" 或者 "23:30"
        time_pattern = re.compile(r'^(\d{4}/\d{1,2}/\d{1,2} )?\d{1,2}:\d{1,2}$')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是时间行
            if time_pattern.match(line):
                # 保存上一条消息
                if current_sender and current_content:
                    msg = {
                        'sender': current_sender,
                        'content': '\n'.join(current_content),
                        'time': line if '/' in line else f"{time.strftime('%Y/%m/%d')} {line}",
                        'type': 'text'
                    }
                    messages.append(msg)
                    current_content = []
                current_time = line
                continue
                
            # 检查是否是发送者（如果下一行是时间，这行就是发送者）
            if current_time is not None and not current_content:
                current_sender = line
                continue
                
            # 内容行
            if current_sender:
                current_content.append(line)
                
        # 添加最后一条消息
        if current_sender and current_content:
            msg = {
                'sender': current_sender,
                'content': '\n'.join(current_content),
                'time': current_time if '/' in current_time else f"{time.strftime('%Y/%m/%d')} {current_time}",
                'type': 'text'
            }
            messages.append(msg)
            
        return messages
            
    def start_monitor(self, check_interval=3):
        """开始监控消息"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.last_messages = set()
        
        def monitor_loop():
            print("消息监控已启动（基于剪贴板复制方式）")
            print("提示：请保持微信聊天窗口在前台")
            
            while self.monitoring:
                try:
                    # 只在微信在前台时监控
                    if not self.is_wechat_active():
                        time.sleep(check_interval)
                        continue
                        
                    # 全选消息
                    self.select_all_messages()
                    # 复制
                    text = self.copy_selected_text()
                    # 取消选中
                    pyautogui.press('esc')
                    
                    # 解析消息
                    messages = self.parse_messages(text)
                    
                    # 检查新消息
                    for msg in messages[-10:]:  # 只检查最新的10条
                        msg_id = hash(f"{msg['sender']}{msg['content']}{msg['time']}")
                        if msg_id not in self.last_messages:
                            self.last_messages.add(msg_id)
                            # 调用回调
                            if self.message_callback:
                                self.message_callback(
                                    msg['sender'],
                                    msg['content'],
                                    msg['time'],
                                    msg['type']
                                )
                                
                    # 限制存储的消息ID数量
                    if len(self.last_messages) > 200:
                        self.last_messages = set(list(self.last_messages)[-100:])
                        
                except Exception as e:
                    print(f"监控出错: {e}")
                    
                time.sleep(check_interval)
                
        # 启动监控线程
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        
    def stop_monitor(self):
        """停止监控"""
        self.monitoring = False
        print("消息监控已停止")


# 测试
if __name__ == "__main__":
    monitor = WeChatMonitor()
    
    def callback(sender, content, time, msg_type):
        print(f"[{time}] {sender}: {content}")
        
    monitor.set_message_callback(callback)
    monitor.start_monitor()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop_monitor()
