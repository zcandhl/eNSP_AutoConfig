import os
import sys
import threading
import webbrowser
import time
import tempfile
import logging
from flask import Flask, render_template, request, jsonify
from core_logic import parse_topo, generate_config, push_to_device, get_device_interfaces, classify_device, get_available_techs, get_device_config, save_device_config, read_current_params, validate_params, check_device_status
from device_info_reader import get_full_device_config, get_detailed_device_info, get_device_diagnostics, get_network_topology_info
from ai_handler import register_ai_routes
from template_manager import register_template_routes
from history_manager import register_history_routes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

register_ai_routes(app)
register_template_routes(app)
register_history_routes(app)

# 注册核心API路由
@app.route('/api/upload_topo', methods=['POST'])
def upload_topo():
    try:
        logger.info('开始处理拓扑文件上传')
        if 'file' not in request.files:
            logger.warning('上传请求中没有文件')
            return jsonify({"status": "error", "msg": "没有文件"})
        file = request.files['file']
        if file.filename == '':
            logger.warning('未选择文件')
            return jsonify({"status": "error", "msg": "未选择文件"})

        MAX_FILE_SIZE = 10 * 1024 * 1024
        if file.content_length and file.content_length > MAX_FILE_SIZE:
            logger.warning(f'文件过大: {file.content_length} bytes')
            return jsonify({"status": "error", "msg": "文件大小超过限制（最大10MB）"})

        allowed_extensions = {'.topo', '.xml', '.zip'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            logger.warning(f'文件类型不允许: {ext}')
            return jsonify({"status": "error", "msg": "文件类型不允许，仅支持 .topo、.xml、.zip 文件"})

        logger.info(f'接收到文件: {file.filename}, 大小: {file.content_length} bytes, 类型: {ext}')
        temp_dir = tempfile.gettempdir()
        temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False, dir=temp_dir)
        temp_path = temp_file.name
        temp_file.close()

        file.save(temp_path)
        logger.info(f'文件保存到临时路径: {temp_path}')

        result = parse_topo(temp_path)
        logger.info(f'拓扑解析结果: {result}')

        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info('临时文件已删除')

        if result.get('status') == 'success' and 'data' in result:
            for dev in result['data']:
                dev['category'] = classify_device(dev.get('type', ''))
                dev['available_techs'] = get_available_techs(dev.get('type', ''))

        return jsonify(result)
    except Exception as e:
        logger.error(f'上传处理异常: {str(e)}')
        return jsonify({"status": "error", "msg": f"上传处理异常: {str(e)}"})

@app.route('/api/validate_config', methods=['POST'])
def validate_config():
    try:
        logger.info('开始处理配置验证')
        data = request.json
        tech = data.get('tech')
        params = data.get('params', {})
        logger.info(f'配置验证参数: 技术={tech}, 参数={params}')
        if not tech:
            logger.warning('缺少技术类型参数')
            return jsonify({"status": "error", "msg": "缺少技术类型参数"})
        validation = validate_params(tech, params)
        logger.info(f'配置验证结果: {validation}')
        return jsonify(validation)
    except Exception as e:
        logger.error(f'配置验证异常: {str(e)}')
        return jsonify({"status": "error", "msg": f"配置验证异常: {str(e)}"})

@app.route('/api/preview_config', methods=['POST'])
def preview_config():
    try:
        logger.info('开始处理配置预览')
        data = request.json
        tech = data.get('tech')
        params = data.get('params', {})
        dev_cat = 'unknown'
        device_type = data.get('device_type', '')
        if device_type:
            dev_cat = classify_device(device_type)
        logger.info(f'配置预览参数: 技术={tech}, 设备类别={dev_cat}, 参数={params}')
        if not tech:
            logger.warning('缺少技术类型参数')
            return jsonify({"status": "error", "msg": "缺少技术类型参数"})
        commands = generate_config(tech, params, dev_cat, preview=True)
        if commands.startswith("// 错误"):
            logger.warning(f'配置生成失败: {commands}')
            return jsonify({"status": "error", "msg": commands})
        logger.info('配置预览生成成功')
        return jsonify({"status": "success", "config": commands})
    except Exception as e:
        logger.error(f'配置预览异常: {str(e)}')
        return jsonify({"status": "error", "msg": f"配置预览异常: {str(e)}"})

@app.route('/api/push_config', methods=['POST'])
def push_config():
    try:
        logger.info('开始处理配置推送')
        data = request.json
        port = data.get('port')
        tech = data.get('tech')
        params = data.get('params', {})
        dev_cat = 'unknown'
        device_type = data.get('device_type', '')
        if device_type:
            dev_cat = classify_device(device_type)
        logger.info(f'配置推送参数: 端口={port}, 技术={tech}, 设备类别={dev_cat}, 参数={params}')
        if not port or not tech:
            logger.warning('缺少必要参数')
            return jsonify({"status": "error", "msg": "缺少必要参数"})
        commands = generate_config(tech, params, dev_cat)
        if not commands or commands.startswith("// 错误"):
            logger.warning(f'配置生成失败: {commands}')
            return jsonify({"status": "error", "msg": commands or "配置生成失败，请检查参数"})
        logger.info('配置命令生成成功')
        result = push_to_device(port, commands)
        logger.info(f'配置推送结果: {result}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'服务器内部错误: {str(e)}')
        return jsonify({"status": "error", "msg": f"服务器内部错误: {str(e)}"})

@app.route('/api/get_interfaces', methods=['POST'])
def get_interfaces_route():
    try:
        logger.info('开始获取设备接口列表')
        data = request.json
        port = data.get('port')
        logger.info(f'获取接口列表参数: 端口={port}')
        if not port:
            logger.warning('未指定设备端口')
            return jsonify({"status": "error", "msg": "未指定设备端口"})
        result = get_device_interfaces(port)
        logger.info(f'接口列表获取结果: {result}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'获取接口列表异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/get_config', methods=['POST'])
def get_config():
    try:
        logger.info('开始读取设备完整配置')
        data = request.json
        port = data.get('port')
        if not port:
            return jsonify({"status": "error", "msg": "缺少端口参数"})
        result = get_full_device_config(int(port))
        logger.info(f'设备完整配置读取结果: {result.get("status")}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'读取设备配置异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/push_custom_config', methods=['POST'])
def push_custom_config():
    try:
        data = request.json
        port = data.get('port')
        commands = data.get('commands', '')
        if not port or not commands:
            return jsonify({"status": "error", "msg": "缺少端口或命令参数"})
        result = push_to_device(int(port), commands)
        return jsonify(result)
    except Exception as e:
        logger.error(f'推送自定义配置异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/batch_push_config', methods=['POST'])
def batch_push_config():
    try:
        logger.info('开始处理批量配置推送')
        data = request.json
        devices = data.get('devices', [])
        tech = data.get('tech')
        params = data.get('params', {})
        if not devices or not tech:
            logger.warning('缺少设备列表或技术类型参数')
            return jsonify({"status": "error", "msg": "缺少设备列表或技术类型参数"})
        logger.info(f'批量配置参数: 设备数量={len(devices)}, 技术={tech}, 参数={params}')
        results = []
        for device in devices:
            port = device.get('port')
            device_type = device.get('device_type', '')
            dev_cat = 'unknown'
            if device_type:
                dev_cat = classify_device(device_type)
            commands = generate_config(tech, params, dev_cat)
            if commands.startswith("// 错误"):
                results.append({
                    "port": port,
                    "device_name": device.get('name', f'设备{port}'),
                    "status": "error",
                    "msg": commands
                })
                continue
            result = push_to_device(port, commands)
            results.append({
                "port": port,
                "device_name": device.get('name', f'设备{port}'),
                "status": result.get('status'),
                "log": result.get('log')
            })
        logger.info(f'批量配置完成，共处理 {len(devices)} 个设备')
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        logger.error(f'批量配置推送异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/check_device_status', methods=['POST'])
def check_device_status_route():
    try:
        logger.info('开始处理设备状态检查')
        data = request.json
        port = data.get('port')
        ports = data.get('ports', [])
        if port:
            # 检查单个设备状态
            result = check_device_status(port)
            logger.info(f'设备状态检查结果: {result}')
            return jsonify(result)
        elif ports:
            # 批量检查设备状态
            results = []
            for p in ports:
                result = check_device_status(p)
                results.append(result)
            logger.info(f'批量设备状态检查完成，共检查 {len(ports)} 个设备')
            return jsonify({"status": "success", "results": results})
        else:
            logger.warning('缺少端口参数')
            return jsonify({"status": "error", "msg": "缺少端口参数"})
    except Exception as e:
        logger.error(f'设备状态检查异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/save_device_config', methods=['POST'])
def save_config():
    try:
        data = request.json
        port = data.get('port')
        if not port:
            return jsonify({"status": "error", "msg": "缺少端口参数"})
        result = save_device_config(int(port))
        return jsonify(result)
    except Exception as e:
        logger.error(f'保存设备配置异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/read_current_params', methods=['POST'])
def read_params():
    try:
        data = request.json
        port = data.get('port')
        tech = data.get('tech')
        if not port or not tech:
            return jsonify({"status": "error", "msg": "缺少端口或技术类型参数"})
        result = read_current_params(int(port), tech)
        return jsonify(result)
    except Exception as e:
        logger.error(f'读取配置参数异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/get_full_config', methods=['POST'])
def get_full_config():
    try:
        logger.info('开始获取设备完整配置信息')
        data = request.json
        port = data.get('port')
        if not port:
            return jsonify({"status": "error", "msg": "缺少端口参数"})
        result = get_full_device_config(int(port))
        logger.info(f'设备完整配置信息获取结果: {result.get("status")}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'获取设备完整配置异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/get_detailed_info', methods=['POST'])
def get_detailed_info():
    try:
        logger.info('开始获取设备详细信息')
        data = request.json
        port = data.get('port')
        if not port:
            return jsonify({"status": "error", "msg": "缺少端口参数"})
        result = get_detailed_device_info(int(port))
        logger.info(f'设备详细信息获取结果: {result.get("status")}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'获取设备详细信息异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/get_diagnostics', methods=['POST'])
def get_diagnostics():
    try:
        logger.info('开始获取设备诊断信息')
        data = request.json
        port = data.get('port')
        if not port:
            return jsonify({"status": "error", "msg": "缺少端口参数"})
        result = get_device_diagnostics(int(port))
        logger.info(f'设备诊断信息获取结果: {result.get("status")}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'获取设备诊断信息异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/get_topology_info', methods=['POST'])
def get_topology_info():
    try:
        logger.info('开始获取网络拓扑信息')
        data = request.json
        port = data.get('port')
        if not port:
            return jsonify({"status": "error", "msg": "缺少端口参数"})
        result = get_network_topology_info(int(port))
        logger.info(f'网络拓扑信息获取结果: {result.get("status")}')
        return jsonify(result)
    except Exception as e:
        logger.error(f'获取网络拓扑信息异常: {str(e)}')
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/')
def index():
    return render_template('index.html')


def start_flask():
    logger.info('Flask服务开始启动')
    try:
        app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f'Flask服务启动失败: {str(e)}')


def run_with_window():
    logger.info('开始启动带状态窗口的应用')
    try:
        import tkinter as tk
        from tkinter import messagebox, font as tkfont
        logger.info('Tkinter模块导入成功')
    except ImportError:
        logger.warning('Tkinter模块导入失败，将以无窗口模式启动')
        threading.Thread(target=start_flask, daemon=True).start()
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:5001")
        logger.info('浏览器已打开')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info('用户中断程序')
            os._exit(0)
        return

    BG_COLOR = "#1a2332"
    BG_LIGHT = "#253347"
    FG_COLOR = "#c8d6e5"
    ACCENT = "#409eff"
    SUCCESS = "#67c23a"
    DANGER = "#f56c6c"
    DIM_COLOR = "#6a8a9a"

    root = tk.Tk()
    root.title("eNSP 自动化配置助手 v1.2")
    root.geometry("460x320")
    root.resizable(False, False)
    root.configure(bg=BG_COLOR)
    root.eval('tk::PlaceWindow . center')

    try:
        root.iconbitmap(default='')
    except Exception as e:
        logger.warning(f'图标加载失败: {str(e)}')

    header = tk.Frame(root, bg=BG_LIGHT, height=60)
    header.pack(fill=tk.X)
    header.pack_propagate(False)

    title_label = tk.Label(header, text="eNSP 自动化配置助手 v1.2",
                           font=("Microsoft YaHei", 14, "bold"),
                           fg=ACCENT, bg=BG_LIGHT)
    title_label.pack(pady=(12, 0))

    subtitle_label = tk.Label(header, text="华为网络设备自动化配置工具",
                              font=("Microsoft YaHei", 9), fg=DIM_COLOR, bg=BG_LIGHT)
    subtitle_label.pack(pady=(0, 8))

    body = tk.Frame(root, bg=BG_COLOR)
    body.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

    status_icon = tk.Label(body, text="...", font=("Segoe UI Emoji", 20),
                           fg=DIM_COLOR, bg=BG_COLOR)
    status_icon.pack(pady=(8, 4))

    status_label = tk.Label(body, text="正在启动服务...",
                            font=("Microsoft YaHei", 12, "bold"),
                            fg=FG_COLOR, bg=BG_COLOR)
    status_label.pack(pady=2)

    info_label = tk.Label(body, text="请稍候...",
                          font=("Microsoft YaHei", 9), fg=DIM_COLOR, bg=BG_COLOR)
    info_label.pack(pady=2)

    url_label = tk.Label(body, text="", font=("Consolas", 10),
                         fg=ACCENT, bg=BG_COLOR, cursor="hand2")
    url_label.pack(pady=4)

    def on_url_click(event):
        webbrowser.open("http://127.0.0.1:5001")

    url_label.bind("<Button-1>", on_url_click)

    btn_frame = tk.Frame(body, bg=BG_COLOR)
    btn_frame.pack(pady=8)

    open_btn = tk.Button(btn_frame, text="  打开浏览器  ",
                         font=("Microsoft YaHei", 10),
                         bg=ACCENT, fg="white", relief=tk.FLAT,
                         activebackground="#66b1ff", activeforeground="white",
                         cursor="hand2", command=lambda: webbrowser.open("http://127.0.0.1:5001"))
    open_btn.pack(side=tk.LEFT, padx=6)

    stop_btn = tk.Button(btn_frame, text="  停止服务  ",
                         font=("Microsoft YaHei", 10),
                         bg=DANGER, fg="white", relief=tk.FLAT,
                         activebackground="#f78989", activeforeground="white",
                         cursor="hand2", command=lambda: on_close())
    stop_btn.pack(side=tk.LEFT, padx=6)

    footer = tk.Label(root, text="端口: 5001 | 主机: 127.0.0.1",
                      font=("Microsoft YaHei", 8), fg=DIM_COLOR, bg=BG_LIGHT)
    footer.pack(fill=tk.X, side=tk.BOTTOM, pady=4)

    def on_close():
        if messagebox.askokcancel("退出", "确定要退出程序吗？\n正在进行的配置可能会中断。"):
            root.destroy()
            os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_close)

    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    def check_server():
        logger.info('开始检查服务状态')
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5001))
        if result == 0:
            logger.info('服务启动成功')
            status_icon.config(text="", fg=SUCCESS)
            status_label.config(text="服务已启动", fg=SUCCESS)
            info_label.config(text="点击下方按钮或链接访问配置界面", fg=FG_COLOR)
            url_label.config(text="http://127.0.0.1:5001")
            webbrowser.open("http://127.0.0.1:5001")
        else:
            logger.warning('服务启动失败，端口5001可能被占用')
            status_icon.config(text="", fg=DANGER)
            status_label.config(text="服务启动失败", fg=DANGER)
            info_label.config(text="端口 5001 可能被占用，请检查", fg=DANGER)
            retry_btn = tk.Button(btn_frame, text="  重试  ",
                                  font=("Microsoft YaHei", 10),
                                  bg="#e6a23c", fg="white", relief=tk.FLAT,
                                  cursor="hand2", command=lambda: [retry_btn.destroy(), check_server()])
            retry_btn.pack(side=tk.LEFT, padx=6)
        sock.close()

    root.after(2500, check_server)
    root.mainloop()

if __name__ == '__main__':
    logger.info('应用程序开始启动')
    if getattr(sys, 'frozen', False):
        logger.info('以打包模式启动，使用带状态窗口的启动器')
        run_with_window()
    else:
        logger.info('以开发模式启动')
        threading.Thread(target=start_flask, daemon=True).start()
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:5001")
        logger.info('浏览器已打开')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info('用户中断程序')
            pass
