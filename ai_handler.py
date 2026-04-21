import json
import logging
import socket
import urllib.request
import urllib.error
from flask import request, jsonify

logger = logging.getLogger(__name__)

AI_SYSTEM_PROMPT = """你是华为eNSP网络设备配置专家。根据用户需求生成对应的华为设备配置命令。

规则：
1. 只生成华为VRP系统可执行的配置命令
2. 命令必须从system-view开始，以quit和return结束
3. 确保视图层级正确（如接口视图、OSPF视图等）
4. 交换机物理接口配IP前需先执行undo portswitch
5. 不要添加任何解释性文字，只输出配置命令
6. 如果用户需求不明确，请简要提问"""


def register_ai_routes(app):
    @app.route('/api/ai_generate', methods=['POST'])
    def ai_generate():
        try:
            logger.info('开始处理AI配置生成请求')
            data = request.json
            prompt = data.get('prompt', '')
            base_url = data.get('base_url', '')
            api_key = data.get('api_key', '')
            model = data.get('model', '')
            messages = data.get('messages', [])

            if not prompt:
                return jsonify({"status": "error", "msg": "请输入配置需求"})

            if not base_url or not model:
                return jsonify({"status": "error", "msg": "请先配置AI模型（API URL、模型名称）"})

            if not api_key:
                api_key = 'ollama'

            logger.info(f'AI请求: model={model}, base_url={base_url}')

            chat_messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
            if messages:
                for msg in messages[-10:]:
                    chat_messages.append(msg)
            chat_messages.append({"role": "user", "content": prompt})

            url = base_url.rstrip('/') + '/chat/completions'
            req_body = json.dumps({
                "model": model,
                "messages": chat_messages,
                "temperature": 0.3,
                "max_tokens": 2048
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=req_body,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                method='POST'
            )

            req_timeout = 60
            with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))

            content = ''
            if 'choices' in resp_data and len(resp_data['choices']) > 0:
                choice = resp_data['choices'][0]
                content = choice.get('message', {}).get('content', '')
            elif 'output' in resp_data:
                content = resp_data.get('output', {}).get('text', '')
            else:
                content = json.dumps(resp_data, ensure_ascii=False, indent=2)

            if not content:
                return jsonify({"status": "error", "msg": "AI返回内容为空"})

            logger.info('AI配置生成成功')
            return jsonify({"status": "success", "config": content})

        except urllib.error.HTTPError as e:
            err_body = ''
            try:
                err_body = e.read().decode('utf-8')
            except Exception as read_err:
                logger.warning(f'读取错误响应失败: {str(read_err)}')
            logger.error(f'AI API HTTP错误: {e.code} {err_body}')
            err_msg = f"API返回错误 {e.code}"
            try:
                err_json = json.loads(err_body)
                if 'error' in err_json:
                    err_msg = err_json['error'].get('message', err_msg)
            except Exception as json_err:
                logger.warning(f'解析错误响应JSON失败: {str(json_err)}')
            return jsonify({"status": "error", "msg": err_msg})
        except urllib.error.URLError as e:
            logger.error(f'AI API连接错误: {str(e)}')
            return jsonify({"status": "error", "msg": f"无法连接AI服务，请检查Base URL: {str(e.reason)}"})
        except socket.timeout:
            logger.error('AI API请求超时')
            return jsonify({"status": "error", "msg": "AI服务请求超时，请稍后重试"})
        except Exception as e:
            logger.error(f'AI配置生成异常: {str(e)}')
            return jsonify({"status": "error", "msg": f"AI配置生成异常: {str(e)}"})
