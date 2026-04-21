"""
设备完整配置读取模块
用于获取华为网络设备的完整配置信息
"""
import socket
import time
import re
import logging

logger = logging.getLogger(__name__)

PROMPT_PATTERN = re.compile(r'[<\[][^\s\]>]+[>\]]')

def _is_prompt_line(line):
    stripped = line.strip()
    if not stripped:
        return False
    if PROMPT_PATTERN.search(stripped):
        return True
    if stripped.endswith('#') or stripped.endswith('>'):
        return True
    return False

def _flush_buffer(client, timeout=1):
    client.settimeout(timeout)
    try:
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            text = chunk.decode('ascii', errors='ignore')
            if '---- More ----' in text:
                client.sendall(b" ")
                time.sleep(0.05)
    except socket.timeout:
        pass

def _handle_more_prompt(client, output_so_far=b'', timeout=8):
    output = output_so_far
    client.settimeout(timeout)
    start = time.time()
    while time.time() - start < timeout:
        try:
            chunk = client.recv(4096)
            if not chunk:
                break
            output += chunk
            text = output.decode('ascii', errors='ignore')
            if '---- More ----' in text:
                client.sendall(b" ")
                time.sleep(0.05)
                continue
            lines = text.strip().split('\n')
            if lines and _is_prompt_line(lines[-1]):
                # 再读取一次，确保获取完整配置
                time.sleep(0.1)
                try:
                    chunk = client.recv(4096)
                    if chunk:
                        output += chunk
                except socket.timeout:
                    pass
                break
        except socket.timeout:
            break
    # 过滤掉所有 ---- More ---- 字符串
    result = output.decode('ascii', errors='ignore')
    result = result.replace('---- More ----', '')
    return result

def _send_and_wait(client, cmd, timeout=8):
    client.sendall(cmd.encode('ascii') + b"\n")
    return _handle_more_prompt(client, timeout=timeout)

def _ensure_user_view(client):
    client.sendall(b"\n")
    time.sleep(0.2)
    output = _handle_more_prompt(client, timeout=3)
    lines = output.strip().split('\n') if output.strip() else ['']
    last_line = lines[-1] if lines else ''
    if _is_prompt_line(last_line) and not last_line.strip().startswith('<'):
        for _ in range(5):
            client.sendall(b"quit\n")
            time.sleep(0.1)
            out = _handle_more_prompt(client, timeout=2)
            last = out.strip().split('\n')[-1] if out.strip() else ''
            if last.strip().startswith('<') or last.strip().endswith('>'):
                break
    _flush_buffer(client)


def get_full_device_config(port):
    """获取设备完整配置信息"""
    host = "127.0.0.1"
    logger.info(f'开始获取设备完整配置信息: 主机={host}, 端口={port}')

    max_retries = 3
    retry_interval = 1

    for attempt in range(max_retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10.0)
            client.connect((host, port))
            logger.info(f'设备连接成功 (尝试 {attempt + 1}/{max_retries})')

            _flush_buffer(client)
            _ensure_user_view(client)

            _send_and_wait(client, "system-view", timeout=5)
            _send_and_wait(client, "screen-length 0 temporary", timeout=5)
            _send_and_wait(client, "quit", timeout=5)

            full_config = {
                "device_basic": {},
                "hardware_info": {},
                "system_info": {},
                "network_config": {},
                "software_version": {},
                "interface_config": [],
                "routing_config": {},
                "vlan_config": {},
                "acl_config": {},
                "security_config": {},
                "other_config": {}
            }

            commands_info = [
                ("display version", "software_version"),
                ("display device", "hardware_info"),
                ("display cpu-usage", "system_info"),
                ("display memory-usage", "system_info"),
                ("display ip interface brief", "interface_config"),
                ("display interface brief", "interface_config"),
                ("display vlan", "vlan_config"),
                ("display ip routing-table", "routing_config"),
                ("display current-configuration", "full_config"),
            ]

            for cmd, info_type in commands_info:
                try:
                    if cmd == "display current-configuration":
                        _send_and_wait(client, "system-view", timeout=5)
                        _send_and_wait(client, "screen-length 0 temporary", timeout=5)
                        output = _send_and_wait(client, cmd, timeout=30)
                        quit_output = _send_and_wait(client, "return", timeout=5)
                        output = output + "\n" + quit_output
                    else:
                        output = _send_and_wait(client, cmd, timeout=10)
                    parsed_info = _parse_device_output(output, info_type)
                    if info_type == "full_config":
                        full_config["other_config"]["full_running_config"] = parsed_info
                    else:
                        full_config[info_type] = parsed_info
                except Exception as cmd_err:
                    logger.warning(f'获取 {cmd} 信息失败: {str(cmd_err)}')

            try:
                hostname_output = _send_and_wait(client, "display current-configuration | include sysname", timeout=5)
                for line in hostname_output.splitlines():
                    line = line.strip()
                    if line.startswith('sysname'):
                        full_config["device_basic"]["hostname"] = line.split('sysname ')[1].strip()
                        break
            except Exception as e:
                logger.warning(f'获取主机名失败: {str(e)}')

            try:
                snmp_output = _send_and_wait(client, "display snmp-agent sys-info", timeout=5)
                full_config["device_basic"]["snmp_info"] = _parse_snmp_info(snmp_output)
            except Exception as e:
                logger.warning(f'获取SNMP信息失败: {str(e)}')

            client.close()
            logger.info('设备完整配置信息获取成功')
            return {
                "status": "success",
                "config": full_config,
                "port": port
            }

        except ConnectionRefusedError:
            logger.error(f'连接被拒绝: 端口={port} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                return {
                    "status": "error",
                    "msg": f"连接被拒绝！请确认 eNSP 中设备已启动(绿色)。端口: {port}",
                    "port": port
                }
        except socket.timeout:
            logger.error(f'连接超时: 端口={port} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                return {
                    "status": "error",
                    "msg": f"连接超时！请确认 eNSP 中设备已启动且可访问。端口: {port}",
                    "port": port
                }
        except Exception as e:
            logger.error(f'获取设备完整配置信息异常: {str(e)} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                return {
                    "status": "error",
                    "msg": str(e),
                    "port": port
                }


def _parse_device_output(output, info_type):
    """解析设备输出信息"""
    lines = output.splitlines()
    parsed_data = []

    if info_type == "interface_config":
        interface_pattern = re.compile(r'^(GigabitEthernet|Ethernet|Serial|Loopback|Vlanif|Tunnel|MEth|NULL|10GE|40GE|100GE|XGigabitEthernet|FortyGigE|GE)(\S*)')
        vlan_port_pattern = re.compile(r'.*\(U\)|.*\(D\)|.*\(TG\)|.*\(UT\)')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('Interface') or line.startswith('----') or line.startswith('PHY:') or line.startswith('Error'):
                continue
            if line.startswith('<') or line.startswith('['):
                continue
            if 'display' in line.lower() or 'more' in line.lower():
                continue
            if vlan_port_pattern.match(line):
                continue
            parts = line.split()
            if len(parts) >= 2:
                intf_match = interface_pattern.match(line)
                if intf_match:
                    parsed_data.append({
                        "interface": intf_match.group(1) + intf_match.group(2),
                        "status": parts[1] if len(parts) > 1 else "",
                        "protocol": parts[2] if len(parts) > 2 else "",
                        "input_packets": parts[3] if len(parts) > 3 else "",
                        "output_packets": parts[4] if len(parts) > 4 else ""
                    })
                elif parts[0] in ['GigabitEthernet', 'Ethernet', 'Serial', 'Loopback', 'Vlanif', 'GE', '10GE', '40GE', '100GE']:
                    parsed_data.append({
                        "interface": parts[0] + (parts[1] if len(parts) > 1 else ""),
                        "status": parts[2] if len(parts) > 2 else "",
                        "protocol": parts[3] if len(parts) > 3 else "",
                        "input_packets": parts[4] if len(parts) > 4 else "",
                        "output_packets": parts[5] if len(parts) > 5 else ""
                    })
        return parsed_data

    elif info_type == "software_version":
        version_info = {}
        for line in lines:
            line = line.strip()
            if 'VRP' in line:
                version_info['vrp_version'] = line
            if 'Software Version' in line:
                version_info['software_version'] = line.split('Software Version')[-1].strip() if 'Software Version' in line else ""
            if 'Board Type' in line:
                version_info['board_type'] = line.split('Board Type')[-1].strip() if 'Board Type' in line else ""
            if 'Huawei' in line:
                version_info['vendor'] = 'Huawei'
        return version_info if version_info else {"raw_info": output}

    elif info_type == "hardware_info":
        hw_info = []
        current_hw = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Slot') or line.startswith('----'):
                continue
            if 'Slot' in line and 'SubCard' not in line:
                if current_hw:
                    hw_info.append(current_hw)
                current_hw = {"slot": line}
            elif line.startswith('P') and '-' in line:
                parts = line.split()
                if len(parts) >= 3:
                    current_hw['port'] = parts[0]
                    current_hw['status'] = parts[1]
                    current_hw['type'] = ' '.join(parts[2:])
        if current_hw:
            hw_info.append(current_hw)
        return hw_info if hw_info else {"raw_info": output}

    elif info_type == "system_info":
        sys_info = {}
        for line in lines:
            line = line.strip()
            if 'CPU' in line:
                sys_info['cpu_usage'] = line
            if 'Memory' in line:
                sys_info['memory_usage'] = line
            if 'Flash' in line:
                sys_info['flash_usage'] = line
        return sys_info if sys_info else {"raw_info": output}

    elif info_type == "vlan_config":
        vlan_info = {}
        for line in lines:
            line = line.strip()
            if line.startswith('VLAN'):
                parts = line.split()
                if len(parts) >= 2:
                    vlan_id = parts[1].replace(':', '')
                    vlan_info[vlan_id] = {"raw": line}
        return vlan_info if vlan_info else {"raw_info": output}

    elif info_type == "routing_config":
        routing_info = {"static": [], "dynamic": [], "direct": []}
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Route Flags') or line.startswith('----'):
                continue
            if 'Static' in line:
                routing_info["static"].append(line)
            elif 'Ospf' in line or 'RIP' in line or 'BGP' in line:
                routing_info["dynamic"].append(line)
            elif 'Direct' in line:
                routing_info["direct"].append(line)
        return routing_info if routing_info else {"raw_info": output}

    else:
        config_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('display '):
                continue
            if '---- More ----' in line:
                continue
            if line.startswith('<') or line.startswith('['):
                if '#' in line or '>' in line:
                    continue
                if 'Error' in line:
                    continue
                if 'return' in line:
                    continue
            if 'Error' in line and len(line) < 30:
                continue
            if '^' in line:
                continue
            config_lines.append(line)
        return '\n'.join(config_lines)


def _parse_snmp_info(output):
    """解析SNMP信息"""
    snmp_info = {}
    for line in output.splitlines():
        line = line.strip()
        if 'Community' in line:
            snmp_info['community'] = line
        if 'Contact' in line:
            snmp_info['contact'] = line
        if 'Location' in line:
            snmp_info['location'] = line
        if 'Device Type' in line:
            snmp_info['device_type'] = line
    return snmp_info if snmp_info else {"raw_info": output}


def get_detailed_device_info(port):
    """获取设备详细信息（简化的完整配置）"""
    host = "127.0.0.1"
    logger.info(f'开始获取设备详细信息: 主机={host}, 端口={port}')

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10.0)
        client.connect((host, port))
        logger.info(f'设备连接成功')

        _flush_buffer(client)
        _ensure_user_view(client)

        _send_and_wait(client, "system-view", timeout=5)
        _send_and_wait(client, "screen-length 0 temporary", timeout=5)
        _send_and_wait(client, "quit", timeout=5)

        device_info = {
            "basic_info": {},
            "version_info": {},
            "resource_info": {},
            "interface_info": [],
            "routing_summary": {}
        }

        version_output = _send_and_wait(client, "display version", timeout=10)
        version_lines = version_output.splitlines()
        for line in version_lines:
            line = line.strip()
            if 'Huawei' in line:
                device_info["basic_info"]["vendor"] = 'Huawei'
            if 'VRP' in line and 'Software Version' in line:
                device_info["version_info"]["vrp"] = line
            if 'Board Type' in line:
                device_info["version_info"]["board_type"] = line.split('Board Type')[-1].strip() if 'Board Type' in line else ""

        cpu_output = _send_and_wait(client, "display cpu-usage", timeout=5)
        device_info["resource_info"]["cpu"] = cpu_output.strip()

        memory_output = _send_and_wait(client, "display memory-usage", timeout=5)
        device_info["resource_info"]["memory"] = memory_output.strip()

        intf_output = _send_and_wait(client, "display interface brief", timeout=10)
        intf_lines = intf_output.splitlines()
        for line in intf_lines:
            line = line.strip()
            if not line or line.startswith('Interface') or line.startswith('----'):
                continue
            if any(kw in line for kw in ['PHY:', 'Error', 'InUti']):
                continue
            if line.startswith('<') or line.startswith('['):
                continue
            parts = line.split()
            if len(parts) >= 2:
                device_info["interface_info"].append({
                    "name": parts[0],
                    "status": parts[1] if len(parts) > 1 else "",
                    "protocol": parts[2] if len(parts) > 2 else ""
                })

        route_output = _send_and_wait(client, "display ip routing-table", timeout=10)
        device_info["routing_summary"]["total_routes"] = len([l for l in route_output.splitlines() if l.strip() and not l.startswith('Route')])

        client.close()
        logger.info('设备详细信息获取成功')
        return {
            "status": "success",
            "device_info": device_info,
            "port": port
        }

    except ConnectionRefusedError:
        logger.error(f'连接被拒绝: 端口={port}')
        return {
            "status": "error",
            "msg": f"连接被拒绝！请确认 eNSP 中设备已启动(绿色)。端口: {port}",
            "port": port
        }
    except socket.timeout:
        logger.error(f'连接超时: 端口={port}')
        return {
            "status": "error",
            "msg": f"连接超时！请确认 eNSP 中设备已启动且可访问。端口: {port}",
            "port": port
        }
    except Exception as e:
        logger.error(f'获取设备详细信息异常: {str(e)}')
        return {
            "status": "error",
            "msg": str(e),
            "port": port
        }


def get_device_diagnostics(port):
    """获取设备诊断信息"""
    host = "127.0.0.1"
    logger.info(f'开始获取设备诊断信息: 主机={host}, 端口={port}')

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10.0)
        client.connect((host, port))

        _flush_buffer(client)
        _ensure_user_view(client)

        _send_and_wait(client, "system-view", timeout=5)
        _send_and_wait(client, "screen-length 0 temporary", timeout=5)
        _send_and_wait(client, "quit", timeout=5)

        diagnostics = {
            "power_status": [],
            "temperature_status": [],
            "fan_status": [],
            "log_info": [],
            "error_info": []
        }

        power_output = _send_and_wait(client, "display power", timeout=5)
        for line in power_output.splitlines():
            line = line.strip()
            if line and not line.startswith('Power'):
                diagnostics["power_status"].append(line)

        temp_output = _send_and_wait(client, "display temperature", timeout=5)
        for line in temp_output.splitlines():
            line = line.strip()
            if line and not line.startswith('Temperature'):
                diagnostics["temperature_status"].append(line)

        fan_output = _send_and_wait(client, "display fan", timeout=5)
        for line in fan_output.splitlines():
            line = line.strip()
            if line and not line.startswith('Fan'):
                diagnostics["fan_status"].append(line)

        log_output = _send_and_wait(client, "display logbuffer", timeout=5)
        log_lines = log_output.splitlines()
        for i, line in enumerate(log_lines):
            if 'Error' in line or '告警' in line or 'Alarm' in line:
                diagnostics["error_info"].append(line.strip())

        client.close()
        logger.info('设备诊断信息获取成功')
        return {
            "status": "success",
            "diagnostics": diagnostics,
            "port": port
        }

    except Exception as e:
        logger.error(f'获取设备诊断信息异常: {str(e)}')
        return {
            "status": "error",
            "msg": str(e),
            "port": port
        }


def get_network_topology_info(port):
    """获取网络拓扑相关信息"""
    host = "127.0.0.1"
    logger.info(f'开始获取网络拓扑信息: 主机={host}, 端口={port}')

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10.0)
        client.connect((host, port))

        _flush_buffer(client)
        _ensure_user_view(client)

        _send_and_wait(client, "system-view", timeout=5)
        _send_and_wait(client, "screen-length 0 temporary", timeout=5)
        _send_and_wait(client, "quit", timeout=5)

        topology_info = {
            "cdp_neighbors": [],
            "lldp_neighbors": [],
            "mac_address_table": [],
            "arp_table": [],
            "stp_port_state": []
        }

        cdp_output = _send_and_wait(client, "display ndp", timeout=5)
        for line in cdp_output.splitlines():
            line = line.strip()
            if line and not line.startswith('Port') and not line.startswith('----'):
                topology_info["cdp_neighbors"].append(line)

        mac_output = _send_and_wait(client, "display mac-address", timeout=5)
        mac_lines = mac_output.splitlines()
        for line in mac_lines:
            line = line.strip()
            if line and not line.startswith('MAC Address') and not line.startswith('----'):
                topology_info["mac_address_table"].append(line)

        arp_output = _send_and_wait(client, "display arp", timeout=5)
        arp_lines = arp_output.splitlines()
        for line in arp_lines:
            line = line.strip()
            if line and not line.startswith('IP') and not line.startswith('----'):
                topology_info["arp_table"].append(line)

        stp_output = _send_and_wait(client, "display stp brief", timeout=5)
        for line in stp_output.splitlines():
            line = line.strip()
            if line and not line.startswith('MSTID') and not line.startswith('----'):
                topology_info["stp_port_state"].append(line)

        client.close()
        logger.info('网络拓扑信息获取成功')
        return {
            "status": "success",
            "topology": topology_info,
            "port": port
        }

    except Exception as e:
        logger.error(f'获取网络拓扑信息异常: {str(e)}')
        return {
            "status": "error",
            "msg": str(e),
            "port": port
        }