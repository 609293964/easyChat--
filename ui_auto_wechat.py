import time
import uiautomation as auto
import subprocess
import os
import pyautogui
import threading
from ctypes import *

from clipboard import setClipboardFiles
from PyQt5.QtWidgets import QApplication
from wechat_locale import WeChatLocale


# 鼠标移动到控件上
def move(element):
    x, y = element.GetPosition()
    auto.SetCursorPos(x, y)


# 鼠标快速点击控件
def click(element):
    x, y = element.GetPosition()
    auto.Click(x, y)


class WeChat:
    def __init__(self, path, locale="zh-CN"):
        self.path = path
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        assert locale in WeChatLocale.getSupportedLocales()
        self.lc = WeChatLocale(locale)
        
    def is_wechat_visible(self):
        try:
            wechat_window = auto.WindowControl(Depth=1, Name=self.lc.weixin, searchDepth=1)
            if wechat_window.Exists(0, 0):
                hwnd = wechat_window.NativeWindowHandle
                user32 = windll.user32
                is_visible = user32.IsWindowVisible(hwnd)
                is_minimized = user32.IsIconic(hwnd)
                return is_visible and not is_minimized
            return False
        except:
            return False
    
    def ensure_wechat_visible(self):
        try:
            wechat_window = auto.WindowControl(Depth=1, Name=self.lc.weixin, searchDepth=1)
            if wechat_window.Exists(0, 0):
                hwnd = wechat_window.NativeWindowHandle
                user32 = windll.user32
                is_minimized = user32.IsIconic(hwnd)
                if is_minimized:
                    user32.OpenIconicWindow(hwnd)
                    time.sleep(1)
                wechat_window.SetFocus()
                return True
        except:
            pass
        return False

    def open_wechat(self):
        if self.is_wechat_visible():
            wechat_window = self.get_wechat()
            wechat_window.SetFocus()
            return

        if self.ensure_wechat_visible():
            time.sleep(1)
            if self.is_wechat_visible():
                return

        auto.SendKeys("{Ctrl}{Alt}w")
        time.sleep(2)
        
        if not self.is_wechat_visible() and self.path and os.path.exists(self.path):
            subprocess.Popen(self.path)
            time.sleep(5)
    
    def get_wechat(self):
        return auto.WindowControl(Depth=1, Name=self.lc.weixin)

    def get_contact(self, name):
        self.open_wechat()
        self.get_wechat()
        
        search_box = auto.EditControl(Depth=13, Name=self.lc.search)
        click(search_box)
        
        setClipboardFiles([]) 
        auto.SetClipboardText(name)
        auto.SendKeys("{Ctrl}v")
        time.sleep(0.3)

        list_control = auto.ListControl(Depth=4)
        for item in list_control.GetChildren():
            if "XTableCell" not in item.ClassName:
                click(item)
                break

        tool_bar = auto.ToolBarControl(Depth=15)
        move(tool_bar)
        click(tool_bar)
    
    def press_enter(self):
        auto.SendKeys("{enter}")

    def _focus_input_box(self):
        self.open_wechat()
        wechat_window = self.get_wechat()
        wechat_window.SetFocus()
        time.sleep(0.2)
        
        clicked = False
        try:
            edit_input = auto.EditControl(Name="输入", searchDepth=20)
            if edit_input.Exists(0.5, 0):
                move(edit_input)
                click(edit_input)
                clicked = True
                time.sleep(0.2)
        except Exception:
            pass
        
        if not clicked:
            try:
                tool_bar = auto.ToolBarControl(searchDepth=20)
                if tool_bar.Exists(0.5, 0):
                    move(tool_bar)
                    click(tool_bar)
                    clicked = True
                    time.sleep(0.2)
            except Exception:
                pass
        
        if not clicked:
            screen_width, screen_height = pyautogui.size()
            pyautogui.click(screen_width // 2, int(screen_height * 0.85))
            time.sleep(0.2)

    def send_text(self, name: str, text: str, search_user: bool = True) -> None:
        if search_user:
            self.get_contact(name)
        else:
            self._focus_input_box()
            
        # 【优化】备份原有剪贴板，防止发消息时破坏用户的复制内容
        clipboard = QApplication.clipboard()
        old_text = clipboard.text()

        auto.SetClipboardText(text)
        time.sleep(0.3)
        auto.SendKeys("{Ctrl}v")
        time.sleep(0.5)
        self.press_enter()
        
        if old_text:
            auto.SetClipboardText(old_text)

    def send_file(self, name: str, path: str, search_user: bool = True) -> None:
        if search_user:
            self.get_contact(name)
        else:
            self._focus_input_box()
        
        setClipboardFiles([path])
        time.sleep(0.3)
        auto.SendKeys("{Ctrl}v")
        time.sleep(0.5)
        self.press_enter()
    
    def start_last_message_monitor(self, callback=None, check_interval=1):
        if hasattr(self, 'last_message_monitoring') and self.last_message_monitoring:
            return
        
        self.last_message_monitoring = True
        self.last_captured_text = ""
        self.last_message_callback = callback
        
        def monitor_loop():
            # 【优化】加入列表控件的缓存，避免高频在整个树中检索 ListControl 导致的高 CPU 占用
            cached_msg_list = None
            
            while self.last_message_monitoring:
                try:
                    self.open_wechat()
                    time.sleep(0.5)
                    
                    if cached_msg_list is None or not cached_msg_list.Exists(0, 0):
                        wechat_win = self.get_wechat()
                        # 【优化】限定搜索深度，大幅提升检索性能
                        cached_msg_list = wechat_win.ListControl(Name=self.lc.message, searchDepth=15)
                    
                    if not cached_msg_list.Exists(1, 0.5):
                        time.sleep(check_interval)
                        continue
                    
                    items = cached_msg_list.GetChildren()
                    
                    if items:
                        last_item = items[-1]
                        last_text = last_item.Name
                        
                        if last_text != self.last_captured_text:
                            self.last_captured_text = last_text
                            current_time = time.strftime("%H:%M:%S")
                            
                            if self.last_message_callback:
                                try:
                                    self.last_message_callback(last_text, current_time)
                                except Exception:
                                    pass
                                    
                except Exception:
                    cached_msg_list = None  # 出错后重置缓存
                    pass
                    
                time.sleep(check_interval)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def stop_last_message_monitor(self):
        if hasattr(self, 'last_message_monitoring'):
            self.last_message_monitoring = False