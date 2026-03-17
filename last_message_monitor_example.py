#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精准最后一条消息监控示例
整合自 v1.py，已经集成到 ui_auto_wechat.py 的 WeChat 类中

功能：持续监控当前打开聊天窗口的最后一条消息，支持自定义回调处理
"""

import time
from ui_auto_wechat import WeChat


def example_alert_callback(last_text, current_time):
    """
    示例回调函数：检测包含感叹号的消息并发出警报
    你可以修改这个函数实现自己的逻辑，比如：
    - 发送通知
    - 自动回复
    - 记录日志
    - 弹窗提醒
    """
    # 在这里添加你的检测逻辑
    if "!" in last_text or "！" in last_text:
        print(f"\n[{current_time}] 🚨🚨🚨 【高危警报】检测到含感叹号的消息！")
        print(f"内容: '{last_text}'")
        # 这里可以添加弹窗、播放声音等操作


def main():
    # 这里填你的微信路径
    wechat_path = "D:\\Program Files (x86)\\Tencent\\Weixin\\Weixin.exe"
    
    # 创建 WeChat 实例
    wechat = WeChat(wechat_path, locale="zh-CN")
    
    # 打开微信
    wechat.open_wechat()
    
    # 启动监控，使用示例回调函数
    # 如果你不需要回调，也可以传 None，只记录最后一条消息到 wechat.last_captured_text
    wechat.start_last_message_monitor(callback=example_alert_callback, check_interval=1)
    
    print("\n监控已启动，请打开你想要监控的聊天窗口，程序会持续监听最后一条消息")
    print("按 Ctrl+C 停止监控\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        wechat.stop_last_message_monitor()
        print("\n监控已停止")


if __name__ == '__main__':
    main()
