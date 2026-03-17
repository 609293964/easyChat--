import os
import shutil
import zipfile

# 创建打包目录
output_dir = "easyChat便携版"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 复制主程序
shutil.copy("dist/wechat_gui.exe", f"{output_dir}/easyChat.exe")

# 复制说明文件
shutil.copy("打包说明.txt", f"{output_dir}/运行说明.txt")

# 创建运行库目录
runtime_dir = f"{output_dir}/运行库安装包"
if not os.path.exists(runtime_dir):
    os.makedirs(runtime_dir)

# 下载VC++运行库（如果有需要可以手动放进去）
with open(f"{runtime_dir}/VC++运行库下载地址.txt", "w", encoding="utf-8") as f:
    f.write("VC++ 2015-2022 Redistributable (x64)\n")
    f.write("下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe\n")
    f.write("\n安装说明：\n")
    f.write("1. 先安装vc_redist.x64.exe\n")
    f.write("2. 安装完成后再运行easyChat.exe\n")

# 压缩成zip包
with zipfile.ZipFile("easyChat便携版.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
    # 遍历目录添加文件
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, output_dir)
            zipf.write(file_path, arcname)

# 清理临时目录
shutil.rmtree(output_dir)

print("便携版打包完成！生成文件：easyChat便携版.zip")
print("使用方法：")
print("1. 解压easyChat便携版.zip")
print("2. 先安装运行库目录下的VC++运行库")
print("3. 然后运行easyChat.exe")
