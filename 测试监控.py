from ui_auto_wechat import WeChat
import time
import uiautomation as auto

# 替换成你的微信路径
wechat_path = "C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe"

print("正在初始化微信...")
wechat = WeChat(wechat_path, locale="zh-CN")

print("打开微信窗口...")
wechat.open_wechat()
time.sleep(2)

# 先测试获取微信窗口
print("\n=== 测试获取微信窗口 ===")
try:
    wechat_window = wechat.get_wechat()
    print(f"微信窗口标题: {wechat_window.Name}")
    print(f"窗口句柄: {wechat_window.NativeWindowHandle}")
except Exception as e:
    print(f"获取微信窗口失败: {e}")
    exit()

# 测试查找消息列表
print("\n=== 测试查找消息列表控件 ===")
try:
    # 尝试多种方式查找
    print("方式1: 查找所有ListControl...")
    all_lists = wechat_window.FindAllControlDepthFirst(controlType=auto.UIA_ControlTypeIds.UIA_ListControlTypeId)
    print(f"找到 {len(all_lists)} 个ListControl控件")
    for i, lst in enumerate(all_lists):
        print(f"  控件{i}: 名称='{lst.Name}', 类型={lst.ControlTypeName}, 子项数量={len(lst.GetChildren())}")
        
except Exception as e:
    print(f"查找消息列表失败: {e}")

print("\n=== 测试获取当前消息 ===")
try:
    messages = wechat.get_current_chat_messages(max_count=5)
    print(f"获取到 {len(messages)} 条消息")
    for msg in messages:
        print(f"[{msg['time']}] {msg['sender']}: {msg['content']} ({msg['type']})")
except Exception as e:
    print(f"获取消息失败: {e}")
    import traceback
    traceback.print_exc()

# 测试监控
print("\n=== 开始测试监控 ===")
def on_message(sender, content, time, msg_type):
    print(f"[新消息] [{time}] [{msg_type}] {sender}: {content}")

wechat.set_message_callback(on_message)
wechat.start_monitor(check_interval=1)

print("请在微信窗口发送消息测试，按Ctrl+C停止...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n停止监控...")
    wechat.stop_monitor()
