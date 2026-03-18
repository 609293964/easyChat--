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
        # 微信打开路径
        self.path = path
        
        # 用于实例化 QApplication 环境，确保剪贴板操作正常工作
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        assert locale in WeChatLocale.getSupportedLocales()
        self.lc = WeChatLocale(locale)
        
    # 检查微信窗口是否可见
    def is_wechat_visible(self):
        try:
            wechat_window = auto.WindowControl(Depth=1, Name=self.lc.weixin, searchDepth=1)
            # 检查窗口是否存在且可见（非最小化）
            if wechat_window.Exists(0, 0):
                # 获取窗口句柄
                hwnd = wechat_window.NativeWindowHandle
                # 使用 Windows API 检查窗口是否可见且未最小化
                user32 = windll.user32
                is_visible = user32.IsWindowVisible(hwnd)
                is_minimized = user32.IsIconic(hwnd)
                return is_visible and not is_minimized
            return False
        except:
            return False
    
    # 确保微信窗口是打开且非最小化的
    def ensure_wechat_visible(self):
        """确保微信窗口存在，如果最小化就还原它"""
        try:
            wechat_window = auto.WindowControl(Depth=1, Name=self.lc.weixin, searchDepth=1)
            if wechat_window.Exists(0, 0):
                hwnd = wechat_window.NativeWindowHandle
                user32 = windll.user32
                is_minimized = user32.IsIconic(hwnd)
                if is_minimized:
                    # 如果最小化了，还原窗口
                    user32.OpenIconicWindow(hwnd)
                    time.sleep(1)
                wechat_window.SetFocus()
                return True
        except:
            pass
        return False

    # 打开微信客户端
    def open_wechat(self):
        # 先检查微信窗口是否已经可见
        if self.is_wechat_visible():
            # 如果已经可见，只需要激活窗口到前台
            wechat_window = self.get_wechat()
            wechat_window.SetFocus()
            return

        # 窗口存在但可能最小化了，先尝试还原
        if self.ensure_wechat_visible():
            time.sleep(1)
            if self.is_wechat_visible():
                return

        # 如果窗口不可见，先尝试通过全局快捷键打开（微信已经运行但最小化）
        auto.SendKeys("{Ctrl}{Alt}w")
        time.sleep(2)
        
        # 如果快捷键打不开，检查一下是否微信进程没启动，直接启动它
        if not self.is_wechat_visible() and self.path and os.path.exists(self.path):
            # 从配置的路径启动微信
            subprocess.Popen(self.path)
            # 等待微信启动
            time.sleep(5)
    
    # 搜寻微信客户端控件
    def get_wechat(self):
        return auto.WindowControl(Depth=1, Name=self.lc.weixin)

    # 搜索指定用户 (保留此方法以防未来需要 search_user=True)
    def get_contact(self, name):
        self.open_wechat()
        self.get_wechat()
        
        search_box = auto.EditControl(Depth=13, Name=self.lc.search)
        click(search_box)
        
        # 复制名字并粘贴搜索
        setClipboardFiles([]) # 清空文件剪贴板
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
    
    # 鼠标移动到发送按钮处点击发送消息
    def press_enter(self):
        # 改用回车键发送，比点击发送按钮更可靠（适配不同微信版本）
        auto.SendKeys("{enter}")

    # 发送文件/图片核心逻辑
    def send_file(self, name: str, path: str, search_user: bool = True) -> None:
        """
        Args:
            name: 指定用户名的名称，输入搜索框后出现的第一个人
            path: 发送文件的本地地址
            search_user: 是否需要搜索用户 (Momo模式默认为False)
        """
        if search_user:
            self.get_contact(name)
        else:
            # 即使不搜索用户，也要确保微信窗口在前台，并点击输入框
            self.open_wechat()
            wechat_window = self.get_wechat()
            wechat_window.SetFocus()
            time.sleep(0.2)
            
            clicked = False
            # 方式1：直接找 EditControl 名字为"输入"
            try:
                edit_input = auto.EditControl(Name="输入", searchDepth=20)
                if edit_input.Exists(0.5, 0):
                    move(edit_input)
                    click(edit_input)
                    clicked = True
                    time.sleep(0.2)
            except Exception:
                pass
            
            # 方式2：通过工具条查找（兼容旧版本）
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
            
            # 方式3：直接点击屏幕下方中央位置（兜底方案）
            if not clicked:
                screen_width, screen_height = pyautogui.size()
                pyautogui.click(screen_width // 2, int(screen_height * 0.85))
                time.sleep(0.2)
        
        # 将文件复制到剪切板
        setClipboardFiles([path])
        time.sleep(0.3)
        
        auto.SendKeys("{Ctrl}v")
        time.sleep(0.5)
        
        self.press_enter()
    
    # ==================== 精准最后一条消息监控 ====================
    def start_last_message_monitor(self, callback=None, check_interval=1):
        """
        启动基于控件树的精准最后一条消息监控 (Momo 自动回复专用)
        """
        if hasattr(self, 'last_message_monitoring') and self.last_message_monitoring:
            print("最后一条消息监控已经在运行中")
            return
        
        self.last_message_monitoring = True
        self.last_captured_text = ""
        self.last_message_callback = callback
        
        def monitor_loop():
            print("✅ 精准最后一条消息监控已启动（控件树方式）")
            
            while self.last_message_monitoring:
                try:
                    # 每次循环都确保微信窗口是打开且激活的
                    self.open_wechat()
                    time.sleep(0.5)
                    
                    # 重新查找消息列表控件
                    msg_list = auto.ListControl(Name=self.lc.message)
                    
                    if not msg_list.Exists(1, 0.5):
                        time.sleep(check_interval)
                        continue
                    
                    items = msg_list.GetChildren()
                    
                    if items:
                        last_item = items[-1]
                        last_text = last_item.Name
                        
                        # 如果消息发生变化
                        if last_text != self.last_captured_text:
                            self.last_captured_text = last_text
                            current_time = time.strftime("%H:%M:%S")
                            
                            # 调用回调函数
                            if self.last_message_callback:
                                try:
                                    self.last_message_callback(last_text, current_time)
                                except Exception as e:
                                    print(f"回调函数执行出错: {e}")
                                    
                except Exception:
                    # 忽略界面刷新时瞬间抓不到数据的偶发错误
                    pass
                    
                time.sleep(check_interval)
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def stop_last_message_monitor(self):
        """停止精准最后一条消息监控"""
        if hasattr(self, 'last_message_monitoring'):
            self.last_message_monitoring = False
            print("精准最后一条消息监控已停止")