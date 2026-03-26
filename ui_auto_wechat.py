import os
import re
import subprocess
import threading
import time

import pyperclip
import uiautomation as auto

from ctypes import windll
from typing import List, Tuple

from clipboard import setClipboardFiles
from wechat_locale import WeChatLocale


def move(element):
    x, y = element.GetPosition()
    auto.SetCursorPos(x, y)


def click(element):
    x, y = element.GetPosition()
    auto.Click(x, y)


class WeChat:
    def __init__(self, path, locale="zh-CN"):
        self.path = path
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
        except Exception:
            return False

    def ensure_wechat_visible(self):
        try:
            wechat_window = auto.WindowControl(Depth=1, Name=self.lc.weixin, searchDepth=1)
            if wechat_window.Exists(0, 0):
                hwnd = wechat_window.NativeWindowHandle
                user32 = windll.user32
                if user32.IsIconic(hwnd):
                    user32.OpenIconicWindow(hwnd)
                    time.sleep(1)
                user32.SetForegroundWindow(hwnd)
                wechat_window.SetFocus()
                return True
        except Exception:
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

    def prevent_offline(self):
        self.open_wechat()
        self.get_wechat()
        search_box = auto.EditControl(Depth=8, Name=self.lc.search)
        click(search_box)

    def get_contact(self, name):
        self.open_wechat()
        self.get_wechat()
        search_box = auto.EditControl(Depth=13, Name=self.lc.search)
        click(search_box)
        pyperclip.copy(name)
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

    def paste_text(self, text: str) -> None:
        pyperclip.copy(text)
        time.sleep(0.3)
        auto.SendKeys("{Ctrl}v")

    def get_independent_window(self, target_name):
        win = auto.WindowControl(Name=target_name, searchDepth=1)
        if win.Exists(0.2, 0):
            return win
        return None

    def _activate_window(self, chat_win) -> bool:
        try:
            hwnd = chat_win.NativeWindowHandle
            user32 = windll.user32
            if user32.IsIconic(hwnd):
                user32.OpenIconicWindow(hwnd)
                time.sleep(0.5)
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
            chat_win.SetFocus()
            time.sleep(0.3)
            return True
        except Exception:
            try:
                chat_win.SetFocus()
                time.sleep(0.3)
                return True
            except Exception:
                return False

    def _find_chat_input(self, chat_win):
        candidates = [
            chat_win.EditControl(Name="输入"),
            chat_win.EditControl(foundIndex=1),
            chat_win.EditControl(searchDepth=8, foundIndex=1),
        ]
        for edit_input in candidates:
            try:
                if edit_input.Exists(0.3, 0):
                    return edit_input
            except Exception:
                pass
        return None

    def _focus_independent_chat_input(self, target_name: str):
        chat_win = self.get_independent_window(target_name)
        if not chat_win:
            print(f"发送失败：找不到名为 '{target_name}' 的独立窗口。请确认窗口是否已拖出！")
            return None

        if not self._activate_window(chat_win):
            print(f"发送失败：无法激活窗口 '{target_name}'。")
            return None

        current_mouse_pos = auto.GetCursorPos()
        try:
            edit_input = self._find_chat_input(chat_win)
            if edit_input:
                move(edit_input)
                click(edit_input)
                time.sleep(0.2)
                return chat_win

            rect = chat_win.BoundingRectangle
            if not rect:
                print(f"发送失败：未能定位 '{target_name}' 的输入区域。")
                return None

            click_x = rect.left + (rect.right - rect.left) // 2
            click_y = rect.bottom - 60
            auto.Click(click_x, click_y)
            time.sleep(0.2)
            return chat_win
        finally:
            auto.SetCursorPos(current_mouse_pos[0], current_mouse_pos[1])

    def _get_message_list(self, chat_win):
        try:
            msg_list = chat_win.ListControl(Name=self.lc.message)
            if msg_list.Exists(0.2, 0):
                return msg_list
        except Exception:
            pass

        try:
            msg_list = chat_win.ListControl(foundIndex=1)
            if msg_list.Exists(0.2, 0):
                return msg_list
        except Exception:
            pass
        return None

    def _message_signature(self, item) -> str:
        try:
            if item.Name and str(item.Name).strip():
                return str(item.Name).strip()
            child_names = []
            for child in item.GetChildren():
                name = getattr(child, "Name", "")
                if name and str(name).strip():
                    child_names.append(str(name).strip())
            return "|".join(child_names)
        except Exception:
            return ""

    def _control_text(self, control) -> str:
        try:
            if control.Name and str(control.Name).strip():
                return str(control.Name).strip()
            child_names = []
            for child in control.GetChildren():
                name = getattr(child, "Name", "")
                if name and str(name).strip():
                    child_names.append(str(name).strip())
            return "|".join(child_names)
        except Exception:
            return ""

    def _capture_message_state(self, chat_win) -> Tuple[int, str]:
        msg_list = self._get_message_list(chat_win)
        if not msg_list:
            return 0, ""
        try:
            items = msg_list.GetChildren()
            count = len(items)
            tail = [self._message_signature(item) for item in items[-3:]]
            tail = [text for text in tail if text]
            return count, "||".join(tail)
        except Exception:
            return 0, ""

    def _wait_for_message_change(self, chat_win, before_state, timeout=8.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            after_state = self._capture_message_state(chat_win)
            if after_state[0] > before_state[0]:
                return True
            if after_state != before_state and after_state[0] > 0:
                return True
            time.sleep(0.4)
        return False

    def _get_toolbar_buttons(self, chat_win):
        buttons = []
        try:
            for control in chat_win.GetChildren():
                try:
                    if getattr(control, "ControlTypeName", "") == "ToolBarControl":
                        for child in control.GetChildren():
                            if getattr(child, "ControlTypeName", "") == "ButtonControl":
                                buttons.append(child)
                            else:
                                try:
                                    for grandchild in child.GetChildren():
                                        if getattr(grandchild, "ControlTypeName", "") == "ButtonControl":
                                            buttons.append(grandchild)
                                except Exception:
                                    pass
                except Exception:
                    pass
        except Exception:
            pass
        return buttons

    def _click_send_button(self, chat_win) -> bool:
        candidates = self._get_toolbar_buttons(chat_win)
        if not candidates:
            try:
                candidates = chat_win.GetChildren()
            except Exception:
                candidates = []

        exact_match = None
        fallback_match = None

        for control in candidates:
            try:
                if getattr(control, "ControlTypeName", "") != "ButtonControl":
                    continue
                text = self._control_text(control)
                if not text:
                    continue
                if text == "发送":
                    exact_match = control
                    break
                if "发送" in text and all(keyword not in text for keyword in ("表情", "收藏", "文件")):
                    fallback_match = control
            except Exception:
                pass

        button = exact_match or fallback_match
        if button is not None:
            click(button)
            return True
        return False

    def _click_send_file_button(self, chat_win) -> bool:
        exact_match = None
        fallback_match = None
        for control in self._get_toolbar_buttons(chat_win):
            try:
                text = self._control_text(control)
                if not text:
                    continue
                if text == "发送文件":
                    exact_match = control
                    break
                if "文件" in text and "发送" in text:
                    fallback_match = control
            except Exception:
                pass

        button = exact_match or fallback_match
        if button is not None:
            click(button)
            return True
        return False

    def _attach_file_via_dialog(self, chat_win, path: str) -> bool:
        if not self._click_send_file_button(chat_win):
            return False

        dialog = None
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                dialog = auto.WindowControl(ClassName="#32770", searchDepth=1)
                if dialog.Exists(0.2, 0):
                    break
            except Exception:
                dialog = None
            time.sleep(0.2)

        if dialog is None or not dialog.Exists(0.2, 0):
            return False

        try:
            dialog.SetFocus()
        except Exception:
            pass

        pyperclip.copy(path)
        time.sleep(0.2)
        auto.SendKeys("{Ctrl}v")
        time.sleep(0.2)
        auto.SendKeys("{Enter}")
        time.sleep(1.5)
        return True

    def send_msg(self, name, at_names: List[str] = None, text: str = None, search_user: bool = True) -> bool:
        chat_win = None
        before_state = None

        if search_user:
            self.get_contact(name)
        else:
            chat_win = self._focus_independent_chat_input(name)
            if not chat_win:
                return False
            before_state = self._capture_message_state(chat_win)

        if at_names is not None:
            for at_name in at_names:
                if at_name == "所有人":
                    auto.SendKeys("@{UP}{enter}")
                elif at_name != "":
                    auto.SendKeys(f"@{at_name}")
                    auto.SendKeys("{enter}")

        if text is not None:
            self.paste_text(text)

        self.press_enter()

        if chat_win and before_state is not None:
            return self._wait_for_message_change(chat_win, before_state, timeout=5.0)
        return True

    def send_file(self, name: str, path: str, search_user: bool = True) -> bool:
        if not path or not os.path.exists(path):
            print(f"发送失败：文件不存在 -> {path}")
            return False

        chat_win = None
        before_state = None

        if search_user:
            self.get_contact(name)
        else:
            chat_win = self._focus_independent_chat_input(name)
            if not chat_win:
                return False
            before_state = self._capture_message_state(chat_win)

        setClipboardFiles([path])
        time.sleep(0.5)

        if chat_win:
            self._activate_window(chat_win)
            time.sleep(0.2)
            rect = chat_win.BoundingRectangle
            if rect:
                auto.Click(rect.left + (rect.right - rect.left) // 2, rect.bottom - 60)
                time.sleep(0.2)

        auto.SendKeys("{Ctrl}v")
        time.sleep(1.5)
        self.press_enter()

        if chat_win and before_state is not None:
            if self._wait_for_message_change(chat_win, before_state, timeout=4.0):
                return True

            if self._attach_file_via_dialog(chat_win, path):
                if self._wait_for_message_change(chat_win, before_state, timeout=5.0):
                    return True
                if self._click_send_button(chat_win):
                    return self._wait_for_message_change(chat_win, before_state, timeout=5.0)

            if self._click_send_button(chat_win):
                return self._wait_for_message_change(chat_win, before_state, timeout=5.0)

            return False
        return True

    def start_last_message_monitor(self, target_name=None, callback=None, check_interval=1):
        if hasattr(self, "last_message_monitoring") and self.last_message_monitoring:
            print("精准最后一条消息监控已经在运行中")
            return

        self.last_message_monitoring = True
        self.last_captured_text = ""
        self.last_message_callback = callback

        def monitor_loop():
            _uia_init = auto.UIAutomationInitializerInThread()
            print(f"已启动独立窗口模式监听，目标窗口: [{target_name}]")

            while self.last_message_monitoring:
                try:
                    if not target_name:
                        time.sleep(check_interval)
                        continue

                    chat_win = self.get_independent_window(target_name)
                    if not chat_win:
                        time.sleep(check_interval)
                        continue

                    msg_list = self._get_message_list(chat_win)
                    if not msg_list:
                        time.sleep(check_interval)
                        continue

                    items = msg_list.GetChildren()
                    if items:
                        last_text = ""
                        for item in reversed(items):
                            text = self._message_signature(item)
                            if not text:
                                continue
                            if re.match(r"^(\d{1,2}:\d{2})$", text):
                                continue
                            if re.match(r"^(昨天|前天|星期.)\s+\d{1,2}:\d{2}$", text):
                                continue
                            if re.match(r"^\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}$", text):
                                continue
                            last_text = text
                            break

                        if last_text and last_text != self.last_captured_text:
                            self.last_captured_text = last_text
                            current_time = time.strftime("%H:%M:%S")
                            print(f"[监控日志] 捕获到消息: {last_text}")
                            if self.last_message_callback:
                                try:
                                    self.last_message_callback(last_text, current_time)
                                except Exception as e:
                                    print(f"执行回调报错: {e}")
                except Exception:
                    pass

                time.sleep(check_interval)

            _uia_init = None

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def stop_last_message_monitor(self):
        if hasattr(self, "last_message_monitoring"):
            self.last_message_monitoring = False
            print("精准最后一条消息监控已停止")


if __name__ == "__main__":
    pass
