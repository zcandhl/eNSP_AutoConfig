import os
import json
import time
import logging
from flask import request, jsonify

logger = logging.getLogger(__name__)

HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'data', 'history')
HISTORY_FILE = os.path.join(HISTORY_DIR, 'operation_history.json')


def init_history_dir():
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
        logger.info(f'创建历史记录存储目录: {HISTORY_DIR}')
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        logger.info(f'创建历史记录文件: {HISTORY_FILE}')


def register_history_routes(app):
    init_history_dir()

    @app.route('/api/add_history', methods=['POST'])
    def add_history():
        try:
            logger.info('开始添加操作历史记录')
            data = request.json
            operation = data.get('operation')
            details = data.get('details', {})

            if not operation:
                logger.warning('缺少操作类型')
                return jsonify({"status": "error", "msg": "缺少操作类型"})

            history_record = {
                'id': str(int(time.time() * 1000)),
                'operation': operation,
                'details': details,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)

            history.insert(0, history_record)

            if len(history) > 100:
                history = history[:100]

            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

            logger.info(f'操作历史记录添加成功: {operation}')
            return jsonify({"status": "success", "msg": "操作历史记录添加成功"})
        except Exception as e:
            logger.error(f'添加操作历史记录异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"添加操作历史记录异常: {str(e)}"})

    @app.route('/api/get_history', methods=['GET'])
    def get_history():
        try:
            logger.info('开始获取操作历史记录')

            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)

            logger.info(f'操作历史记录获取成功，共 {len(history)} 条')
            return jsonify({"status": "success", "data": history})
        except Exception as e:
            logger.error(f'获取操作历史记录异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"获取操作历史记录异常: {str(e)}"})

    @app.route('/api/clear_history', methods=['POST'])
    def clear_history():
        try:
            logger.info('开始清空操作历史记录')

            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

            logger.info('操作历史记录清空成功')
            return jsonify({"status": "success", "msg": "操作历史记录清空成功"})
        except Exception as e:
            logger.error(f'清空操作历史记录异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"清空操作历史记录异常: {str(e)}"})
