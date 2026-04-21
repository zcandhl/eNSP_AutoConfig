# core_logic.py
import zipfile
import xml.etree.ElementTree as ET
import socket
import time
import re
import tempfile
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('core.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== 1. Topo 解析（增强版） ==========
def parse_topo(file_path):
    logger.info(f'开始解析拓扑文件: {file_path}')
    devices = []
    root = None
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        logger.info('文件读取成功')
    except Exception as e:
        logger.error(f'读取文件失败: {str(e)}')
        return {"status": "error", "msg": f"读取文件失败: {str(e)}"}
    
    # 尝试多种编码解码
    xml_text = None
    for enc in ['utf-16', 'utf-8', 'gbk']:
        try:
            xml_text = raw_data.decode(enc)
            if xml_text.startswith('\ufeff'):
                xml_text = xml_text[1:]
            logger.info(f'文件编码识别成功: {enc}')
            break
        except UnicodeDecodeError:
            continue
    if xml_text is None:
        logger.error('无法识别文件编码')
        return {"status": "error", "msg": "无法识别文件编码"}
    
    # 去除 XML 声明
    xml_text = re.sub(r'<\?xml.*?\?>', '', xml_text).strip()
    
    # 尝试解析 XML
    try:
        root = ET.fromstring(xml_text)
        logger.info('XML 解析成功')
    except ET.ParseError as e:
        # 可能是 ZIP 压缩的拓扑文件
        logger.warning(f'XML 解析失败，尝试作为 ZIP 文件处理: {str(e)}')
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                logger.info(f'ZIP 文件包含文件: {zip_ref.namelist()}')
                for name in zip_ref.namelist():
                    if name.endswith('.xml'):
                        raw_data = zip_ref.read(name)
                        for enc in ['utf-16', 'utf-8', 'gbk']:
                            try:
                                xml_text = raw_data.decode(enc)
                                logger.info(f'ZIP 内文件编码识别成功: {enc}')
                                break
                            except UnicodeDecodeError:
                                continue
                        xml_text = re.sub(r'<\?xml.*?\?>', '', xml_text).strip()
                        root = ET.fromstring(xml_text)
                        logger.info('ZIP 内 XML 解析成功')
                        break
        except zipfile.BadZipFile:
            logger.error('文件不是有效的 ZIP 格式')
            return {"status": "error", "msg": f"XML 解析失败: {str(e)}，且文件不是有效的 ZIP 格式"}
        except Exception as e:
            logger.error(f'ZIP 处理异常: {str(e)}')
            return {"status": "error", "msg": f"ZIP 处理异常: {str(e)}"}
    
    if root is None:
        logger.error('未能提取到 XML 根节点')
        return {"status": "error", "msg": "未能提取到 XML 根节点"}
    
    # 查找所有设备节点（兼容多种标签名）
    nodes = root.findall('.//dev') + root.findall('.//Device') + root.findall('.//node')
    logger.info(f'找到 {len(nodes)} 个设备节点')
    if not nodes:
        devices_node = root.find('.//devices')
        if devices_node is not None:
            nodes = devices_node.findall('dev') + devices_node.findall('Device')
            logger.info(f'从 devices 节点找到 {len(nodes)} 个设备节点')
    
    if not nodes:
        logger.error('文件中未找到任何设备节点')
        return {"status": "error", "msg": "文件中未找到任何设备节点"}
    
    for node in nodes:
        dev_name = node.get('name', 'Unknown')
        dev_type = node.get('model') or node.get('type', 'Unknown')
        # 兼容多种端口属性名
        port_str = node.get('com_port') or node.get('cxPort') or node.get('console') or node.get('port')
        if port_str and port_str != "0":
            try:
                port_int = int(port_str)
                devices.append({
                    'name': dev_name,
                    'type': dev_type,
                    'port': port_int
                })
                logger.info(f'添加设备: {dev_name} (类型: {dev_type}, 端口: {port_int})')
            except ValueError:
                logger.warning(f'端口号格式错误: {port_str}')
                continue
    
    if not devices:
        logger.error('未找到包含有效控制台端口（非0）的网络设备')
        return {"status": "error", "msg": "未找到包含有效控制台端口（非0）的网络设备"}
    
    logger.info(f'拓扑解析完成，共找到 {len(devices)} 个设备')
    return {"status": "success", "data": devices}

# ========== 设备类型分类 ==========
SWITCH_TYPES = {
    'S1700', 'S1720', 'S2700', 'S3700', 'S5700', 'S5720', 'S6700', 'S6720', 'S7700', 'S7900', 'S9700', 'S12700',
    'S5700HI', 'S5710', 'S5720HI', 'S5730', 'S5735', 'S6730',
    'CE5800', 'CE6800', 'CE6810', 'CE6850', 'CE6851', 'CE6855', 'CE6860', 'CE7850', 'CE12800',
    'LSW'
}
ROUTER_TYPES = {
    'AR120', 'AR120W', 'AR1220', 'AR1220V', 'AR1220W', 'AR156', 'AR169',
    'AR2200', 'AR2220', 'AR2240', 'AR2240C', 'AR3260',
    'AR6000', 'AR6100', 'AR6120', 'AR6140',
    'NE20E', 'NE40E', 'NE80E', 'NE5000',
    'Router'
}
FIREWALL_TYPES = {
    'USG2110', 'USG2220', 'USG5120', 'USG5320', 'USG5520', 'USG6000V', 'USG6300', 'USG6500', 'USG6600', 'USG9500V',
    'USG2000', 'USG5000', 'USG6000', 'USG9000',
    'FW'
}
WLAN_TYPES = {
    'AC6005', 'AC6605', 'ACU2', 'AC6508', 'AC6805', 'AC8005',
    'AP2010DN', 'AP3010DN', 'AP4030DN', 'AP5030DN', 'AP6010DN', 'AP7030DE', 'AP8050DN',
    'AP2010', 'AP3010', 'AP4030', 'AP5030', 'AP6010', 'AP7030', 'AP8050'
}

DEVICE_TECH_MAP = {
    'switch': ['vlan', 'stp', 'eth_trunk', 'dhcp', 'virtual_interface', 'acl', 'vrrp'],
    'l3_switch': ['vlan', 'stp', 'eth_trunk', 'dhcp', 'virtual_interface', 'acl', 'vrrp', 'static_route', 'ospf', 'rip'],
    'router': ['interface_ip', 'static_route', 'rip', 'ospf', 'bgp', 'isis', 'dhcp', 'virtual_interface', 'acl', 'nat', 'vrrp', 'eth_trunk'],
    'firewall': ['interface_ip', 'static_route', 'ospf', 'bgp', 'acl', 'nat', 'dhcp', 'virtual_interface', 'vrrp'],
    'wlan_ac': ['vlan', 'stp', 'dhcp', 'virtual_interface', 'acl', 'wlan'],
    'unknown': ['interface_ip', 'vlan', 'dhcp', 'virtual_interface', 'eth_trunk', 'stp', 'static_route', 'rip', 'ospf', 'bgp', 'isis', 'acl', 'nat', 'vrrp', 'wlan']
}

L3_SWITCH_TYPES = {
    'S5700', 'S5720', 'S6700', 'S6720', 'S7700', 'S7900', 'S9700', 'S12700',
    'S5700HI', 'S5710', 'S5720HI', 'S5730', 'S5735', 'S6730',
    'CE5800', 'CE6800', 'CE6810', 'CE6850', 'CE6851', 'CE6855', 'CE6860', 'CE7850', 'CE12800'
}

def classify_device(dev_type):
    dt_upper = dev_type.upper().strip()
    for prefix in SWITCH_TYPES:
        if dt_upper.startswith(prefix) or dt_upper == prefix:
            for l3_prefix in L3_SWITCH_TYPES:
                if dt_upper.startswith(l3_prefix) or dt_upper == l3_prefix:
                    return 'l3_switch'
            return 'switch'
    for prefix in ROUTER_TYPES:
        if dt_upper.startswith(prefix) or dt_upper == prefix:
            return 'router'
    for prefix in FIREWALL_TYPES:
        if dt_upper.startswith(prefix) or dt_upper == prefix:
            return 'firewall'
    for prefix in WLAN_TYPES:
        if dt_upper.startswith(prefix) or dt_upper == prefix:
            if prefix.startswith('AP'):
                return 'wlan_ac'
            return 'wlan_ac'
    dt_prefix = dt_upper.split('-')[0] if '-' in dt_upper else dt_upper.split()[0] if ' ' in dt_upper else dt_upper[:4]
    if any(dt_prefix.startswith(kw) for kw in ['S5', 'S6', 'S7', 'S9', 'S12', 'CE']):
        return 'l3_switch'
    if any(dt_prefix.startswith(kw) for kw in ['S2', 'S3', 'S1']):
        return 'switch'
    if any(dt_prefix.startswith(kw) for kw in ['AR', 'NE']):
        return 'router'
    if 'ROUTER' in dt_upper:
        return 'router'
    if any(dt_prefix.startswith(kw) for kw in ['USG']):
        return 'firewall'
    if any(kw in dt_upper for kw in ['FW', 'FIREWALL']):
        return 'firewall'
    if any(dt_prefix.startswith(kw) for kw in ['AC', 'AP']):
        return 'wlan_ac'
    return 'unknown'

def get_available_techs(dev_type):
    category = classify_device(dev_type)
    return DEVICE_TECH_MAP.get(category, DEVICE_TECH_MAP['unknown'])

# ========== 2. 配置命令生成器（安全参数获取） ==========
def config_interface_ip(params):
    intf = params.get('intf_name', '')
    ip = params.get('ip_address', '')
    mask = params.get('mask', '')
    desc = params.get('intf_desc', '')
    shutdown = params.get('intf_shutdown', 'undo_shutdown')
    dev_cat = params.get('_device_category', 'unknown')
    if not intf or not ip or not mask:
        return "// 错误：接口名、IP地址、掩码不能为空"
    cmd = "system-view\n"
    cmd += f"interface {intf}\n"
    intf_lower = intf.lower()
    if dev_cat in ('switch', 'l3_switch') and not intf_lower.startswith('vlanif') and not intf_lower.startswith('loopback') and not intf_lower.startswith('null'):
        cmd += " undo portswitch\n"
    if desc:
        cmd += f" description {desc}\n"
    cmd += f" ip address {ip} {mask}\n"
    if shutdown == 'shutdown':
        cmd += " shutdown\n"
    else:
        cmd += " undo shutdown\n"
    cmd += "quit\nquit\n"
    return cmd

def config_vlan(params):
    action = params.get('vlan_action', 'create_and_assign')
    vlan_id = params.get('vlan_id', '')
    vlan_name = params.get('vlan_name', '')
    vlan_desc = params.get('vlan_desc', '')
    interface = params.get('interface', '')
    link_type = params.get('link_type', 'access').lower()
    
    if not vlan_id:
        return "// 错误：VLAN ID 不能为空"
    
    cmd = "system-view\n"
    
    if action in ('create', 'create_and_assign'):
        vlan_ids = [v.strip() for v in vlan_id.replace('，', ',').split(',') if v.strip()]
        if len(vlan_ids) > 1:
            cmd += f"vlan batch {' '.join(vlan_ids)}\n"
        else:
            cmd += f"vlan {vlan_id}\n"
            if vlan_name:
                cmd += f" name {vlan_name}\n"
            if vlan_desc:
                cmd += f" description {vlan_desc}\n"
            cmd += "quit\n"
    
    if action in ('assign', 'create_and_assign'):
        if not interface:
            return "// 错误：接口名不能为空"
        else:
            cmd += f"interface {interface}\n"
            cmd += f" port link-type {link_type}\n"
            if link_type == 'access':
                pvid = params.get('pvid', vlan_id.split(',')[0].strip())
                cmd += f" port default vlan {pvid}\n"
            elif link_type == 'trunk':
                pvid = params.get('pvid', '1')
                if pvid != '1':
                    cmd += f" port trunk pvid vlan {pvid}\n"
                allowed = params.get('trunk_allowed_vlans', vlan_id.split(',')[0].strip())
                cmd += f" port trunk allow-pass vlan {allowed}\n"
            elif link_type == 'hybrid':
                pvid = params.get('pvid', vlan_id.split(',')[0].strip())
                cmd += f" port hybrid pvid vlan {pvid}\n"
                untagged = params.get('hybrid_untagged_vlans', vlan_id.split(',')[0].strip())
                tagged = params.get('hybrid_tagged_vlans', '')
                cmd += f" port hybrid untagged vlan {untagged}\n"
                if tagged:
                    cmd += f" port hybrid tagged vlan {tagged}\n"
            cmd += "quit\n"
    
    cmd += "quit\n"
    return cmd

def config_dhcp(params):
    mode = params.get('mode', 'interface')
    dev_cat = params.get('_device_category', 'unknown')
    if mode == 'interface':
        interface = params.get('interface', '')
        dns = params.get('dns', '')
        if not interface or not dns:
            return "// 错误：接口名和DNS不能为空"
        cmd = f"""system-view
dhcp enable
interface {interface}
 dhcp select interface
 dhcp server dns-list {dns}
"""
        if dev_cat in ('switch', 'l3_switch'):
            cmd += " undo shutdown\n"
        cmd += "quit\nquit\n"
        return cmd
    else:
        pool = params.get('pool_name', '')
        gateway = params.get('gateway', '')
        network = params.get('network', '')
        mask = params.get('mask', '')
        dns = params.get('dns', '')
        interface = params.get('interface', '')
        if not all([pool, gateway, network, mask, dns, interface]):
            return "// 错误：全局地址池参数不完整"
        cmd = f"""system-view
dhcp enable
ip pool {pool}
 gateway-list {gateway}
 network {network} mask {mask}
 dns-list {dns}
 excluded-ip-address {gateway}
 quit
interface {interface}
 dhcp select global
"""
        if dev_cat in ('switch', 'l3_switch'):
            cmd += " undo shutdown\n"
        cmd += " quit\nquit\n"
        return cmd

def config_virtual_interface(params):
    vif_type = params.get('vif_type', 'vlanif')
    ip = params.get('ip', '')
    mask = params.get('mask', '')
    if not ip or not mask:
        return "// 错误：IP地址和掩码不能为空"
    if vif_type == 'vlanif':
        vlan_id = params.get('vlan_id', '')
        if not vlan_id:
            return "// 错误：Vlanif需要VLAN ID"
        return f"""system-view
interface Vlanif{vlan_id}
 ip address {ip} {mask}
 undo shutdown
quit
quit
"""
    else:
        loop_id = params.get('loopback_id', '')
        if not loop_id:
            return "// 错误：Loopback需要ID"
        return f"""system-view
interface LoopBack{loop_id}
 ip address {ip} {mask}
quit
quit
"""

def config_eth_trunk(params):
    trunk_id = params.get('trunk_id', '')
    members = params.get('member_interfaces', '')
    mode = params.get('mode', 'manual')
    if not trunk_id or not members:
        return "// 错误：Trunk ID和成员接口不能为空"
    cmd = f"""system-view
interface Eth-Trunk{trunk_id}
 quit
"""
    for member in members.split(','):
        member = member.strip()
        if member:
            cmd += f"""interface {member}
 eth-trunk {trunk_id}
 quit
"""
    if mode == 'lacp':
        cmd += f"interface Eth-Trunk{trunk_id}\n mode lacp\n quit\n"
    cmd += "quit\n"
    return cmd

def config_stp(params):
    mode = params.get('stp_mode', 'stp').lower()
    cmd = "system-view\n"
    if mode == 'stp':
        cmd += "stp mode stp\n"
    elif mode == 'rstp':
        cmd += "stp mode rstp\n"
    else:
        region = params.get('region_name', '')
        instance = params.get('instance_id', '')
        vlan_range = params.get('vlan_range', '')
        if not region or not instance or not vlan_range:
            return "// 错误：MSTP需要区域名、实例ID和VLAN范围"
        cmd += f"""stp mode mstp
stp region-configuration
 region-name {region}
 instance {instance} vlan {vlan_range}
 active region-configuration
quit
"""
    priority = params.get('priority', '')
    if priority:
        cmd += f"stp priority {priority}\n"
    cmd += "quit\n"
    return cmd

def config_static_route(params):
    dest = params.get('dest_network', '')
    mask = params.get('mask', '')
    if not dest or not mask:
        return "// 错误：目的网络和掩码不能为空"
    next_hop = params.get('next_hop', '').strip()
    out_intf = params.get('out_interface', '').strip()
    if next_hop:
        return f"""system-view
ip route-static {dest} {mask} {next_hop}
quit
"""
    elif out_intf:
        return f"""system-view
ip route-static {dest} {mask} {out_intf}
quit
"""
    else:
        return "// 错误：请填写下一跳IP或出接口"

def config_rip(params):
    proc = params.get('process_id', '1')
    network = params.get('network', '')
    if not network:
        return "// 错误：宣告网络不能为空"
    return f"""system-view
rip {proc}
 version 2
 undo summary
 network {network}
 quit
quit
"""

def config_ospf(params):
    proc = params.get('process_id', '1')
    rid = params.get('router_id', '')
    area = params.get('area_id', '0')
    network = params.get('network', '')
    wildcard = params.get('wildcard_mask', '')
    area_type = params.get('area_type', 'normal')
    silent_intf = params.get('silent_intf', '')
    if not rid or not network or not wildcard:
        return "// 错误：Router ID、宣告网段、反掩码不能为空"
    cmd = f"""system-view
ospf {proc} router-id {rid}
 area {area}
"""
    if area_type == 'stub':
        cmd += "  stub\n"
    elif area_type == 'nssa':
        cmd += "  nssa\n"
    cmd += f"  network {network} {wildcard}\n"
    cmd += " quit\n"
    if silent_intf:
        for intf in silent_intf.replace('，', ',').split(','):
            intf = intf.strip()
            if intf:
                cmd += f" silent-interface {intf}\n"
    cmd += "quit\nquit\n"
    return cmd

def config_bgp(params):
    as_num = params.get('as_number', '')
    rid = params.get('router_id', '')
    peer_ip = params.get('peer_ip', '')
    peer_as = params.get('peer_as', '')
    network = params.get('network', '')
    mask = params.get('mask', '')
    if not all([as_num, rid, peer_ip, peer_as, network, mask]):
        return "// 错误：BGP参数不完整"
    return f"""system-view
bgp {as_num}
 router-id {rid}
 peer {peer_ip} as-number {peer_as}
 network {network} mask {mask}
 quit
quit
"""

def config_isis(params):
    proc = params.get('process_id', '1')
    net = params.get('net_entity', '')
    interface = params.get('interface', '')
    if not net or not interface:
        return "// 错误：NET实体和接口不能为空"
    return f"""system-view
isis {proc}
 network-entity {net}
 quit
interface {interface}
 isis enable {proc}
 quit
quit
"""

def config_acl(params):
    acl_type = params.get('acl_type', 'standard')
    acl_num = params.get('acl_num', '')
    rule_id = params.get('rule_id', '')
    src_ip = params.get('src_ip', '')
    src_wild = params.get('src_wildcard', '')
    action = params.get('acl_action', 'permit')
    if not acl_num or not rule_id or not src_ip or not src_wild:
        return "// 错误：ACL编号、规则ID、源IP、反掩码不能为空"
    if acl_type == 'standard':
        return f"""system-view
acl {acl_num}
 rule {rule_id} {action} source {src_ip} {src_wild}
 quit
quit
"""
    else:
        protocol = params.get('protocol', 'ip')
        dst_ip = params.get('dst_ip', '')
        dst_wild = params.get('dst_wildcard', '')
        dst_port = params.get('dst_port', '')
        if not dst_ip or not dst_wild:
            return "// 错误：扩展ACL需要目的IP和反掩码"
        cmd = f"""system-view
acl {acl_num}
"""
        if dst_port:
            cmd += f" rule {rule_id} {action} {protocol} source {src_ip} {src_wild} destination {dst_ip} {dst_wild} {dst_port}\n"
        else:
            cmd += f" rule {rule_id} {action} {protocol} source {src_ip} {src_wild} destination {dst_ip} {dst_wild}\n"
        cmd += " quit\nquit\n"
        return cmd

def config_nat(params):
    acl_num = params.get('acl_num', '')
    src_net = params.get('src_network', '')
    src_wild = params.get('src_wildcard', '')
    out_intf = params.get('out_interface', '')
    if not all([acl_num, src_net, src_wild, out_intf]):
        return "// 错误：ACL编号、源网络、反掩码、出接口不能为空"
    return f"""system-view
acl {acl_num}
 rule permit source {src_net} {src_wild}
 quit
interface {out_intf}
 nat outbound {acl_num}
 quit
quit
"""

def config_vrrp(params):
    interface = params.get('interface', '')
    vrid = params.get('vrid', '')
    vip = params.get('virtual_ip', '')
    priority = params.get('priority', '100')
    preempt = params.get('preempt_mode', 'enable')
    delay = params.get('preempt_delay', '0')
    auth_mode = params.get('auth_mode', '')
    auth_key = params.get('auth_key', '')
    if not interface or not vrid or not vip:
        return "// 错误：接口、VRID、虚拟IP不能为空"
    cmd = f"""system-view
interface {interface}
 vrrp vrid {vrid} virtual-ip {vip}
"""
    if priority and priority != '100':
        cmd += f" vrrp vrid {vrid} priority {priority}\n"
    if preempt == 'disable':
        cmd += f" vrrp vrid {vrid} preempt-mode disable\n"
    elif delay and delay != '0':
        cmd += f" vrrp vrid {vrid} preempt-mode timer delay {delay}\n"
    if auth_mode and auth_key:
        cmd += f" vrrp vrid {vrid} authentication-mode {auth_mode} {auth_key}\n"
    cmd += " quit\nquit\n"
    return cmd

def config_wlan(params):
    cmd = "system-view\n"
    src_intf = params.get('ac_source_interface', '')
    if src_intf:
        cmd += f"capwap source interface {src_intf}\n"
    cmd += "wlan\n"
    domain = params.get('domain_profile_name', '')
    if domain:
        cmd += f" regulatory-domain-profile name {domain}\n quit\n"
    ssid_profile = params.get('ssid_profile_name', '')
    ssid_name = params.get('ssid_name', '')
    if ssid_profile and ssid_name:
        cmd += f" ssid-profile name {ssid_profile}\n  ssid {ssid_name}\n quit\n"
    sec_profile = params.get('security_profile_name', '')
    sec_mode = params.get('security_mode', 'open')
    if sec_profile:
        cmd += f" security-profile name {sec_profile}\n"
        if sec_mode == 'psk':
            psk = params.get('psk_password', '')
            if psk:
                cmd += f"  security wpa2 psk pass-phrase {psk} aes\n"
            else:
                cmd += f"  security wpa2 psk aes\n"
        else:
            cmd += f"  security open\n"
        cmd += " quit\n"
    vap_profile = params.get('vap_profile_name', '')
    svlan = params.get('service_vlan', '')
    if vap_profile and svlan:
        cmd += f" vap-profile name {vap_profile}\n"
        cmd += f"  forward-mode tunnel\n"
        cmd += f"  service-vlan vlan-id {svlan}\n"
        if ssid_profile:
            cmd += f"  ssid-profile {ssid_profile}\n"
        if sec_profile:
            cmd += f"  security-profile {sec_profile}\n"
        cmd += " quit\n"
    ap_group = params.get('ap_group_name', '')
    if ap_group and vap_profile:
        cmd += f" ap-group name {ap_group}\n"
        cmd += f"  vap-profile {vap_profile} wlan 1 radio 0\n"
        cmd += f"  vap-profile {vap_profile} wlan 1 radio 1\n"
        cmd += " quit\n"
    
    # 添加 AP 功能
    ap_mac = params.get('ap_mac', '')
    ap_name = params.get('ap_name', '')
    if ap_mac and ap_name:
        cmd += f" ap-id 0 ap-mac {ap_mac}\n"
        cmd += f"  ap-name {ap_name}\n"
        if ap_group:
            cmd += f"  ap-group {ap_group}\n"
        cmd += " quit\n"
    
    cmd += "quit\nreturn\n"
    return cmd

CONFIG_GENERATORS = {
    "interface_ip": config_interface_ip,
    "vlan": config_vlan,
    "dhcp": config_dhcp,
    "virtual_interface": config_virtual_interface,
    "eth_trunk": config_eth_trunk,
    "stp": config_stp,
    "static_route": config_static_route,
    "rip": config_rip,
    "ospf": config_ospf,
    "bgp": config_bgp,
    "isis": config_isis,
    "acl": config_acl,
    "nat": config_nat,
    "vrrp": config_vrrp,
    "wlan": config_wlan,
}

def validate_params(tech, params):
    """验证配置参数"""
    logger.info(f'开始验证配置参数: 技术={tech}, 参数={params}')
    
    if not isinstance(params, dict):
        logger.error('参数类型错误，应为字典')
        return {"valid": False, "error": "参数类型错误，应为字典"}
    
    if tech not in CONFIG_GENERATORS:
        logger.warning(f'未知的技术类型: {tech}')
        return {"valid": False, "error": "未知的配置类型"}
    
    if tech == 'interface_ip':
        required = ['intf_name', 'ip_address', 'mask']
        # 验证IP地址格式
        if 'ip_address' in params:
            ip = params['ip_address']
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                return {"valid": False, "error": "IP地址格式错误"}
            # 验证每个IP部分在0-255范围内
            parts = ip.split('.')
            for part in parts:
                try:
                    num = int(part)
                    if num < 0 or num > 255:
                        return {"valid": False, "error": "IP地址格式错误"}
                except ValueError:
                    return {"valid": False, "error": "IP地址格式错误"}
        # 验证掩码格式
        if 'mask' in params:
            mask = params['mask']
            if not (re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', mask) or re.match(r'^\d{1,2}$', mask)):
                return {"valid": False, "error": "掩码格式错误"}
            # 验证掩码值范围
            if re.match(r'^\d{1,2}$', mask):
                mask_num = int(mask)
                if mask_num < 0 or mask_num > 32:
                    return {"valid": False, "error": "掩码范围应在0-32之间"}
    elif tech == 'vlan':
        action = params.get('vlan_action', 'create_and_assign')
        if action in ('assign', 'create_and_assign'):
            required = ['vlan_id', 'interface']
        else:
            required = ['vlan_id']
        # 验证VLAN ID范围
        if 'vlan_id' in params:
            vlan_ids = [v.strip() for v in params['vlan_id'].replace('，', ',').split(',') if v.strip()]
            for vid in vlan_ids:
                try:
                    vid_num = int(vid)
                    if vid_num < 1 or vid_num > 4094:
                        return {"valid": False, "error": "VLAN ID范围应在1-4094之间"}
                except ValueError:
                    return {"valid": False, "error": "VLAN ID格式错误"}
    elif tech == 'dhcp':
        mode = params.get('mode', 'interface')
        if mode == 'interface':
            required = ['interface', 'dns']
        else:
            required = ['pool_name', 'gateway', 'network', 'mask', 'dns', 'interface']
        # 验证DNS格式
        if 'dns' in params:
            dns_servers = [d.strip() for d in params['dns'].split(' ') if d.strip()]
            for dns in dns_servers:
                if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', dns):
                    return {"valid": False, "error": "DNS服务器地址格式错误"}
    elif tech == 'virtual_interface':
        vif_type = params.get('vif_type', 'vlanif')
        if vif_type == 'vlanif':
            required = ['vlan_id', 'ip', 'mask']
        else:
            required = ['loopback_id', 'ip', 'mask']
    elif tech == 'eth_trunk':
        required = ['trunk_id', 'member_interfaces']
    elif tech == 'stp':
        mode = params.get('stp_mode', 'stp').lower()
        if mode == 'mstp':
            required = ['stp_mode', 'region_name', 'instance_id', 'vlan_range']
        else:
            required = ['stp_mode']
    elif tech == 'static_route':
        required = ['dest_network', 'mask']
        if not params.get('next_hop') and not params.get('out_interface'):
            logger.error('静态路由需要下一跳IP或出接口')
            return {"valid": False, "error": "静态路由需要下一跳IP或出接口"}
    elif tech == 'rip':
        required = ['network']
    elif tech == 'ospf':
        required = ['router_id', 'network', 'wildcard_mask']
        # 验证Router ID格式
        if 'router_id' in params:
            rid = params['router_id']
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', rid):
                return {"valid": False, "error": "Router ID格式错误"}
    elif tech == 'bgp':
        required = ['as_number', 'router_id', 'peer_ip', 'peer_as', 'network', 'mask']
        # 验证AS号范围
        if 'as_number' in params:
            try:
                as_num = int(params['as_number'])
                if as_num < 1 or as_num > 65535:
                    return {"valid": False, "error": "AS号范围应在1-65535之间"}
            except ValueError:
                return {"valid": False, "error": "AS号格式错误"}
    elif tech == 'isis':
        required = ['net_entity', 'interface']
    elif tech == 'acl':
        acl_type = params.get('acl_type', 'standard')
        if acl_type == 'standard':
            required = ['acl_num', 'rule_id', 'src_ip', 'src_wildcard']
        else:
            required = ['acl_num', 'rule_id', 'src_ip', 'src_wildcard', 'dst_ip', 'dst_wildcard']
        # 验证ACL编号范围
        if 'acl_num' in params:
            try:
                acl_num = int(params['acl_num'])
                if not ((1000 <= acl_num <= 1999) or (2000 <= acl_num <= 2999) or (3000 <= acl_num <= 3999) or (4000 <= acl_num <= 4999)):
                    return {"valid": False, "error": "ACL编号范围错误"}
            except ValueError:
                return {"valid": False, "error": "ACL编号格式错误"}
    elif tech == 'nat':
        required = ['acl_num', 'src_network', 'src_wildcard', 'out_interface']
    elif tech == 'vrrp':
        required = ['interface', 'vrid', 'virtual_ip']
        # 验证VRID范围
        if 'vrid' in params:
            try:
                vrid = int(params['vrid'])
                if vrid < 1 or vrid > 255:
                    return {"valid": False, "error": "VRID范围应在1-255之间"}
            except ValueError:
                return {"valid": False, "error": "VRID格式错误"}
    elif tech == 'wlan':
        required = []
    else:
        required = []
    
    missing = [param for param in required if not params.get(param)]
    if missing:
        logger.error(f'缺少必要参数: {missing}')
        return {"valid": False, "error": f"缺少必要参数: {', '.join(missing)}"}
    
    logger.info('参数验证通过')
    return {"valid": True, "error": None}

def generate_config(tech, params, device_category='unknown', preview=False):
    logger.info(f'开始生成配置: 技术={tech}, 参数={params}, 设备类别={device_category}, 预览={preview}')
    
    # 验证参数
    validation = validate_params(tech, params)
    if not validation["valid"]:
        return f"// 错误：{validation['error']}"
    
    params['_device_category'] = device_category
    result = CONFIG_GENERATORS[tech](params)
    logger.info(f'配置生成成功，命令行数: {len(result.splitlines())}')
    
    if preview:
        # 添加预览标记
        return f"// 预览模式\n{result}"
    
    return result

# ========== 3. Socket 通信辅助函数 ==========
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

def _is_prompt_at_user_view(client):
    client.sendall(b"\n")
    time.sleep(0.2)
    output = _handle_more_prompt(client, timeout=2)
    lines = output.strip().split('\n') if output.strip() else []
    if lines:
        last_line = lines[-1].strip()
        return last_line.startswith('<') and not '#' in last_line
    return False

def _wait_for_prompt(client, timeout=8):
    output = b""
    client.settimeout(timeout)
    start = time.time()
    while time.time() - start < timeout:
        try:
            chunk = client.recv(4096)
            if not chunk:
                break
            output += chunk
            text = output.decode('ascii', errors='ignore')
            lines = text.split('\n')
            if lines and _is_prompt_line(lines[-1]):
                break
        except socket.timeout:
            break
    return output.decode('ascii', errors='ignore')

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
                break
        except socket.timeout:
            break
    return output.decode('ascii', errors='ignore')

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

def send_command(client, cmd, wait_prompt=True, timeout=5):
    if cmd:
        client.sendall(cmd.encode('ascii') + b"\n")
    if not wait_prompt:
        time.sleep(0.2)
        return ""
    return _wait_for_prompt(client, timeout)

def push_to_device(port, commands):
    host = "127.0.0.1"
    logger.info(f'开始推送配置到设备: 主机={host}, 端口={port}')
    
    max_retries = 3
    retry_interval = 1
    
    for attempt in range(max_retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect((host, port))
            logger.info(f'设备连接成功 (尝试 {attempt + 1}/{max_retries})')

            _flush_buffer(client)
            _ensure_user_view(client)

            cmd_lines = []
            for line in commands.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('//') or line.startswith('#'):
                    continue
                cmd_lines.append(line)

            if not cmd_lines:
                client.close()
                return {"status": "error", "log": "没有可执行的命令"}

            first_cmd = cmd_lines[0].lower().strip()
            config_keywords = ['vlan', 'interface', 'ospf', 'bgp', 'rip', 'isis', 'acl', 'nat', 'stp', 'dhcp', 'qos', 'policy', 'traffic', 'firewall', 'undo', 'ip route', 'rip', 'aaa', 'user-interface', 'sysname', 'stp', 'vrrp', 'cluster', 'ntdp', 'ndp', 'diffserv', 'drop-profile']

            if first_cmd != 'system-view' and any(first_cmd.startswith(kw) for kw in config_keywords):
                cmd_lines.insert(0, 'system-view')
            elif first_cmd == 'sysname' or first_cmd == 'clock' or first_cmd == 'language-mode':
                cmd_lines.insert(0, 'system-view')

            last_cmd = cmd_lines[-1].lower().strip()
            if last_cmd != 'return' and last_cmd != 'quit' and last_cmd != 'system-view':
                if last_cmd.startswith('interface ') or last_cmd.startswith('vlan '):
                    cmd_lines.append('return')

            BATCH_SIZE = 5
            log_output = ""
            output_bytes = b""
            total_sent = 0
            error_occurred = False

            for batch_start in range(0, len(cmd_lines), BATCH_SIZE):
                batch = cmd_lines[batch_start:batch_start + BATCH_SIZE]
                for cmd in batch:
                    logger.info(f'发送命令: {cmd}')
                    log_output += f"> {cmd}\n"
                    try:
                        cmd_bytes = (cmd + '\r\n').encode('ascii')
                        client.sendall(cmd_bytes)
                        time.sleep(0.5)
                        client.settimeout(5)
                        start = time.time()
                        resp = b""
                        while time.time() - start < 5:
                            try:
                                chunk = client.recv(4096)
                                if not chunk:
                                    break
                                resp += chunk
                                text = resp.decode('ascii', errors='ignore')
                                if '---- More ----' in text:
                                    client.sendall(b' ')
                                    time.sleep(0.1)
                                    continue
                                if text.strip().endswith('>') or '[Huawei' in text:
                                    break
                            except socket.timeout:
                                break
                        resp_text = resp.decode('ascii', errors='ignore')
                        log_output += resp_text
                        output_bytes += resp
                        
                        # 检查命令执行错误
                        if 'Error' in resp_text or 'error' in resp_text:
                            error_occurred = True
                            logger.warning(f'命令执行错误: {cmd}')
                            logger.warning(f'错误信息: {resp_text}')
                    except Exception as cmd_error:
                        error_occurred = True
                        error_msg = f'命令执行异常: {str(cmd_error)}'
                        log_output += f"// {error_msg}\n"
                        logger.error(error_msg)
                total_sent += len(batch)

                is_last_batch = (batch_start + BATCH_SIZE >= len(cmd_lines))
                if not is_last_batch:
                    time.sleep(0.2)

            client.close()
            
            # 分析执行结果
            if error_occurred:
                logger.warning('配置推送过程中出现错误')
                return {"status": "error", "log": log_output}
            else:
                logger.info(f'配置推送完成，共发送 {len(cmd_lines)} 条命令')
                return {"status": "success", "log": log_output}
            
        except ConnectionRefusedError:
            logger.error(f'连接被拒绝: 端口={port} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                logger.info(f'等待 {retry_interval} 秒后重试...')
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "log": f"连接被拒绝！请确认 eNSP 中设备已启动(绿色)。\n端口: {port}"}
        except socket.timeout:
            logger.error(f'连接超时: 端口={port} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                logger.info(f'等待 {retry_interval} 秒后重试...')
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "log": f"连接超时！请确认 eNSP 中设备已启动且可访问。\n端口: {port}"}
        except Exception as e:
            logger.error(f'连接设备发生错误: {str(e)} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                logger.info(f'等待 {retry_interval} 秒后重试...')
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "log": f"连接设备发生错误...\n错误信息: {str(e)}"}

# ========== 4. 读取设备接口列表（物理+虚拟） ==========
def get_device_interfaces(port):
    host = "127.0.0.1"
    logger.info(f'开始获取设备接口列表: 主机={host}, 端口={port}')
    
    max_retries = 3
    retry_interval = 1
    
    for attempt in range(max_retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect((host, port))
            logger.info(f'设备连接成功 (尝试 {attempt + 1}/{max_retries})')
            
            _flush_buffer(client)
            _ensure_user_view(client)
            
            _send_and_wait(client, "system-view", timeout=5)
            _send_and_wait(client, "screen-length 0 temporary", timeout=5)
            _send_and_wait(client, "quit", timeout=5)
            
            output = _send_and_wait(client, "display interface brief", timeout=10)
            client.close()
            logger.info('接口信息获取成功')

            physical = []
            virtual = []
            all_interfaces = []

            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('Interface') or line.startswith('----'):
                    continue
                if line.startswith('<') or line.startswith('['):
                    continue
                if any(kw in line for kw in ['Physical', '*down:', '(l):', '(s):', '(b):', '^down:', '(e):', '(d):', 'InUti', 'PHY:', 'Error']):
                    continue
                parts = line.split()
                if not parts or len(parts) < 2:
                    continue
                iface = parts[0]
                if iface.startswith('display') or iface.startswith('Error'):
                    continue
                if iface.startswith('Vlanif') or iface.startswith('LoopBack') or iface.startswith('NULL'):
                    virtual.append(iface)
                elif (iface.startswith('GigabitEthernet') or iface.startswith('Ethernet') or
                      iface.startswith('Eth-Trunk') or iface.startswith('GE') or
                      iface.startswith('Serial') or iface.startswith('Cellular') or
                      iface.startswith('10GE') or iface.startswith('40GE') or iface.startswith('100GE') or
                      iface.startswith('XGigabitEthernet') or iface.startswith('FortyGigE')):
                    physical.append(iface)
                elif '/' in iface and not iface.startswith('InUti'):
                    physical.append(iface)
                else:
                    continue
                all_interfaces.append(iface)

            if not all_interfaces:
                logger.warning(f'接口列表为空，可能解析失败 (尝试 {attempt + 1}/{max_retries})')
                logger.debug(f'原始输出前500字符: {output[:500]}')
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
                    continue

            logger.info(f'接口列表解析完成: 物理接口={len(physical)}, 虚拟接口={len(virtual)}, 总接口={len(all_interfaces)}')
            return {
                "status": "success",
                "interfaces": all_interfaces,
                "physical": physical,
                "virtual": virtual
            }
            
        except Exception as e:
            logger.error(f'获取接口列表异常: {str(e)} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                logger.info(f'等待 {retry_interval} 秒后重试...')
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "msg": str(e)}

def save_device_config(port):
    host = "127.0.0.1"
    logger.info(f'开始保存设备配置: 主机={host}, 端口={port}')

    max_retries = 3
    retry_interval = 1

    for attempt in range(max_retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect((host, port))
            logger.info(f'设备连接成功 (尝试 {attempt + 1}/{max_retries})')

            _flush_buffer(client)
            _ensure_user_view(client)

            client.sendall(b"save\n")
            time.sleep(0.3)

            output = b""
            client.settimeout(5)
            start = time.time()
            confirmed = False
            file_confirmed = False
            while time.time() - start < 30:
                try:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    output += chunk
                    text = output.decode('ascii', errors='ignore')

                    if 'Are you sure' in text or 'confirm' in text.lower() or '(y/n)' in text.lower():
                        client.sendall(b"y\n")
                        time.sleep(0.1)
                        confirmed = True
                        output = b""
                        start = time.time()
                        continue

                    if confirmed and ('Please input the file name' in text or 'vrpcfg.zip' in text):
                        client.sendall(b"\n")
                        time.sleep(0.1)
                        file_confirmed = True
                        output = b""
                        start = time.time()
                        continue

                    if file_confirmed and ('successfully' in text.lower() or 'saved' in text.lower()):
                        break
                    if file_confirmed and ('Error' in text or 'error' in text):
                        break
                    if file_confirmed and _is_prompt_line(text.strip().split('\n')[-1]) if text.strip() else False:
                        break
                except socket.timeout:
                    if file_confirmed:
                        break
                    if confirmed and not file_confirmed:
                        client.sendall(b"\n")
                        time.sleep(0.1)
                        file_confirmed = True
                        output = b""
                        start = time.time()

            final_output = output.decode('ascii', errors='ignore')
            client.close()

            if 'successfully' in final_output.lower() or 'saved' in final_output.lower() or (confirmed and file_confirmed):
                logger.info('设备配置保存成功')
                return {"status": "success", "msg": "配置已成功保存到设备", "log": final_output}
            else:
                logger.info(f'设备配置保存完成: {final_output[:200]}')
                return {"status": "success", "msg": "保存命令已发送", "log": final_output}

        except ConnectionRefusedError:
            logger.error(f'连接被拒绝: 端口={port} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "msg": "连接被拒绝！请确认 eNSP 中设备已启动(绿色)。"}
        except Exception as e:
            logger.error(f'保存配置异常: {str(e)} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "msg": f"保存配置异常: {str(e)}"}


PARAM_PATTERNS = {
    'interface_ip': {
        'commands': ['display ip interface brief'],
        'parse': lambda lines: _parse_interface_ip(lines),
    },
    'vlan': {
        'commands': ['display vlan'],
        'parse': lambda lines: _parse_vlan(lines),
    },
    'ospf': {
        'commands': ['display ospf routing'],
        'parse': lambda lines: _parse_ospf(lines),
    },
    'static_route': {
        'commands': ['display ip routing-table'],
        'parse': lambda lines: _parse_static_route(lines),
    },
    'acl': {
        'commands': ['display acl configuration'],
        'parse': lambda lines: _parse_acl(lines),
    },
    'vrrp': {
        'commands': ['display vrrp'],
        'parse': lambda lines: _parse_vrrp(lines),
    },
    'bgp': {
        'commands': ['display bgp routing'],
        'parse': lambda lines: _parse_bgp(lines),
    },
    'rip': {
        'commands': ['display rip'],
        'parse': lambda lines: _parse_rip(lines),
    },
    'isis': {
        'commands': ['display isis route'],
        'parse': lambda lines: _parse_isis(lines),
    },
    'nat': {
        'commands': ['display nat'],
        'parse': lambda lines: _parse_nat(lines),
    },
    'stp': {
        'commands': ['display stp'],
        'parse': lambda lines: _parse_stp(lines),
    },
    'eth_trunk': {
        'commands': ['display eth-trunk'],
        'parse': lambda lines: _parse_eth_trunk(lines),
    },
    'dhcp': {
        'commands': ['display ip pool'],
        'parse': lambda lines: _parse_dhcp(lines),
    },
    'virtual_interface': {
        'commands': ['display vlanif'],
        'parse': lambda lines: _parse_virtual_interface(lines),
    },
    'wlan': {
        'commands': ['display wlan'],
        'parse': lambda lines: _parse_wlan(lines),
    },
}


def _parse_interface_ip(lines):
    params = {}
    intf_pattern = re.compile(r'(GigabitEthernet|Ethernet|Serial|Loopback|Vlanif|Tunnel|MEth)(\S+)')
    ip_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)')
    for line in lines:
        m = intf_pattern.search(line)
        if m:
            if 'intf_name' not in params:
                params['intf_name'] = m.group(1) + m.group(2)
                break
    for line in lines:
        m = ip_pattern.search(line)
        if m and 'ip_address' not in params:
            params['ip_address'] = m.group(1)
            params['mask'] = m.group(2)
            break
    return params


def _parse_vlan(lines):
    params = {}
    vlan_id_pattern = re.compile(r'VLAN ID:\s*(\d+)')
    vlan_name_pattern = re.compile(r'VLAN Name:\s*(\S+)')
    link_type_pattern = re.compile(r'Link-type:\s*(\S+)')
    interface_pattern = re.compile(r'Interface:\s*(.+)')
    for line in lines:
        m = vlan_id_pattern.search(line)
        if m and 'vlan_id' not in params:
            params['vlan_id'] = m.group(1)
        m = vlan_name_pattern.search(line)
        if m and 'vlan_name' not in params:
            params['vlan_name'] = m.group(1)
        m = link_type_pattern.search(line)
        if m and 'link_type' not in params:
            params['link_type'] = m.group(1)
        m = interface_pattern.search(line)
        if m and 'interface' not in params:
            params['interface'] = m.group(1).strip().split(',')[0].strip()
    return params


def _parse_ospf(lines):
    params = {}
    proc_pattern = re.compile(r'OSPF Process (\d+)')
    rid_pattern = re.compile(r'Router ID:\s*(\d+\.\d+\.\d+\.\d+)')
    area_pattern = re.compile(r'Area\s+(\d+\.\d+\.\d+\.\d+|\d+)')
    net_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)/(\d+)')
    for line in lines:
        m = proc_pattern.search(line)
        if m and 'process_id' not in params:
            params['process_id'] = m.group(1)
        m = rid_pattern.search(line)
        if m and 'router_id' not in params:
            params['router_id'] = m.group(1)
        m = area_pattern.search(line)
        if m and 'area_id' not in params:
            params['area_id'] = m.group(1)
        m = net_pattern.search(line)
        if m and 'network' not in params:
            params['network'] = m.group(1)
            params['mask'] = m.group(2)
    return params


def _parse_static_route(lines):
    params = {}
    pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)')
    for line in lines:
        m = pattern.search(line)
        if m and 'dest_network' not in params:
            params['dest_network'] = m.group(1)
            params['mask'] = m.group(2)
            params['next_hop'] = m.group(3)
    return params


def _parse_acl(lines):
    params = {}
    acl_pattern = re.compile(r'ACL\s+(\d+)')
    rule_pattern = re.compile(r'rule\s+(\d+)\s+(\w+)\s+.*?source\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)')
    for line in lines:
        m = acl_pattern.search(line)
        if m and 'acl_num' not in params:
            params['acl_num'] = m.group(1)
            num = int(m.group(1))
            params['acl_type'] = 'standard' if num < 3000 else 'extended'
        m = rule_pattern.search(line)
        if m and 'rule_id' not in params:
            params['rule_id'] = m.group(1)
            params['acl_action'] = m.group(2)
            params['src_ip'] = m.group(3)
            params['src_mask'] = m.group(4)
    return params


def _parse_vrrp(lines):
    params = {}
    vrid_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\d+)\s+(Master|Backup)')
    pri_pattern = re.compile(r'Priority:\s*(\d+)')
    for line in lines:
        m = vrid_pattern.search(line)
        if m and 'virtual_ip' not in params:
            params['virtual_ip'] = m.group(1)
            params['vrid'] = m.group(2)
            params['interface'] = m.group(3)
        m = pri_pattern.search(line)
        if m and 'priority' not in params:
            params['priority'] = m.group(1)
    return params


def _parse_bgp(lines):
    params = {}
    as_pattern = re.compile(r'Local AS Number:\s*(\d+)')
    rid_pattern = re.compile(r'Router ID:\s*(\d+\.\d+\.\d+\.\d+)')
    peer_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+)')
    for line in lines:
        m = as_pattern.search(line)
        if m and 'as_number' not in params:
            params['as_number'] = m.group(1)
        m = rid_pattern.search(line)
        if m and 'router_id' not in params:
            params['router_id'] = m.group(1)
        m = peer_pattern.search(line)
        if m and 'peer_ip' not in params:
            params['peer_ip'] = m.group(1)
            params['peer_as'] = m.group(2)
    return params


def _parse_rip(lines):
    params = {}
    net_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)')
    for line in lines:
        m = net_pattern.search(line)
        if m and 'network' not in params:
            params['network'] = m.group(1)
    return params


def _parse_isis(lines):
    params = {}
    sysid_pattern = re.compile(r'System ID:\s*(\S+)')
    net_pattern = re.compile(r'NET:\s*(\S+)')
    for line in lines:
        m = sysid_pattern.search(line)
        if m and 'sys_id' not in params:
            params['sys_id'] = m.group(1)
        m = net_pattern.search(line)
        if m and 'net_entity' not in params:
            params['net_entity'] = m.group(1)
    return params


def _parse_nat(lines):
    params = {}
    intf_pattern = re.compile(r'Interface:\s*(\S+)')
    acl_pattern = re.compile(r'ACL\s+(\d+)')
    for line in lines:
        m = intf_pattern.search(line)
        if m and 'interface' not in params:
            params['interface'] = m.group(1)
        m = acl_pattern.search(line)
        if m and 'acl_num' not in params:
            params['acl_num'] = m.group(1)
    return params


def _parse_stp(lines):
    params = {}
    mode_pattern = re.compile(r'Mode:\s*(\S+)')
    region_pattern = re.compile(r'Region:\s*(\S+)')
    inst_pattern = re.compile(r'Instance\s+(\d+).*?VLAN\s+(\S+)')
    for line in lines:
        m = mode_pattern.search(line)
        if m and 'stp_mode' not in params:
            params['stp_mode'] = m.group(1)
        m = region_pattern.search(line)
        if m and 'region_name' not in params:
            params['region_name'] = m.group(1)
        m = inst_pattern.search(line)
        if m and 'instance_id' not in params:
            params['instance_id'] = m.group(1)
            params['vlan_range'] = m.group(2)
    return params


def _parse_eth_trunk(lines):
    params = {}
    trunk_pattern = re.compile(r'Eth-Trunk(\d+)')
    mode_pattern = re.compile(r'Mode:\s*(\S+)')
    member_pattern = re.compile(r'(\S+)\s+\(m\)')
    members = []
    for line in lines:
        m = trunk_pattern.search(line)
        if m and 'trunk_id' not in params:
            params['trunk_id'] = m.group(1)
        m = mode_pattern.search(line)
        if m and 'mode' not in params:
            params['mode'] = m.group(1)
        m = member_pattern.search(line)
        if m:
            members.append(m.group(1))
    if members:
        params['member_interfaces'] = ','.join(members)
    return params


def _parse_dhcp(lines):
    params = {}
    pool_pattern = re.compile(r'Pool Name:\s*(\S+)')
    ip_pattern = re.compile(r'IP addresses\s+(\d+\.\d+\.\d+\.\d+)')
    dns_pattern = re.compile(r'DNS\s+(\d+\.\d+\.\d+\.\d+)')
    for line in lines:
        m = pool_pattern.search(line)
        if m and 'pool_name' not in params:
            params['pool_name'] = m.group(1)
        m = ip_pattern.search(line)
        if m and 'start_ip' not in params:
            params['start_ip'] = m.group(1)
        m = dns_pattern.search(line)
        if m and 'dns' not in params:
            params['dns'] = m.group(1)
    return params


def _parse_virtual_interface(lines):
    params = {}
    vif_pattern = re.compile(r'(Vlanif|LoopBack|Tunnel)(\d+)')
    ip_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)')
    for line in lines:
        m = vif_pattern.search(line)
        if m and 'vif_type' not in params:
            params['vif_type'] = m.group(1).lower()
            if params['vif_type'] == 'vlanif':
                params['vlan_id'] = m.group(2)
            elif params['vif_type'] == 'loopback':
                params['loopback_id'] = m.group(2)
            elif params['vif_type'] == 'tunnel':
                params['tunnel_id'] = m.group(2)
        m = ip_pattern.search(line)
        if m and 'ip' not in params:
            params['ip'] = m.group(1)
            params['mask'] = m.group(2)
    return params


def _parse_wlan(lines):
    params = {}
    ssid_pattern = re.compile(r'SSID\s+(\S+)')
    vap_pattern = re.compile(r'VAP\s+(\S+)')
    sec_pattern = re.compile(r'security-profile\s+name\s+(\S+)')
    in_wlan_block = False
    for line in lines:
        if line.lstrip().startswith('wlan'):
            in_wlan_block = True
            continue
        if in_wlan_block:
            m = vap_pattern.search(line)
            if m and 'vap_profile_name' not in params:
                params['vap_profile_name'] = m.group(1)
            m = sec_pattern.search(line)
            if m and 'security_profile_name' not in params:
                params['security_profile_name'] = m.group(1)
            m = ssid_pattern.search(line)
            if m and 'ssid_name' not in params:
                params['ssid_name'] = m.group(1)
            if not line.startswith(' ') and not line.startswith('\t') and not line.lstrip().startswith('wlan'):
                in_wlan_block = False
    return params


def read_current_params(port, tech):
    host = "127.0.0.1"
    logger.info(f'开始读取设备当前配置参数: 端口={port}, 技术={tech}')

    if tech not in PARAM_PATTERNS:
        return {"status": "error", "msg": f"暂不支持读取 {tech} 类型的配置参数"}

    pattern_info = PARAM_PATTERNS[tech]
    commands = pattern_info['commands']

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect((host, port))
        logger.info(f'设备连接成功')

        _flush_buffer(client)

        client.sendall(b"screen-length 0 temporary\n")
        _handle_more_prompt(client, timeout=3)

        all_output = ""
        for cmd in commands:
            client.sendall((cmd + "\n").encode('ascii'))
            output = _handle_more_prompt(client, timeout=8)
            if 'Error' in output:
                logger.warning(f'命令执行失败: {cmd}')
                continue
            all_output += output + "\n"

        client.close()

        lines = all_output.strip().splitlines()
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('display ') or stripped.startswith('----'):
                continue
            if stripped.startswith('<') or stripped.startswith('['):
                continue
            if 'More' in stripped or '#' in stripped:
                continue
            clean_lines.append(line.rstrip())

        params = pattern_info['parse'](clean_lines)
        logger.info(f'配置参数解析完成: {params}')

        if not params:
            return {"status": "success", "params": {}, "msg": "未找到相关配置参数，可能设备上尚未配置此项"}

        return {"status": "success", "params": params}

    except ConnectionRefusedError:
        logger.error(f'连接被拒绝: 端口={port}')
        return {"status": "error", "msg": "连接被拒绝！请确认 eNSP 中设备已启动(绿色)。"}
    except Exception as e:
        logger.error(f'读取配置参数异常: {str(e)}')
        return {"status": "error", "msg": f"读取配置参数异常: {str(e)}"}

def get_device_config(port):
    host = "127.0.0.1"
    logger.info(f'开始获取设备当前配置: 主机={host}, 端口={port}')
    
    max_retries = 3
    retry_interval = 1
    
    for attempt in range(max_retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect((host, port))
            logger.info(f'设备连接成功 (尝试 {attempt + 1}/{max_retries})')
            
            _flush_buffer(client)
            _ensure_user_view(client)
            
            _send_and_wait(client, "system-view", timeout=5)
            _send_and_wait(client, "screen-length 0 temporary", timeout=5)
            _send_and_wait(client, "quit", timeout=5)
            
            output = _send_and_wait(client, "display current-configuration", timeout=15)
            client.close()
            logger.info('设备配置获取成功')
            
            config_lines = []
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('display current-configuration') or line.startswith('---- More ----'):
                    continue
                if (line.startswith('<') or line.startswith('[')) and ('#' in line or '>' in line):
                    continue
                if 'Error' in line and len(line) < 30:
                    continue
                if line.startswith('More'):
                    continue
                config_lines.append(line)
            
            config_text = '\n'.join(config_lines)
            logger.info(f'配置解析完成，共 {len(config_lines)} 行')
            return {"status": "success", "config": config_text}
            
        except Exception as e:
            logger.error(f'获取设备配置异常: {str(e)} (尝试 {attempt + 1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                return {"status": "error", "msg": str(e)}

def check_device_status(port):
    """检查设备状态"""
    host = "127.0.0.1"
    logger.info(f'开始检查设备状态: 主机={host}, 端口={port}')
    
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(3.0)
        client.connect((host, port))
        logger.info(f'设备 {port} 在线')
        
        # 尝试获取设备基本信息
        _flush_buffer(client)
        _ensure_user_view(client)
        
        # 获取设备名称
        hostname_output = _send_and_wait(client, "display current-configuration | include sysname", timeout=3)
        hostname = "Unknown"
        for line in hostname_output.splitlines():
            line = line.strip()
            if line.startswith('sysname'):
                hostname = line.split('sysname ')[1].strip()
                break
        
        client.close()
        
        return {
            "status": "success",
            "port": port,
            "online": True,
            "hostname": hostname
        }
    except ConnectionRefusedError:
        logger.warning(f'设备 {port} 连接被拒绝，可能离线')
        return {
            "status": "success",
            "port": port,
            "online": False,
            "hostname": "Unknown"
        }
    except socket.timeout:
        logger.warning(f'设备 {port} 连接超时，可能离线')
        return {
            "status": "success",
            "port": port,
            "online": False,
            "hostname": "Unknown"
        }
    except Exception as e:
        logger.error(f'检查设备状态异常: {str(e)}')
        return {
            "status": "error",
            "port": port,
            "msg": str(e)
        }