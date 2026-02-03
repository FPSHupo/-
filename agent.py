import os
import clr
import json
import requests
import socket  
import platform  
import psutil  
from datetime import datetime, timezone
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import time
import sys

# 获取当前脚本所在的路径并加载 DLL
clr.AddReference(os.path.join(os.getcwd(), 'OpenHardwareMonitorLib.dll'))  # DLL 在同一目录下
from OpenHardwareMonitor import Hardware

# 目标 API 地址
API_URL = 'http://139.155.143.38:9527/api/report'  # 请根据实际情况修改为后端的 URL

# 获取硬件信息
handle = Hardware.Computer()
handle.CPUEnabled = True  # 启用 CPU 模块
handle.GPUEnabled = True  # 启用 GPU 模块
handle.Open()

# 设置员工ID（先显示窗口让员工输入）
employee_id = None

def ask_employee_id():
    global employee_id
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    while not employee_id:  # 如果员工 ID 为空，循环提示用户输入
        employee_id = simpledialog.askstring("员工ID", "请输入员工ID：")
        
        if not employee_id:
            messagebox.showwarning("输入为空", "请输入员工ID！")  # 如果输入为空，弹出提示框

    root.quit()  # 关闭输入框

ask_employee_id()  # 弹出窗口要求员工输入

# 获取当前电脑的所有 IP 地址
def get_ip_addresses():
    ip_addresses = []
    # 获取所有网络适配器的地址
    addrs = psutil.net_if_addrs()
    for interface, addresses in addrs.items():
        for address in addresses:
            if address.family == socket.AF_INET:  # IPv4 地址
                ip_addresses.append(address.address)
    return ip_addresses

# 创建任务栏图标
def create_image():
    # 生成一个简单的图标
    image = Image.new('RGB', (64, 64), color=(0, 128, 255))
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "监控", fill="white")
    return image

# 退出函数
def on_quit(icon, item):
    print("退出程序...")
    icon.stop()  # 停止任务栏图标
    stop_event.set()  # 设置停止事件标志
    handle.Close()  # 关闭硬件监控

# 设置右键菜单
menu = Menu(MenuItem("退出", on_quit))

# 创建并显示任务栏图标
icon = Icon("Employee Monitor", create_image(), menu=menu)

# 创建一个事件标志，用来停止后台循环
stop_event = threading.Event()

# 准备数据结构
employee_data = {
    "employee": {
        "employee_id": employee_id,  # 使用输入的员工 ID
        "cpu_model": None,
        "gpu_model": None,
        "ip_addresses": get_ip_addresses()  # 获取并加入所有 IP 地址
    },
    "temps": {}
}

# 获取 CPU 型号和 GPU 型号、温度
def get_hardware_info():
    global employee_data
    for hardware in handle.Hardware:
        hardware.Update()  # 更新硬件信息

        if hardware.HardwareType == Hardware.HardwareType.CPU:
            employee_data["employee"]["cpu_model"] = hardware.Name if hardware.Name else None

        elif hardware.HardwareType == Hardware.HardwareType.GpuNvidia or hardware.HardwareType == Hardware.HardwareType.GpuAti:
            employee_data["employee"]["gpu_model"] = hardware.Name if hardware.Name else None
            for sensor in hardware.Sensors:
                if sensor.SensorType == Hardware.SensorType.Temperature and sensor.Value is not None:
                    employee_data["temps"]["gpu_temp"] = sensor.Value if sensor.Value is not None else None

# 获取其他信息（内存和硬盘信息）
def get_system_info():
    system_info = {
        "os": platform.system(),  # 获取操作系统信息
        "memory": {"size_gb": None, "type": "DDR4"},  # 默认 DDR4，您可以修改
        "disk": {"total_gb": None, "type": "HDD"}  # 默认 HDD，您可以修改
    }

    if system_info["os"] == "Windows":
        # 获取内存信息（使用 psutil）
        total_memory = psutil.virtual_memory().total  # 获取内存总大小（字节）
        system_info["memory"]["size_gb"] = round(total_memory / (1024 ** 3)) if total_memory else None  # 转换为 GB 并四舍五入取整

        # 获取硬盘信息
        disk_info = psutil.disk_usage('/').total  # 获取硬盘总大小（字节）
        system_info["disk"]["total_gb"] = round(disk_info / (1024 ** 3)) if disk_info else None  # 转换为 GB 并四舍五入取整
    
    return system_info

# 获取系统信息（内存和硬盘）
def gather_data():
    system_info = get_system_info()
    employee_data["employee"]["memory"] = system_info["memory"]
    employee_data["employee"]["disk"] = system_info["disk"]

    # 获取硬件信息
    get_hardware_info()

    # 获取当前时间戳，使用时区感知的 UTC 时间
    employee_data["last_seen"] = datetime.now(timezone.utc).timestamp()

# 发送数据到后端
def send_data():
    response = requests.post(API_URL, json=employee_data)
    if response.status_code == 200:
        print("员工数据已成功上报！")
    else:
        print(f"上报失败，状态码: {response.status_code}, 错误信息: {response.text}")

# 后台定时上传数据
def background_task():
    while not stop_event.is_set():
        gather_data()
        send_data()
        time.sleep(5)  # 每隔5秒上报一次数据

# 启动后台数据上报线程
background_thread = threading.Thread(target=background_task)
background_thread.daemon = True  # 设置为守护线程，主线程退出时自动关闭
background_thread.start()

# 创建并显示任务栏图标
icon.run()
