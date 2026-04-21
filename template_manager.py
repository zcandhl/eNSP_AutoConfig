import os
import json
import time
import logging
from flask import request, jsonify

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'data', 'config_templates')


def init_templates_dir():
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR)
        logger.info(f'创建模板存储目录: {TEMPLATES_DIR}')


def register_template_routes(app):
    init_templates_dir()

    @app.route('/api/save_template', methods=['POST'])
    def save_template():
        try:
            logger.info('开始保存配置模板')
            data = request.json
            template_name = data.get('name')
            tech = data.get('tech')
            params = data.get('params')

            if not template_name or not tech or not params:
                logger.warning('缺少模板名称、技术类型或参数')
                return jsonify({"status": "error", "msg": "缺少模板名称、技术类型或参数"})

            if not isinstance(params, dict):
                logger.error('参数类型错误，应为字典')
                return jsonify({"status": "error", "msg": "参数类型错误，应为字典"})

            template_data = {
                'name': template_name,
                'tech': tech,
                'params': params,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            template_file = os.path.join(TEMPLATES_DIR, f'{template_name}.json')
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)

            logger.info(f'模板保存成功: {template_name}')
            return jsonify({"status": "success", "msg": "模板保存成功"})
        except Exception as e:
            logger.error(f'保存模板异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"保存模板异常: {str(e)}"})

    @app.route('/api/load_templates', methods=['GET'])
    def load_templates():
        try:
            logger.info('开始加载配置模板列表')
            templates = []

            if os.path.exists(TEMPLATES_DIR):
                for filename in os.listdir(TEMPLATES_DIR):
                    if filename.endswith('.json'):
                        template_file = os.path.join(TEMPLATES_DIR, filename)
                        try:
                            with open(template_file, 'r', encoding='utf-8') as f:
                                template_data = json.load(f)
                                templates.append(template_data)
                        except Exception as e:
                            logger.error(f'加载模板文件失败: {filename}, 错误: {str(e)}')

            logger.info(f'模板列表加载完成，共 {len(templates)} 个模板')
            return jsonify({"status": "success", "data": templates})
        except Exception as e:
            logger.error(f'加载模板列表异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"加载模板列表异常: {str(e)}"})

    @app.route('/api/delete_template', methods=['POST'])
    def delete_template():
        try:
            logger.info('开始删除配置模板')
            data = request.json
            template_name = data.get('name')

            if not template_name:
                logger.warning('缺少模板名称')
                return jsonify({"status": "error", "msg": "缺少模板名称"})

            template_file = os.path.join(TEMPLATES_DIR, f'{template_name}.json')
            if os.path.exists(template_file):
                os.remove(template_file)
                logger.info(f'模板删除成功: {template_name}')
                return jsonify({"status": "success", "msg": "模板删除成功"})
            else:
                logger.warning(f'模板文件不存在: {template_name}')
                return jsonify({"status": "error", "msg": "模板文件不存在"})
        except Exception as e:
            logger.error(f'删除模板异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"删除模板异常: {str(e)}"})
