import uiautomation as auto
import time

print("请打开微信聊天窗口，3秒后开始遍历控件...")
time.sleep(3)

# 获取微信窗口
wechat_window = auto.WindowControl(Depth=1, Name="微信", searchDepth=1)
if not wechat_window.Exists(0, 0):
    wechat_window = auto.WindowControl(Depth=1, ClassName="WeChatMainWndForPC", searchDepth=1)
    
if wechat_window.Exists(0, 0):
    print(f"找到微信窗口: {wechat_window.Name}, 句柄: {wechat_window.NativeWindowHandle}")
    
    # 遍历所有控件
    print("\n=== 控件结构 ===")
    def walk_control(control, depth=0):
        indent = "  " * depth
        try:
            name = control.Name if hasattr(control, 'Name') else ""
            control_type = control.ControlTypeName if hasattr(control, 'ControlTypeName') else ""
            print(f"{indent}{control_type} - '{name}'")
            
            # 只遍历前3层，避免输出太多
            if depth < 3:
                for child in control.GetChildren():
                    walk_control(child, depth + 1)
        except Exception as e:
            print(f"{indent}错误: {e}")
    
    walk_control(wechat_window)
    
    # 查找消息列表
    print("\n=== 查找消息列表控件 ===")
    all_lists = wechat_window.FindAllControlDepthFirst(controlType=auto.UIA_ControlTypeIds.UIA_ListControlTypeId)
    print(f"找到 {len(all_lists)} 个List控件")
    for i, lst in enumerate(all_lists):
        try:
            name = lst.Name
            child_count = len(lst.GetChildren())
            print(f"列表{i}: 名称='{name}', 子项数量={child_count}")
            if child_count > 0:
                first_child = lst.GetChildren()[0]
                print(f"  第一个子项: {first_child.ControlTypeName} - '{first_child.Name}'")
        except:
            pass
else:
    print("未找到微信窗口，请确保微信已经打开")
