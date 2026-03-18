import os


# 用来自动打包成exe程序
def main():
    # 排除不需要的大体积依赖，减小体积，加快打包速度
    excludes = [
        'torch', 'torchvision', 'torchaudio',
        'scipy', 'matplotlib', 'tkinter', 'jupyter',
        'fsspec', 'jinja2', 'urllib3',
        'certifi', 'charset_normalizer',
        'cv2', 'pytest'
    ]
    
    exclude_args = ' '.join([f'--exclude-module={mod}' for mod in excludes])
    
    cmd = f"pyinstaller.exe -Fw {exclude_args} wechat_gui_momo.py"

    print(f"执行打包命令: {cmd}")
    # 执行命令并打印输出
    result = os.system(cmd)


if __name__ == '__main__':
    main()
