let interfaceCache = [];
let physicalCache = [];
let virtualCache = [];
let currentDevicePort = null;
let currentDeviceCategory = 'unknown';
let currentAvailableTechs = [];
let deviceDataList = [];
let isLoadingInterfaces = false;

const TECH_NAMES = {
    'interface_ip': '📌 接口 IP 地址',
    'vlan': '🔌 VLAN',
    'dhcp': '🌐 DHCP',
    'virtual_interface': '🔄 虚拟接口',
    'eth_trunk': '🔗 Eth-Trunk',
    'stp': '🌲 生成树',
    'static_route': '➡️ 静态路由',
    'rip': '🗺️ RIP',
    'ospf': '🌍 OSPF',
    'bgp': '🌎 BGP',
    'isis': '📡 IS-IS',
    'acl': '🛡️ ACL',
    'nat': '🌊 NAT',
    'vrrp': '⚡ VRRP',
    'wlan': '📶 WLAN'
};

const CATEGORY_NAMES = {
    'switch': '二层交换机',
    'l3_switch': '三层交换机',
    'router': '路由器',
    'firewall': '防火墙',
    'wlan_ac': '无线控制器',
    'unknown': '未知设备'
};

function switchTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ensp-theme', theme);
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-theme') === theme);
    });
}

function initTheme() {
    const saved = localStorage.getItem('ensp-theme') || 'dark-blue';
    switchTheme(saved);
}

function toggleBlock(blockId) {
    const block = document.getElementById(blockId);
    const title = block.previousElementSibling;
    if (block.classList.contains('show')) {
        block.classList.remove('show');
        title.classList.remove('active');
    } else {
        block.classList.add('show');
        title.classList.add('active');
    }
}

function updateStepIndicator(step) {
    document.querySelectorAll('.step-item').forEach((s, index) => {
        if (index + 1 < step) {
            s.classList.add('completed');
            s.classList.remove('active');
        } else if (index + 1 === step) {
            s.classList.add('active');
            s.classList.remove('completed');
        } else {
            s.classList.remove('active', 'completed');
        }
    });
}

updateStepIndicator(1);

function showInterfaceLoadStatus(msg, isError = false) {
    const statusDiv = document.getElementById('interfaceLoadStatus');
    statusDiv.innerHTML = '';
    const statusMsg = document.createElement('div');
    statusMsg.className = isError ? 'status-error' : 'status-success';
    if (msg.includes('正在')) {
        const spinner = document.createElement('span');
        spinner.className = 'spinner me-2';
        statusMsg.appendChild(spinner);
    }
    const msgText = document.createTextNode(msg);
    statusMsg.appendChild(msgText);
    statusDiv.appendChild(statusMsg);
    setTimeout(() => {
        if (statusDiv.contains(statusMsg)) {
            statusDiv.removeChild(statusMsg);
        }
    }, 5000);
}

async function manualLoadInterfaces() {
    const port = currentDevicePort;
    if (!port) { alert('请先选择目标设备'); return; }
    if (isLoadingInterfaces) return;
    isLoadingInterfaces = true;
    showInterfaceLoadStatus('⏳ 正在读取设备接口列表...');
    try {
        const res = await fetch('/api/get_interfaces', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ port: parseInt(port) })
        });
        const data = await res.json();
        if (data.status === 'success') {
            interfaceCache = data.interfaces || [];
            physicalCache = data.physical || [];
            virtualCache = data.virtual || [];
            showInterfaceLoadStatus(`✅ 已读取 ${interfaceCache.length} 个接口 (物理:${physicalCache.length}, 虚拟:${virtualCache.length})`);
            updateInterfaceSelects();
        } else {
            interfaceCache = [];
            physicalCache = [];
            virtualCache = [];
            showInterfaceLoadStatus(`❌ 读取失败: ${data.msg}`, true);
        }
    } catch (e) {
        console.error(e);
        interfaceCache = [];
        physicalCache = [];
        virtualCache = [];
        if (e.name === 'TypeError' && e.message.includes('fetch')) {
            showInterfaceLoadStatus('❌ 后端服务未启动，请确认 app.py 正在运行', true);
        } else {
            showInterfaceLoadStatus('❌ 请求超时，请确认 eNSP 设备已启动(绿色)', true);
        }
    }
    isLoadingInterfaces = false;
}

function makeField(id, label, placeholder, type = 'input') {
    if (type === 'select') {
        return `<div class="form-field"><label for="${id}">${label}</label><select id="${id}">${placeholder}</select></div>`;
    }
    return `<div class="form-field"><label for="${id}">${label}</label><input type="text" id="${id}" placeholder="${placeholder}"></div>`;
}

function makeSelect(id, label, options) {
    const opts = options.map(o => {
        if (typeof o === 'string') return `<option value="${o}">${o}</option>`;
        return `<option value="${o.value}">${o.label}</option>`;
    }).join('');
    return `<div class="form-field"><label for="${id}">${label}</label><select id="${id}">${opts}</select></div>`;
}

function makeGroup(title, content) {
    return `<div class="form-field" style="grid-column: 1 / -1;"><div style="font-weight:600;font-size:13px;color:#409eff;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ecf5ff;">${title}</div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;">${content}</div></div>`;
}

const techForms = {
    interface_ip: () => `
        ${makeField('p_intf_name', '接口名', '如 GigabitEthernet0/0/0')}
        ${makeField('p_ip_address', 'IP 地址', '如 192.168.1.1')}
        ${makeField('p_mask', '子网掩码', '如 255.255.255.0 或 24')}
        ${makeField('p_intf_desc', '接口描述（可选）', '如 TO-CORE-SW')}
        ${makeSelect('p_intf_shutdown', '接口状态', [{value:'undo_shutdown',label:'开启(undo shutdown)'},{value:'shutdown',label:'关闭(shutdown)'}])}
    `,
    vlan: () => `
        ${makeSelect('p_vlan_action', 'VLAN 操作', [{value:'create',label:'创建 VLAN'},{value:'assign',label:'接口加入 VLAN'},{value:'create_and_assign',label:'创建并加入 VLAN'}])}
        <div id="vlan_extras" style="grid-column: 1 / -1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>
    `,
    dhcp: () => `
        ${makeSelect('p_mode', 'DHCP模式', [{value:'interface',label:'接口地址池'},{value:'global',label:'全局地址池'}])}
        <div id="dhcp_extras" style="grid-column: 1 / -1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>
    `,
    virtual_interface: () => `
        ${makeSelect('p_vif_type', '虚拟接口类型', [{value:'vlanif',label:'Vlanif'},{value:'loopback',label:'Loopback'}])}
        <div id="vif_extras" style="grid-column: 1 / -1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>
        ${makeField('p_ip', 'IP 地址', '如 192.168.1.1')}
        ${makeField('p_mask', '子网掩码', '如 255.255.255.0')}
    `,
    eth_trunk: () => `
        ${makeField('p_trunk_id', 'Eth-Trunk 编号', '如 1')}
        ${makeField('p_member_interfaces', '成员接口', '逗号分隔，如 GE0/0/1,GE0/0/2')}
        ${makeSelect('p_mode', '聚合模式', [{value:'manual',label:'手工模式'},{value:'lacp',label:'LACP模式'}])}
    `,
    stp: () => `
        ${makeSelect('p_stp_mode', '生成树模式', [{value:'stp',label:'STP'},{value:'rstp',label:'RSTP'},{value:'mstp',label:'MSTP'}])}
        <div id="stp_extras" style="grid-column: 1 / -1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>
        ${makeField('p_priority', '优先级（可选）', '如 4096')}
    `,
    static_route: () => `
        ${makeField('p_dest_network', '目的网络', '如 10.0.0.0')}
        ${makeField('p_mask', '子网掩码', '如 255.255.255.0')}
        ${makeField('p_next_hop', '下一跳 IP（可选）', '如 192.168.1.254')}
        ${makeField('p_out_interface', '出接口（可选）', '如 GigabitEthernet0/0/1')}
    `,
    rip: () => `
        ${makeField('p_process_id', '进程 ID', '默认 1')}
        ${makeField('p_network', '宣告网络', '如 192.168.1.0')}
    `,
    ospf: () => `
        ${makeField('p_process_id', '进程 ID', '如 1')}
        ${makeField('p_router_id', 'Router ID', '如 1.1.1.1')}
        ${makeField('p_area_id', '区域 ID', '如 0')}
        ${makeField('p_network', '宣告网段', '如 192.168.1.0')}
        ${makeField('p_wildcard_mask', '反掩码', '如 0.0.0.255')}
        ${makeSelect('p_area_type', '区域类型（可选）', [{value:'normal',label:'普通区域'},{value:'stub',label:'Stub 区域'},{value:'nssa',label:'NSSA 区域'}])}
        ${makeField('p_silent_intf', '静默接口（可选）', '如 GigabitEthernet0/0/1')}
    `,
    bgp: () => `
        ${makeField('p_as_number', '本地 AS 号', '如 65001')}
        ${makeField('p_router_id', 'Router ID', '如 1.1.1.1')}
        ${makeField('p_peer_ip', '对等体 IP', '如 10.0.0.2')}
        ${makeField('p_peer_as', '对等体 AS 号', '如 65002')}
        ${makeField('p_network', '宣告网络', '如 192.168.1.0')}
        ${makeField('p_mask', '子网掩码', '如 255.255.255.0')}
    `,
    isis: () => `
        ${makeField('p_process_id', '进程 ID', '如 1')}
        ${makeField('p_net_entity', 'NET 实体', '如 49.0001.0000.0000.0001.00')}
        ${makeField('p_interface', '接口', '如 GigabitEthernet0/0/0')}
    `,
    acl: () => `
        ${makeSelect('p_acl_type', 'ACL 类型', [{value:'standard',label:'标准ACL (2000-2999)'},{value:'extended',label:'扩展ACL (3000-3999)'}])}
        ${makeSelect('p_acl_action', '动作', [{value:'permit',label:'Permit (允许)'},{value:'deny',label:'Deny (拒绝)'}])}
        <div id="acl_extras" style="grid-column: 1 / -1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>
    `,
    nat: () => `
        ${makeField('p_acl_num', 'ACL 编号', '如 2000')}
        ${makeField('p_src_network', '源网络', '如 192.168.1.0')}
        ${makeField('p_src_wildcard', '反掩码', '如 0.0.0.255')}
        ${makeField('p_out_interface', '出接口', '如 GigabitEthernet0/0/1')}
    `,
    vrrp: () => `
        ${makeField('p_interface', '接口', '如 GigabitEthernet0/0/0')}
        ${makeField('p_vrid', 'VRID', '如 1')}
        ${makeField('p_virtual_ip', '虚拟 IP', '如 192.168.1.254')}
        ${makeField('p_priority', '优先级（可选，默认100）', '如 120')}
        ${makeSelect('p_preempt_mode', '抢占模式', [{value:'enable',label:'启用抢占（默认）'},{value:'disable',label:'禁用抢占'}])}
        ${makeField('p_preempt_delay', '抢占延迟（可选，秒）', '如 20')}
        ${makeField('p_auth_mode', '认证模式（可选）', '如 md5 或 simple')}
        ${makeField('p_auth_key', '认证密钥（可选）', '如 huawei123')}
    `,
    wlan: () => `
        ${makeGroup('🔧 AC 源接口', makeField('p_ac_source_interface', '源接口', '如 Vlanif100'))}
        ${makeGroup('📁 AP 组', makeField('p_ap_group_name', 'AP 组名', '如 default'))}
        ${makeGroup('🌐 域管理模板', makeField('p_domain_profile_name', '域管理模板名', '如 domain1'))}
        ${makeGroup('📶 SSID 模板', makeField('p_ssid_profile_name', 'SSID 模板名', '如 ssid1') + makeField('p_ssid_name', 'SSID 名称', '如 Huawei-WiFi'))}
        ${makeGroup('🔐 安全模板', makeField('p_security_profile_name', '安全模板名', '如 sec1') + makeSelect('p_security_mode', '安全模式', [{value:'open',label:'开放'},{value:'psk',label:'PSK'}]) + '<div id="wlan_psk_extras" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>')}
        ${makeGroup('📡 VAP 模板', makeField('p_vap_profile_name', 'VAP 模板名', '如 vap1') + makeField('p_service_vlan', '业务 VLAN ID', '如 100'))}
        ${makeGroup('📱 AP 管理', makeField('p_ap_mac', 'AP MAC 地址', '如 00e0-fc12-3456') + makeField('p_ap_name', 'AP 名称', '如 AP001'))}
    `
};

function makeExtraField(id, label, placeholder) {
    return `<div class="form-field"><label for="${id}">${label}</label><input type="text" id="${id}" placeholder="${placeholder}"></div>`;
}

function _replaceElementClean(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const clone = el.cloneNode(true);
    el.parentNode.replaceChild(clone, el);
    return clone;
}

function bindDynamicExtras() {
    const tech = document.getElementById('techSelect').value;
    if (tech === 'vlan') {
        const action = _replaceElementClean('p_vlan_action');
        const extrasDiv = document.getElementById('vlan_extras');
        const update = () => {
            const act = action.value;
            let html = '';
            if (act === 'create') {
                html = makeField('p_vlan_id', 'VLAN ID', '如 10 或 10,20,30') +
                       makeField('p_vlan_name', 'VLAN 名称（可选）', '如 SALES') +
                       makeField('p_vlan_desc', 'VLAN 描述（可选）', '如 销售部VLAN');
            } else if (act === 'assign') {
                html = makeField('p_vlan_id', 'VLAN ID', '如 10') +
                       makeField('p_interface', '接口名', '如 GigabitEthernet0/0/1') +
                       makeSelect('p_link_type', '链路类型', [{value:'access',label:'Access'},{value:'trunk',label:'Trunk'},{value:'hybrid',label:'Hybrid'}]) +
                       '<div id="vlan_link_extras" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>';
            } else if (act === 'create_and_assign') {
                html = makeField('p_vlan_id', 'VLAN ID', '如 10') +
                       makeField('p_vlan_name', 'VLAN 名称（可选）', '如 SALES') +
                       makeField('p_vlan_desc', 'VLAN 描述（可选）', '如 销售部VLAN') +
                       makeField('p_interface', '接口名', '如 GigabitEthernet0/0/1') +
                       makeSelect('p_link_type', '链路类型', [{value:'access',label:'Access'},{value:'trunk',label:'Trunk'},{value:'hybrid',label:'Hybrid'}]) +
                       '<div id="vlan_link_extras" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;"></div>';
            }
            extrasDiv.innerHTML = html;
            const linkType = document.getElementById('p_link_type');
            const linkExtras = document.getElementById('vlan_link_extras');
            if (linkType && linkExtras) {
                const updateLink = () => {
                    if (linkType.value === 'trunk') {
                        linkExtras.innerHTML = makeField('p_trunk_allowed_vlans', '允许通过的 VLAN', '如 10,20,30') + makeField('p_pvid', 'PVID（可选，默认1）', '如 10');
                    } else if (linkType.value === 'hybrid') {
                        linkExtras.innerHTML = makeExtraField('p_hybrid_untagged_vlans', 'Untagged VLANs', '如 10') + makeExtraField('p_hybrid_tagged_vlans', 'Tagged VLANs', '如 20,30') + makeExtraField('p_pvid', 'PVID（可选）', '如 10');
                    } else {
                        linkExtras.innerHTML = makeField('p_pvid', 'PVID（可选）', '如 10');
                    }
                };
                linkType.addEventListener('change', updateLink);
                updateLink();
            }
            if (interfaceCache.length > 0) {
                setTimeout(() => { updateInterfaceSelects(); }, 0);
            }
        };
        action.addEventListener('change', update);
        update();
    } else if (tech === 'dhcp') {
        const mode = _replaceElementClean('p_mode');
        const extrasDiv = document.getElementById('dhcp_extras');
        const update = () => {
            if (mode.value === 'interface') {
                extrasDiv.innerHTML = makeExtraField('p_interface', '接口名', '如 GigabitEthernet0/0/1') + makeExtraField('p_dns', 'DNS 服务器', '如 8.8.8.8');
            } else {
                extrasDiv.innerHTML = makeExtraField('p_pool_name', '地址池名称', '如 pool1') + makeExtraField('p_gateway', '网关地址', '如 192.168.1.1') + makeExtraField('p_network', '网段', '如 192.168.1.0') + makeExtraField('p_mask', '子网掩码', '如 255.255.255.0') + makeExtraField('p_dns', 'DNS 服务器', '如 8.8.8.8') + makeExtraField('p_interface', '应用接口', '如 GigabitEthernet0/0/1');
            }
            if (interfaceCache.length > 0) {
                setTimeout(() => { updateInterfaceSelects(); }, 0);
            }
        };
        mode.addEventListener('change', update);
        update();
    } else if (tech === 'virtual_interface') {
        const vif = _replaceElementClean('p_vif_type');
        const extrasDiv = document.getElementById('vif_extras');
        const update = () => {
            if (vif.value === 'vlanif') {
                extrasDiv.innerHTML = makeExtraField('p_vlan_id', 'VLAN ID', '如 10');
            } else {
                extrasDiv.innerHTML = makeExtraField('p_loopback_id', 'Loopback ID', '如 0');
            }
        };
        vif.addEventListener('change', update);
        update();
    } else if (tech === 'stp') {
        const mode = _replaceElementClean('p_stp_mode');
        const extrasDiv = document.getElementById('stp_extras');
        const update = () => {
            if (mode.value === 'mstp') {
                extrasDiv.innerHTML = makeExtraField('p_region_name', 'MSTP 域名', '如 region1') + makeExtraField('p_instance_id', '实例 ID', '如 1') + makeExtraField('p_vlan_range', 'VLAN 范围', '如 10-20');
            } else {
                extrasDiv.innerHTML = '';
            }
        };
        mode.addEventListener('change', update);
        update();
    } else if (tech === 'acl') {
        const type = _replaceElementClean('p_acl_type');
        const extrasDiv = document.getElementById('acl_extras');
        const update = () => {
            if (type.value === 'standard') {
                extrasDiv.innerHTML = makeExtraField('p_acl_num', 'ACL 编号', '2000-2999') + makeExtraField('p_rule_id', '规则 ID', '如 5') + makeExtraField('p_src_ip', '源 IP', '如 192.168.1.0') + makeExtraField('p_src_wildcard', '反掩码', '如 0.0.0.255');
            } else {
                extrasDiv.innerHTML = makeExtraField('p_acl_num', 'ACL 编号', '3000-3999') + makeExtraField('p_rule_id', '规则 ID', '如 5') + makeExtraField('p_protocol', '协议', '如 tcp') + makeExtraField('p_src_ip', '源 IP', '如 192.168.1.0') + makeExtraField('p_src_wildcard', '源反掩码', '如 0.0.0.255') + makeExtraField('p_dst_ip', '目的 IP', '如 10.0.0.1') + makeExtraField('p_dst_wildcard', '目的反掩码', '如 0.0.0.0') + makeExtraField('p_dst_port', '目的端口（可选）', '如 eq 80');
            }
        };
        type.addEventListener('change', update);
        update();
    } else if (tech === 'wlan') {
        const mode = _replaceElementClean('p_security_mode');
        const extrasDiv = document.getElementById('wlan_psk_extras');
        if (mode) {
            const update = () => {
                if (mode.value === 'psk') {
                    extrasDiv.innerHTML = makeExtraField('p_psk_password', 'PSK 密码', '如 MyPassword123');
                } else {
                    extrasDiv.innerHTML = '';
                }
            };
            mode.addEventListener('change', update);
            update();
        }
    }
}

function replaceInputWithSelectList(inputElement, list, multiple = false, placeholderText = '-- 请选择接口 --') {
    if (!inputElement || inputElement.tagName !== 'INPUT') return inputElement;
    const select = document.createElement('select');
    if (multiple) {
        select.multiple = true;
        select.size = Math.min(list.length + 1, 6);
    }
    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.text = multiple ? '-- 按住 Ctrl 多选 --' : placeholderText;
    select.appendChild(emptyOpt);
    list.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.text = item;
        select.appendChild(opt);
    });
    if (inputElement.value) {
        const vals = inputElement.value.split(',').map(v => v.trim());
        for (let i = 0; i < select.options.length; i++) {
            if (vals.includes(select.options[i].value)) {
                select.options[i].selected = true;
            }
        }
    }
    inputElement.parentNode.replaceChild(select, inputElement);
    select.id = inputElement.id;
    return select;
}

function getInterfaceListForTech(tech, fieldId) {
    const physicalOnlyTechs = ['vlan', 'eth_trunk'];
    const virtualOnlyFields = ['p_ac_source_interface'];
    if (tech === 'nat' && fieldId === 'p_out_interface') return physicalCache;
    if (physicalOnlyTechs.includes(tech)) return physicalCache;
    if (virtualOnlyFields.includes(fieldId)) return virtualCache;
    return interfaceCache;
}

function replaceInputWithSmartSelect(inputElement, tech, fieldId, multiple = false) {
    let list = getInterfaceListForTech(tech, fieldId);
    if (!list || list.length === 0) list = interfaceCache;
    let placeholder = '-- 请选择接口 --';
    if (fieldId === 'p_member_interfaces') placeholder = '-- 按住 Ctrl 多选 --';
    return replaceInputWithSelectList(inputElement, list, multiple, placeholder);
}

function updateInterfaceSelects() {
    if (interfaceCache.length === 0) return;
    const tech = document.getElementById('techSelect').value;
    const configs = [
        { id: 'p_intf_name', multiple: false },
        { id: 'p_interface', multiple: false },
        { id: 'p_out_interface', multiple: false },
        { id: 'p_member_interfaces', multiple: true },
        { id: 'p_ac_source_interface', multiple: false }
    ];
    for (let cfg of configs) {
        let el = document.getElementById(cfg.id);
        if (el) {
            let list = getInterfaceListForTech(tech, cfg.id);
            if (!list || list.length === 0) list = interfaceCache;
            if (el.tagName === 'INPUT') {
                replaceInputWithSmartSelect(el, tech, cfg.id, cfg.multiple);
            } else if (el.tagName === 'SELECT') {
                let currentVal = el.value;
                let selectedVals = [];
                if (el.multiple) {
                    selectedVals = Array.from(el.selectedOptions).map(o => o.value).filter(v => v);
                }
                let placeholder = cfg.multiple ? '-- 按住 Ctrl 多选 --' : '-- 请选择接口 --';
                if (cfg.id === 'p_member_interfaces') placeholder = '-- 按住 Ctrl 多选 --';
                el.innerHTML = '';
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.text = placeholder;
                el.appendChild(emptyOpt);
                list.forEach(item => {
                    const opt = document.createElement('option');
                    opt.value = item;
                    opt.text = item;
                    el.appendChild(opt);
                });
                if (el.multiple && selectedVals.length > 0) {
                    for (let i = 0; i < el.options.length; i++) {
                        if (selectedVals.includes(el.options[i].value)) {
                            el.options[i].selected = true;
                        }
                    }
                } else if (currentVal) {
                    el.value = currentVal;
                }
            }
        }
    }
}

function changeTech() {
    const tech = document.getElementById('techSelect').value;
    console.log(`[changeTech] 开始, tech=${tech}, currentDevicePort=${currentDevicePort}`);
    const formArea = document.getElementById('formArea');
    if (!techForms[tech]) {
        formArea.innerHTML = '<p style="color:#f56c6c;padding:20px;">暂未支持该技术</p>';
        return;
    }
    formArea.innerHTML = techForms[tech]();
    console.log(`[changeTech] 表单已生成`);
    bindDynamicExtras();
    console.log(`[changeTech] 动态字段已绑定`);
    if (interfaceCache.length > 0) {
        setTimeout(() => { updateInterfaceSelects(); }, 0);
    }
    if (currentDevicePort) {
        console.log(`[changeTech] currentDevicePort=${currentDevicePort}, 准备调用 autoReadCurrentParams`);
        setTimeout(() => { autoReadCurrentParams(tech); }, 100);
    } else {
        console.log(`[changeTech] currentDevicePort 为空, 跳过自动读取`);
    }
}

async function autoReadCurrentParams(tech) {
    const port = currentDevicePort;
    console.log(`[autoRead] 开始, tech=${tech}, port=${port}`);
    if (!port) {
        console.log('[autoRead] 失败: currentDevicePort 为空');
        return;
    }
    try {
        console.log(`[autoRead] 发送请求到 /api/read_current_params`);
        const res = await Promise.race([
            fetch('/api/read_current_params', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ port: parseInt(port), tech: tech })
            }),
            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
        ]);
        console.log(`[autoRead] 收到响应, status=${res.status}`);
        const data = await res.json();
        console.log(`[autoRead] 数据:`, data);

        if (data.status === 'success') {
            const params = data.params || data.data || {};
            if (params && Object.keys(params).length > 0) {
                console.log(`[autoRead] 成功, 填充参数:`, params);
                fillFormParams(params, tech);
            } else {
                console.log(`[autoRead] 成功但无参数: ${data.msg || '未找到配置'}`);
            }
        } else {
            console.log(`[autoRead] 失败: ${data.msg}`);
        }
    } catch (e) {
        console.error('[autoRead] 异常:', e);
    }
}

function fillFormParams(params, tech) {
    if (tech === 'vlan') {
        let vlanAction = 'create_and_assign';
        if (params.interface && params.link_type) {
            vlanAction = 'assign';
        } else if (params.vlan_id && !params.interface) {
            vlanAction = 'create';
        }
        const originalParams = { ...params };
        delete originalParams.vlan_id;
        delete originalParams.vlan_name;
        delete originalParams.vlan_desc;
        delete originalParams.interface;
        delete originalParams.link_type;
        delete originalParams.trunk_allowed_vlans;
        delete originalParams.pvid;
        delete originalParams.vlan_action;

        const waitForVLANForm = (attempt) => {
            if (attempt > 20) return;
            const actionEl = document.getElementById('p_vlan_action');
            if (!actionEl) {
                setTimeout(() => waitForVLANForm(attempt + 1), 100);
                return;
            }
            actionEl.value = vlanAction;
            actionEl.dispatchEvent(new Event('change'));
            setTimeout(() => {
                if (originalParams.vlan_id) {
                    const el = document.getElementById('p_vlan_id');
                    if (el) el.value = originalParams.vlan_id;
                }
                if (originalParams.vlan_name) {
                    const el = document.getElementById('p_vlan_name');
                    if (el) el.value = originalParams.vlan_name;
                }
                if (originalParams.vlan_desc) {
                    const el = document.getElementById('p_vlan_desc');
                    if (el) el.value = originalParams.vlan_desc;
                }
                if (originalParams.interface) {
                    const el = document.getElementById('p_interface');
                    if (el) el.value = originalParams.interface;
                }
                if (originalParams.link_type) {
                    const el = document.getElementById('p_link_type');
                    if (el) {
                        el.value = originalParams.link_type;
                        el.dispatchEvent(new Event('change'));
                    }
                }
                setTimeout(() => {
                    if (originalParams.trunk_allowed_vlans) {
                        const el = document.getElementById('p_trunk_allowed_vlans');
                        if (el) el.value = originalParams.trunk_allowed_vlans;
                    }
                    if (originalParams.pvid) {
                        const el = document.getElementById('p_pvid');
                        if (el) el.value = originalParams.pvid;
                    }
                }, 100);
            }, 100);
        };
        waitForVLANForm(0);
    } else {
        const waitForForm = (attempt) => {
            if (attempt > 20) return;
            const firstKey = Object.keys(params)[0];
            if (!document.getElementById(`p_${firstKey}`)) {
                setTimeout(() => waitForForm(attempt + 1), 100);
                return;
            }
            for (let key in params) {
                const el = document.getElementById(`p_${key}`);
                if (el) {
                    if (el.tagName === 'SELECT' && el.multiple) {
                        const values = params[key].split(',');
                        for (let i = 0; i < el.options.length; i++) {
                            el.options[i].selected = values.includes(el.options[i].value);
                        }
                    } else {
                        el.value = params[key];
                    }
                }
            }
        };
        waitForForm(0);
    }
}

async function uploadTopo() {
    const fileInput = document.getElementById('topoFile');
    if (!fileInput.files.length) { alert('请选择.topo文件'); return; }
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    const res = await fetch('/api/upload_topo', { method: 'POST', body: fd });
    const data = await res.json();
    const select = document.getElementById('deviceSelect');
    const readBtn = document.getElementById('readInterfacesBtn');
    if (data.status === 'success') {
        deviceDataList = data.data;
        select.innerHTML = '<option value="">请选择设备</option>';
        data.data.forEach(dev => {
            const opt = document.createElement('option');
            opt.value = dev.port;
            const catName = CATEGORY_NAMES[dev.category] || dev.category;
            opt.text = `${dev.name} [${catName}] - 端口:${dev.port}`;
            select.appendChild(opt);
        });
        alert('解析成功！');
        updateStepIndicator(2);
        select.onchange = () => {
            const port = select.value;
            if (port) {
                currentDevicePort = port;
                const dev = deviceDataList.find(d => d.port == port);
                if (dev) {
                    currentDeviceCategory = dev.category || 'unknown';
                    currentAvailableTechs = dev.available_techs || [];
                }
                readBtn.disabled = false;
                document.getElementById('readConfigBtn').disabled = false;
                document.getElementById('saveConfigBtn').disabled = false;
                interfaceCache = [];
                physicalCache = [];
                virtualCache = [];
                showInterfaceLoadStatus(`设备类型: ${CATEGORY_NAMES[currentDeviceCategory] || currentDeviceCategory}，请点击"读取设备接口"`);
                updateTechSelect();
            } else {
                currentDevicePort = null;
                currentDeviceCategory = 'unknown';
                currentAvailableTechs = [];
                readBtn.disabled = true;
                interfaceCache = [];
                physicalCache = [];
                virtualCache = [];
                showInterfaceLoadStatus('');
                updateTechSelect();
            }
        };
        if (select.value) {
            currentDevicePort = select.value;
            const dev = deviceDataList.find(d => d.port == select.value);
            if (dev) {
                currentDeviceCategory = dev.category || 'unknown';
                currentAvailableTechs = dev.available_techs || [];
            }
            readBtn.disabled = false;
            document.getElementById('readConfigBtn').disabled = false;
            document.getElementById('saveConfigBtn').disabled = false;
            interfaceCache = [];
            physicalCache = [];
            virtualCache = [];
            showInterfaceLoadStatus(`设备类型: ${CATEGORY_NAMES[currentDeviceCategory] || currentDeviceCategory}，请点击"读取设备接口"`);
            updateTechSelect();
        } else {
            readBtn.disabled = true;
        }
    } else {
        alert('解析失败: ' + data.msg);
    }
}

function updateTechSelect() {
    const techSelect = document.getElementById('techSelect');
    const currentVal = techSelect.value;
    techSelect.innerHTML = '';
    const allTechs = [
        'interface_ip', 'vlan', 'dhcp', 'virtual_interface', 'eth_trunk',
        'stp', 'static_route', 'rip', 'ospf', 'bgp', 'isis', 'acl', 'nat', 'vrrp', 'wlan'
    ];
    const available = currentAvailableTechs.length > 0 ? currentAvailableTechs : allTechs;
    allTechs.forEach(tech => {
        const opt = document.createElement('option');
        opt.value = tech;
        opt.text = TECH_NAMES[tech] || tech;
        if (!available.includes(tech)) {
            opt.disabled = true;
            opt.text += ' (不适用)';
        }
        techSelect.appendChild(opt);
    });
    if (available.includes(currentVal)) {
        techSelect.value = currentVal;
    } else {
        techSelect.value = available[0] || 'interface_ip';
    }
    changeTech();
}

// 批量配置相关函数
let selectedBatchDevices = [];

function toggleBatchMode() {
    const batchMode = document.getElementById('batchMode').checked;
    const deviceSelect = document.getElementById('deviceSelect');
    if (batchMode) {
        // 启用批量模式，修改设备选择为多选
        deviceSelect.multiple = true;
        deviceSelect.size = Math.min(deviceDataList.length + 1, 6);
        deviceSelect.onchange = updateBatchDevicesList;
    } else {
        // 禁用批量模式，恢复为单选
        deviceSelect.multiple = false;
        deviceSelect.size = 1;
        deviceSelect.onchange = function() {
            const port = deviceSelect.value;
            if (port) {
                currentDevicePort = port;
                const dev = deviceDataList.find(d => d.port == port);
                if (dev) {
                    currentDeviceCategory = dev.category || 'unknown';
                    currentAvailableTechs = dev.available_techs || [];
                }
                document.getElementById('readInterfacesBtn').disabled = false;
                document.getElementById('readConfigBtn').disabled = false;
                document.getElementById('saveConfigBtn').disabled = false;
                interfaceCache = [];
                physicalCache = [];
                virtualCache = [];
                showInterfaceLoadStatus(`设备类型: ${CATEGORY_NAMES[currentDeviceCategory] || currentDeviceCategory}，请点击"读取设备接口"`);
                updateTechSelect();
            } else {
                currentDevicePort = null;
                currentDeviceCategory = 'unknown';
                currentAvailableTechs = [];
                document.getElementById('readInterfacesBtn').disabled = true;
                document.getElementById('readConfigBtn').disabled = true;
                document.getElementById('saveConfigBtn').disabled = true;
                interfaceCache = [];
                physicalCache = [];
                virtualCache = [];
                showInterfaceLoadStatus('');
                updateTechSelect();
            }
        };
        updateTechSelect();
    }
    updateBatchDevicesList();
}

function updateBatchDevicesList() {
    const deviceSelect = document.getElementById('deviceSelect');
    const batchMode = document.getElementById('batchMode').checked;
    const batchDevicesList = document.getElementById('batchDevicesList');
    const batchPushBtn = document.getElementById('batchPushBtn');
    
    if (!batchMode) {
        batchDevicesList.innerHTML = '<p class="text-muted text-center small">选择设备后将显示在此处</p>';
        batchPushBtn.disabled = true;
        return;
    }
    
    selectedBatchDevices = [];
    for (let i = 0; i < deviceSelect.options.length; i++) {
        if (deviceSelect.options[i].selected && deviceSelect.options[i].value) {
            const port = deviceSelect.options[i].value;
            const dev = deviceDataList.find(d => d.port == port);
            if (dev) {
                selectedBatchDevices.push(dev);
            }
        }
    }
    
    if (selectedBatchDevices.length === 0) {
        batchDevicesList.innerHTML = '<p class="text-muted text-center small">请选择要批量配置的设备</p>';
        batchPushBtn.disabled = true;
    } else {
        batchDevicesList.innerHTML = '';
        selectedBatchDevices.forEach(dev => {
            const deviceItem = document.createElement('div');
            deviceItem.className = 'template-item';
            const catName = CATEGORY_NAMES[dev.category] || dev.category;
            deviceItem.innerHTML = `
                <div>
                    <div style="font-weight:600;color:#dce6f0;">${dev.name}</div>
                    <div style="font-size:11px;color:#5a7a94;">${catName} · 端口:${dev.port}</div>
                </div>
            `;
            batchDevicesList.appendChild(deviceItem);
        });
        batchPushBtn.disabled = false;
    }
}

async function batchPushConfig() {
    const tech = document.getElementById('techSelect').value;
    const terminal = document.getElementById('terminal');
    if (selectedBatchDevices.length === 0) {
        alert('请选择要批量配置的设备');
        return;
    }
    updateStepIndicator(3);
    switchPanel('terminal');
    
    // 验证和预览配置
    const previewResult = await validateAndPreviewConfig();
    if (!previewResult || !previewResult.success) {
        return;
    }
    
    const params = previewResult.params;
    
    // 批量推送配置
    terminal.innerHTML += `⏳ 正在批量配置 ${selectedBatchDevices.length} 个设备...\n`;
    try {
        const res = await fetch('/api/batch_push_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                devices: selectedBatchDevices, 
                tech: tech, 
                params: params 
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            terminal.innerHTML += `✅ 批量配置完成\n`;
            data.results.forEach(result => {
                terminal.innerHTML += `\n=== 设备: ${result.device_name} (端口: ${result.port}) ===\n`;
                if (result.status === 'success') {
                    terminal.innerHTML += `✅ 配置成功\n`;
                } else {
                    terminal.innerHTML += `❌ 配置失败: ${result.msg || result.log}\n`;
                }
            });
        } else {
            terminal.innerHTML += `❌ 批量配置失败: ${data.msg}\n`;
        }
    } catch (e) {
        console.error('批量配置失败:', e);
        terminal.innerHTML += '❌ 批量配置失败，请检查网络连接\n';
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function checkAllDevicesStatus() {
    const deviceStatusList = document.getElementById('deviceStatusList');
    deviceStatusList.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> 正在检查设备状态...</div>';
    
    try {
        const ports = deviceDataList.map(dev => dev.port);
        if (ports.length === 0) {
            deviceStatusList.innerHTML = '<p class="text-muted text-center small">请先解析拓扑文件</p>';
            return;
        }
        
        const res = await fetch('/api/check_device_status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ ports: ports })
        });
        
        const data = await res.json();
        if (data.status === 'success') {
            deviceStatusList.innerHTML = '';
            data.results.forEach(result => {
                const deviceItem = document.createElement('div');
                deviceItem.className = 'template-item';
                const dev = deviceDataList.find(d => d.port == result.port);
                const deviceName = dev ? dev.name : `设备${result.port}`;
                const statusClass = result.online ? 'status-online' : 'status-offline';
                const statusIcon = result.online ? 'fas fa-check-circle' : 'fas fa-times-circle';
                const statusText = result.online ? '在线' : '离线';
                
                deviceItem.innerHTML = `
                    <div>
                        <div style="font-weight:600;color:#dce6f0;">${deviceName}</div>
                        <div style="font-size:11px;color:#5a7a94;">端口:${result.port} · ${result.hostname || '未知主机名'}</div>
                    </div>
                    <div style="display:flex;align-items:center;">
                        <span class="${statusClass}"><i class="${statusIcon}"></i> ${statusText}</span>
                    </div>
                `;
                deviceStatusList.appendChild(deviceItem);
            });
        } else {
            deviceStatusList.innerHTML = `<p class="text-danger text-center small">检查失败: ${data.msg}</p>`;
        }
    } catch (e) {
        console.error('检查设备状态失败:', e);
        deviceStatusList.innerHTML = '<p class="text-danger text-center small">检查设备状态失败，请检查网络连接</p>';
    }
}

function getDeviceType() {
    const dev = deviceDataList.find(d => d.port == currentDevicePort);
    return dev ? dev.type || '' : '';
}

function switchPanel(panel) {
    const terminal = document.getElementById('terminal');
    const editor = document.getElementById('configEditor');
    if (panel === 'terminal') {
        terminal.style.display = 'block';
        editor.style.display = 'none';
    } else {
        terminal.style.display = 'none';
        editor.style.display = 'flex';
    }
}

async function readDeviceConfig() {
    const port = currentDevicePort;
    if (!port) { alert('请先选择目标设备'); return; }
    const terminal = document.getElementById('terminal');
    terminal.innerHTML = "⏳ 正在读取设备配置...\n";
    try {
        const res = await fetch('/api/get_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ port: parseInt(port) })
        });
        const data = await res.json();
        if (data.status === 'success') {
            const config = data.config;
            let displayText = "";
            displayText += "=".repeat(80) + "\n";
            displayText += "                     设备完整配置信息\n";
            displayText += "=".repeat(80) + "\n";

            if (config.other_config && config.other_config.full_running_config) {
                displayText += config.other_config.full_running_config + "\n";
            }

            displayText += "=".repeat(80) + "\n";
            displayText += `配置读取完成，共 ${displayText.split('\n').length} 行\n`;
            displayText += "=".repeat(80) + "\n";

            document.getElementById('configTextarea').value = displayText;
            switchPanel('editor');
            terminal.innerHTML += `✅ 配置读取成功，共 ${displayText.split('\n').length} 行\n`;
        } else {
            terminal.innerHTML += `❌ 读取失败: ${data.msg}\n`;
        }
    } catch (e) {
        console.error(e);
        terminal.innerHTML += '❌ 读取配置失败，请检查设备连接\n';
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function pushCustomConfig() {
    const port = currentDevicePort;
    if (!port) { alert('请先选择目标设备'); return; }
    const commands = document.getElementById('configTextarea').value.trim();
    if (!commands) { alert('配置内容不能为空'); return; }
    const terminal = document.getElementById('terminal');
    switchPanel('terminal');
    terminal.innerHTML = "⏳ 正在推送自定义配置...\n";
    try {
        const res = await fetch('/api/push_custom_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ port: parseInt(port), commands: commands })
        });
        const data = await res.json();
        if (data.status === 'success') {
            terminal.innerHTML += '✅ 配置推送完成\n';
            terminal.innerHTML += data.log;
        } else {
            terminal.innerHTML += `❌ 推送失败: ${data.msg}\n`;
        }
    } catch (e) {
        console.error(e);
        terminal.innerHTML += '❌ 推送配置失败，请检查设备连接\n';
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function saveDeviceConfig() {
    const port = currentDevicePort;
    if (!port) { alert('请先选择目标设备'); return; }
    const terminal = document.getElementById('terminal');
    switchPanel('terminal');
    terminal.innerHTML = "⏳ 正在保存配置到设备...\n";
    try {
        const res = await fetch('/api/save_device_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ port: parseInt(port) })
        });
        const data = await res.json();
        if (data.status === 'success') {
            terminal.innerHTML += `✅ ${data.msg}\n`;
            if (data.log) terminal.innerHTML += data.log;
        } else {
            terminal.innerHTML += `❌ 保存失败: ${data.msg}\n`;
        }
    } catch (e) {
        console.error(e);
        terminal.innerHTML += '❌ 保存配置失败，请检查设备连接\n';
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function readCurrentParams() {
    const port = document.getElementById('deviceSelect').value;
    const tech = document.getElementById('techSelect').value;
    if (!port) { alert('请先解析拓扑并选择设备'); return; }
    const terminal = document.getElementById('terminal');
    switchPanel('terminal');
    terminal.innerHTML += "\n⏳ 正在读取设备当前配置参数...\n";
    try {
        const res = await fetch('/api/read_current_params', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ port: parseInt(port), tech: tech })
        });
        const data = await res.json();
        console.log('📡 后端返回数据:', data);

        if (data.status === 'success') {
            const params = data.params || data.data || {};
            if (!params || Object.keys(params).length === 0) {
                terminal.innerHTML += `⚠️ ${data.msg || '未找到相关配置参数'}\n`;
                return;
            }
            terminal.innerHTML += `✅ 配置参数读取成功，已填充到表单\n`;
            terminal.innerHTML += `📋 读取到的参数: ${JSON.stringify(params, null, 2)}\n`;
            console.log('📋 解析后的参数:', params);

            const fillParams = (p) => {
                for (let key in p) {
                    const el = document.getElementById(`p_${key}`);
                    if (el) {
                        if (el.tagName === 'SELECT' && el.multiple) {
                            const values = p[key].split(',');
                            for (let i = 0; i < el.options.length; i++) {
                                el.options[i].selected = values.includes(el.options[i].value);
                            }
                        } else {
                            el.value = p[key];
                        }
                        console.log(`✅ 填充 ${key}: ${p[key]}`);
                    } else {
                        console.log(`⚠️ 元素不存在: p_${key}`);
                    }
                }
            };

            if (tech === 'vlan') {
                let vlanAction = 'create_and_assign';
                if (params.interface && params.link_type) {
                    vlanAction = 'assign';
                } else if (params.vlan_id && !params.interface) {
                    vlanAction = 'create';
                }

                const originalParams = { ...params };
                delete originalParams.vlan_id;
                delete originalParams.vlan_name;
                delete originalParams.vlan_desc;
                delete originalParams.interface;
                delete originalParams.link_type;
                delete originalParams.trunk_allowed_vlans;
                delete originalParams.pvid;
                delete originalParams.vlan_action;

                document.getElementById('techSelect').value = 'vlan';
                changeTech();

                const waitForVLANForm = (attempt) => {
                    if (attempt > 20) {
                        terminal.innerHTML += `⚠️ 表单生成超时\n`;
                        return;
                    }
                    const actionEl = document.getElementById('p_vlan_action');
                    if (!actionEl) {
                        console.log(`🔍 等待 VLAN 表单生成... ${attempt}/20`);
                        setTimeout(() => waitForVLANForm(attempt + 1), 150);
                        return;
                    }

                    actionEl.value = vlanAction;
                    console.log(`📝 设置 VLAN action: ${vlanAction}`);
                    actionEl.dispatchEvent(new Event('change'));

                    setTimeout(() => {
                        if (originalParams.vlan_id) {
                            const vlanIdEl = document.getElementById('p_vlan_id');
                            if (vlanIdEl) vlanIdEl.value = originalParams.vlan_id;
                        }
                        if (originalParams.vlan_name) {
                            const vlanNameEl = document.getElementById('p_vlan_name');
                            if (vlanNameEl) vlanNameEl.value = originalParams.vlan_name;
                        }
                        if (originalParams.vlan_desc) {
                            const vlanDescEl = document.getElementById('p_vlan_desc');
                            if (vlanDescEl) vlanDescEl.value = originalParams.vlan_desc;
                        }
                        if (originalParams.interface) {
                            const intfEl = document.getElementById('p_interface');
                            if (intfEl) intfEl.value = originalParams.interface;
                        }
                        if (originalParams.link_type) {
                            const linkTypeEl = document.getElementById('p_link_type');
                            if (linkTypeEl) {
                                linkTypeEl.value = originalParams.link_type;
                                linkTypeEl.dispatchEvent(new Event('change'));
                            }
                        }

                        setTimeout(() => {
                            if (originalParams.trunk_allowed_vlans) {
                                const trunkEl = document.getElementById('p_trunk_allowed_vlans');
                                if (trunkEl) trunkEl.value = originalParams.trunk_allowed_vlans;
                            }
                            if (originalParams.pvid) {
                                const pvidEl = document.getElementById('p_pvid');
                                if (pvidEl) pvidEl.value = originalParams.pvid;
                            }
                            console.log('✅ VLAN 参数填充完成');
                        }, 150);
                    }, 150);
                };
                waitForVLANForm(0);
            } else {
                changeTech();
                const waitForForm = (attempt) => {
                    if (attempt > 20) {
                        terminal.innerHTML += `⚠️ 表单生成超时\n`;
                        return;
                    }
                    const firstKey = Object.keys(params)[0];
                    if (!document.getElementById(`p_${firstKey}`)) {
                        console.log(`🔍 等待表单生成... ${attempt}/20`);
                        setTimeout(() => waitForForm(attempt + 1), 150);
                        return;
                    }
                    fillParams(params);
                };
                waitForForm(0);
            }
        } else {
            terminal.innerHTML += `❌ 读取失败: ${data.msg}\n`;
        }
    } catch (e) {
        console.error(e);
        terminal.innerHTML += '❌ 读取配置参数失败，请检查设备连接\n';
    }
    terminal.scrollTop = terminal.scrollHeight;
}

function validateForm(tech, params) {
    const errors = [];
    if (tech === 'interface_ip') {
        if (!params.intf_name) errors.push('接口名不能为空');
        if (!params.ip_address) { errors.push('IP地址不能为空'); }
        else if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(params.ip_address)) { errors.push('IP地址格式不正确'); }
        if (!params.mask) { errors.push('掩码不能为空'); }
        else if (!/^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\d{1,2})$/.test(params.mask)) { errors.push('掩码格式不正确'); }
    } else if (tech === 'vlan') {
        if (!params.vlan_id) errors.push('VLAN ID不能为空');
        else if (!/^\d{1,4}(,\d{1,4})*$/.test(params.vlan_id.replace(/\s/g, ''))) { errors.push('VLAN ID格式不正确'); }
        else {
            const ids = params.vlan_id.split(',');
            for (const id of ids) {
                const n = parseInt(id.trim());
                if (n < 1 || n > 4094) { errors.push(`VLAN ID ${id} 必须在1-4094之间`); }
            }
        }
        const action = params.vlan_action || 'create_and_assign';
        if (action !== 'create' && !params.interface) errors.push('接口名不能为空');
        if (params.link_type === 'trunk' && !params.trunk_allowed_vlans) { errors.push('Trunk模式需要填写允许通过的VLAN列表'); }
    } else if (tech === 'dhcp') {
        if (params.mode === 'interface') {
            if (!params.interface) errors.push('接口名不能为空');
            if (!params.dns) errors.push('DNS服务器不能为空');
        } else {
            if (!params.pool_name) errors.push('地址池名称不能为空');
            if (!params.gateway) errors.push('网关地址不能为空');
            if (!params.network) errors.push('网段不能为空');
            if (!params.mask) errors.push('掩码不能为空');
            if (!params.dns) errors.push('DNS服务器不能为空');
            if (!params.interface) errors.push('应用接口不能为空');
        }
    } else if (tech === 'virtual_interface') {
        if (params.vif_type === 'vlanif') { if (!params.vlan_id) errors.push('VLAN ID不能为空'); }
        else { if (!params.loopback_id) errors.push('Loopback ID不能为空'); }
        if (!params.ip) errors.push('IP地址不能为空');
        if (!params.mask) errors.push('掩码不能为空');
    } else if (tech === 'static_route') {
        if (!params.dest_network) errors.push('目的网络不能为空');
        if (!params.mask) errors.push('掩码不能为空');
        if (!params.next_hop && !params.out_interface) { errors.push('请填写下一跳IP或出接口'); }
    } else if (tech === 'ospf') {
        if (!params.router_id) errors.push('Router ID不能为空');
        if (!params.network) errors.push('宣告网段不能为空');
        if (!params.wildcard_mask) errors.push('反掩码不能为空');
    } else if (tech === 'bgp') {
        if (!params.as_number) errors.push('本地AS号不能为空');
        if (!params.router_id) errors.push('Router ID不能为空');
        if (!params.peer_ip) errors.push('对等体IP不能为空');
        if (!params.peer_as) errors.push('对等体AS号不能为空');
        if (!params.network) errors.push('宣告网络不能为空');
        if (!params.mask) errors.push('掩码不能为空');
    } else if (tech === 'nat') {
        if (!params.acl_num) errors.push('ACL编号不能为空');
        if (!params.src_network) errors.push('源网络不能为空');
        if (!params.src_wildcard) errors.push('反掩码不能为空');
        if (!params.out_interface) errors.push('出接口不能为空');
    } else if (tech === 'vrrp') {
        if (!params.interface) errors.push('接口不能为空');
        if (!params.vrid) errors.push('VRID不能为空');
        if (!params.virtual_ip) errors.push('虚拟IP不能为空');
    }
    return errors;
}

async function validateAndPreviewConfig() {
    const tech = document.getElementById('techSelect').value;
    const terminal = document.getElementById('terminal');
    let params = {};
    const formArea = document.getElementById('formArea');
    const elements = formArea.querySelectorAll('input, select');
    for (let el of elements) {
        let key = el.id.replace('p_', '');
        if (el.tagName === 'SELECT' && el.multiple) {
            let vals = Array.from(el.selectedOptions).map(o => o.value).filter(v => v);
            if (vals.length) params[key] = vals.join(',');
        } else if (el.tagName === 'SELECT') {
            if (el.value) params[key] = el.value;
        } else if (el.tagName === 'INPUT') {
            if (el.value) params[key] = el.value;
        }
    }
    if (params.mask && !params.mask.includes('.')) {
        let len = parseInt(params.mask);
        if (len >= 0 && len <= 32) {
            let maskParts = [];
            for (let i = 0; i < 4; i++) {
                if (len >= 8) { maskParts.push(255); len -= 8; }
                else if (len > 0) { maskParts.push(256 - Math.pow(2, 8 - len)); len = 0; }
                else { maskParts.push(0); }
            }
            params.mask = maskParts.join('.');
        }
    }
    
    // 前端验证
    const validationErrors = validateForm(tech, params);
    if (validationErrors.length > 0) {
        terminal.innerHTML = "❌ 表单验证失败:\n";
        validationErrors.forEach(error => { terminal.innerHTML += `- ${error}\n`; });
        return false;
    }
    
    // 后端验证
    terminal.innerHTML = "⏳ 正在验证配置参数...\n";
    try {
        const res = await fetch('/api/validate_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tech: tech, params: params })
        });
        const data = await res.json();
        if (!data.valid) {
            terminal.innerHTML += `❌ 配置验证失败: ${data.error}\n`;
            return false;
        }
        terminal.innerHTML += "✅ 配置参数验证通过\n";
    } catch (e) {
        console.error('配置验证失败:', e);
        terminal.innerHTML += '❌ 配置验证失败，请检查网络连接\n';
        return false;
    }
    
    // 生成配置预览
    terminal.innerHTML += "⏳ 正在生成配置预览...\n";
    try {
        const res = await fetch('/api/preview_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tech: tech, params: params, device_type: getDeviceType() })
        });
        const data = await res.json();
        if (data.status === 'success') {
            terminal.innerHTML += "✅ 配置预览生成成功\n";
            terminal.innerHTML += "\n📋 生成的配置命令:\n";
            terminal.innerHTML += data.config;
            terminal.innerHTML += "\n";
            return { success: true, params: params };
        } else {
            terminal.innerHTML += `❌ 配置预览生成失败: ${data.msg}\n`;
            return false;
        }
    } catch (e) {
        console.error('配置预览生成失败:', e);
        terminal.innerHTML += '❌ 配置预览生成失败，请检查网络连接\n';
        return false;
    }
}

async function pushConfig() {
    const port = document.getElementById('deviceSelect').value;
    const tech = document.getElementById('techSelect').value;
    const terminal = document.getElementById('terminal');
    if (!port) { alert('请先解析拓扑并选择设备'); return; }
    updateStepIndicator(3);
    switchPanel('terminal');
    
    // 验证和预览配置
    const previewResult = await validateAndPreviewConfig();
    if (!previewResult || !previewResult.success) {
        return;
    }
    
    const params = previewResult.params;
    
    // 推送配置到设备
    terminal.innerHTML += "⏳ 正在连接设备并下发命令...\n";
    try {
        const res = await fetch('/api/push_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ port: parseInt(port), tech: tech, params: params, device_type: getDeviceType() })
        });
        const data = await res.json();
        terminal.innerHTML += data.log;
    } catch (e) {
        console.error(e);
        if (e.name === 'TypeError' && e.message.includes('fetch')) {
            terminal.innerHTML += '❌ 后端服务未启动，请确认 app.py 正在运行\n';
        } else {
            terminal.innerHTML += '❌ 请求超时，请确认 eNSP 设备已启动(绿色)\n';
        }
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function saveTemplate() {
    const templateName = document.getElementById('templateName').value.trim();
    const tech = document.getElementById('techSelect').value;
    if (!templateName) { alert('请输入模板名称'); return; }
    let params = {};
    const formArea = document.getElementById('formArea');
    const elements = formArea.querySelectorAll('input, select');
    for (let el of elements) {
        let key = el.id.replace('p_', '');
        if (el.tagName === 'SELECT' && el.multiple) {
            let vals = Array.from(el.selectedOptions).map(o => o.value).filter(v => v);
            if (vals.length) params[key] = vals.join(',');
        } else if (el.tagName === 'SELECT') {
            if (el.value) params[key] = el.value;
        } else if (el.tagName === 'INPUT') {
            if (el.value) params[key] = el.value;
        }
    }
    try {
        const res = await fetch('/api/save_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: templateName, tech: tech, params: params })
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert('模板保存成功');
            document.getElementById('templateName').value = '';
            loadTemplates();
            addHistory('保存模板', { template_name: templateName, tech: tech });
        } else {
            alert('保存失败: ' + data.msg);
        }
    } catch (e) {
        console.error('保存模板失败:', e);
        alert('保存模板失败，请检查网络连接');
    }
}

async function loadTemplates() {
    try {
        const res = await fetch('/api/load_templates', { method: 'GET' });
        const data = await res.json();
        if (data.status === 'success') {
            const templatesList = document.getElementById('templatesList');
            if (data.data && data.data.length > 0) {
                templatesList.innerHTML = '';
                data.data.forEach(template => {
                    const templateItem = document.createElement('div');
                    templateItem.className = 'template-item';
                    templateItem.innerHTML = `
                        <div>
                            <div style="font-weight:600;color:#dce6f0;">${template.name}</div>
                            <div style="font-size:11px;color:#5a7a94;">${template.tech} · ${template.created_at}</div>
                        </div>
                        <div style="display:flex;gap:4px;">
                            <button class="btn btn-sm btn-outline-primary" onclick="applyTemplate('${template.name}', '${template.tech}', ${JSON.stringify(template.params).replace(/'/g, "&apos;")})">使用</button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteTemplate('${template.name}')">删除</button>
                        </div>
                    `;
                    templatesList.appendChild(templateItem);
                });
            } else {
                templatesList.innerHTML = '<p style="color:#5a7a94;text-align:center;">暂无模板</p>';
            }
        } else {
            alert('加载模板失败: ' + data.msg);
        }
    } catch (e) {
        console.error('加载模板失败:', e);
        alert('加载模板失败，请检查网络连接');
    }
}

function applyTemplate(name, tech, params) {
    document.getElementById('techSelect').value = tech;
    changeTech();
    const tryApply = (attempt) => {
        if (attempt > 10) return;
        let allFound = true;
        for (let key in params) {
            if (!document.getElementById(`p_${key}`)) {
                allFound = false;
                break;
            }
        }
        if (!allFound) {
            setTimeout(() => tryApply(attempt + 1), 50);
            return;
        }
        for (let key in params) {
            const element = document.getElementById(`p_${key}`);
            if (element) {
                if (element.tagName === 'SELECT' && element.multiple) {
                    const values = params[key].split(',');
                    for (let i = 0; i < element.options.length; i++) {
                        element.options[i].selected = values.includes(element.options[i].value);
                    }
                } else if (element.tagName === 'SELECT') {
                    element.value = params[key];
                    element.dispatchEvent(new Event('change'));
                } else {
                    element.value = params[key];
                }
            }
        }
        alert(`已应用模板: ${name}`);
        addHistory('应用模板', { template_name: name, tech: tech });
    };
    setTimeout(() => tryApply(0), 50);
}

async function deleteTemplate(name) {
    if (!confirm(`确定要删除模板 "${name}" 吗？`)) return;
    try {
        const res = await fetch('/api/delete_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert('模板删除成功');
            loadTemplates();
            addHistory('删除模板', { template_name: name });
        } else {
            alert('删除失败: ' + data.msg);
        }
    } catch (e) {
        console.error('删除模板失败:', e);
        alert('删除模板失败，请检查网络连接');
    }
}

async function addHistory(operation, details) {
    try {
        await fetch('/api/add_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ operation: operation, details: details })
        });
    } catch (error) {
        console.error('添加操作历史记录异常:', error);
    }
}

async function loadHistory() {
    try {
        const res = await fetch('/api/get_history', { method: 'GET' });
        const data = await res.json();
        const historyList = document.getElementById('historyList');
        if (data.status === 'success') {
            historyList.innerHTML = '';
            if (data.data && data.data.length > 0) {
                data.data.forEach(record => {
                    const historyItem = document.createElement('div');
                    historyItem.className = 'template-item';
                    let detailsHtml = '';
                    for (let [key, value] of Object.entries(record.details)) {
                        detailsHtml += `<span style="font-size:11px;color:#5a7a94;">${key}: ${value}</span> `;
                    }
                    historyItem.innerHTML = `
                        <div>
                            <div style="font-weight:600;color:#dce6f0;">${record.operation}</div>
                            <div style="font-size:11px;color:#5a7a94;">${record.timestamp}</div>
                            <div>${detailsHtml}</div>
                        </div>
                    `;
                    historyList.appendChild(historyItem);
                });
            } else {
                historyList.innerHTML = '<p style="color:#5a7a94;text-align:center;">暂无历史记录</p>';
            }
        } else {
            alert('加载历史记录失败: ' + data.msg);
        }
    } catch (e) {
        console.error('加载历史记录失败:', e);
        alert('加载历史记录失败，请检查网络连接');
    }
}

async function clearHistory() {
    if (!confirm('确定要清空所有操作历史记录吗？此操作不可恢复！')) return;
    try {
        const res = await fetch('/api/clear_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert('操作历史记录清空成功！');
            loadHistory();
        } else {
            alert('清空历史记录失败: ' + data.msg);
        }
    } catch (e) {
        console.error('清空历史记录失败:', e);
        alert('清空历史记录失败，请检查网络连接');
    }
}

const AI_PROVIDERS = {
    deepseek: { baseUrl: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
    openai: { baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
    qwen: { baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-turbo' },
    zhipu: { baseUrl: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash' },
    moonshot: { baseUrl: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k' },
    ollama: { baseUrl: 'http://localhost:11434/v1', model: 'qwen2.5:7b' },
    custom: { baseUrl: '', model: '' }
};

let aiChatHistory = [];
let aiIsSending = false;

function toggleAIPanel() {
    const panel = document.getElementById('aiPanel');
    const fab = document.getElementById('aiFab');
    panel.classList.toggle('hidden');
    if (panel.classList.contains('hidden')) {
        fab.classList.add('visible');
    } else {
        fab.classList.remove('visible');
    }
}

function toggleAIConfig() {
    const form = document.getElementById('aiConfigForm');
    const arrow = document.getElementById('aiConfigArrow');
    form.classList.toggle('collapsed');
    arrow.classList.toggle('collapsed');
}

function onAIProviderChange() {
    const provider = document.getElementById('aiProvider').value;
    const config = AI_PROVIDERS[provider];
    if (config) {
        document.getElementById('aiBaseUrl').value = config.baseUrl;
        document.getElementById('aiModel').value = config.model;
    }
}

function toggleAIKeyVisibility() {
    const input = document.getElementById('aiApiKey');
    const icon = document.getElementById('aiKeyEyeIcon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

function saveAIConfig() {
    const config = {
        provider: document.getElementById('aiProvider').value,
        baseUrl: document.getElementById('aiBaseUrl').value.trim(),
        apiKey: document.getElementById('aiApiKey').value.trim(),
        model: document.getElementById('aiModel').value.trim()
    };
    localStorage.setItem('ensp-ai-config', JSON.stringify(config));
    addAIChatMsg('system', '✅ AI模型配置已保存');
}

function loadAIConfig() {
    const saved = localStorage.getItem('ensp-ai-config');
    if (saved) {
        try {
            const config = JSON.parse(saved);
            document.getElementById('aiProvider').value = config.provider || 'deepseek';
            document.getElementById('aiBaseUrl').value = config.baseUrl || '';
            document.getElementById('aiApiKey').value = config.apiKey || '';
            document.getElementById('aiModel').value = config.model || '';
        } catch (e) {}
    }
}

function getAIConfig() {
    const saved = localStorage.getItem('ensp-ai-config');
    if (saved) {
        try { return JSON.parse(saved); } catch (e) {}
    }
    return { provider: '', baseUrl: '', apiKey: '', model: '' };
}

function addAIChatMsg(role, content) {
    const messagesDiv = document.getElementById('aiChatMessages');
    const welcomeEl = messagesDiv.querySelector('.ai-welcome');
    if (welcomeEl) welcomeEl.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `ai-msg ${role}`;

    if (role === 'assistant') {
        let displayContent = content;
        let configCommands = '';
        const codeBlockRegex = /```[\w]*\n?([\s\S]*?)```/g;
        let match;
        let hasCodeBlock = false;
        while ((match = codeBlockRegex.exec(content)) !== null) {
            hasCodeBlock = true;
            configCommands += match[1].trim() + '\n';
        }
        if (!hasCodeBlock) {
            const lines = content.split('\n');
            const cmdLines = lines.filter(l => {
                const trimmed = l.trim();
                return trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('//') &&
                       !trimmed.startsWith('*') && !trimmed.startsWith('-') &&
                       !trimmed.startsWith('1') && !trimmed.startsWith('2') &&
                       !trimmed.startsWith('规则') && !trimmed.startsWith('注意') &&
                       !trimmed.startsWith('说明') && !trimmed.startsWith('以上') &&
                       !trimmed.startsWith('以下') && !trimmed.startsWith('这是') &&
                       (trimmed.startsWith('system-view') || trimmed.startsWith('sysname') ||
                        trimmed.startsWith('interface') || trimmed.startsWith('vlan') ||
                        trimmed.startsWith('ip ') || trimmed.startsWith('ospf') ||
                        trimmed.startsWith('bgp') || trimmed.startsWith('acl') ||
                        trimmed.startsWith('quit') || trimmed.startsWith('return') ||
                        trimmed.startsWith('stp') || trimmed.startsWith('dhcp') ||
                        trimmed.startsWith(' port') || trimmed.startsWith(' ip ') ||
                        trimmed.startsWith(' undo') || trimmed.startsWith(' description') ||
                        trimmed.startsWith(' security') || trimmed.startsWith(' ssid') ||
                        trimmed.startsWith(' vap') || trimmed.startsWith(' capwap') ||
                        trimmed.startsWith(' wlan') || trimmed.startsWith(' regulatory') ||
                        trimmed.startsWith(' name') || trimmed.startsWith(' network') ||
                        trimmed.startsWith(' area') || trimmed.startsWith(' peer') ||
                        trimmed.startsWith(' rule') || trimmed.startsWith(' nat') ||
                        trimmed.startsWith(' vrrp') || trimmed.startsWith(' rip') ||
                        trimmed.startsWith(' isis') || trimmed.startsWith(' eth-trunk') ||
                        trimmed.startsWith(' mode') || trimmed.startsWith(' forward') ||
                        trimmed.startsWith(' service') || trimmed.startsWith(' active') ||
                        trimmed.startsWith(' region') || trimmed.startsWith(' instance') ||
                        trimmed.startsWith(' priority') || trimmed.startsWith(' preempt') ||
                        trimmed.startsWith(' authentication') || trimmed.startsWith(' gateway') ||
                        trimmed.startsWith(' dns') || trimmed.startsWith(' excluded') ||
                        trimmed.startsWith(' select') || trimmed.startsWith(' enable') ||
                        trimmed.startsWith(' summary') || trimmed.startsWith(' version') ||
                        trimmed.startsWith(' batch') || trimmed.startsWith(' default') ||
                        trimmed.startsWith(' allow-pass') || trimmed.startsWith(' hybrid') ||
                        trimmed.startsWith(' pvid') || trimmed.startsWith(' tagged') ||
                        trimmed.startsWith(' untagged') || trimmed.startsWith(' link-type') ||
                        trimmed.startsWith(' shutdown') || trimmed.startsWith(' address'));
            });
            if (cmdLines.length >= 2) {
                configCommands = cmdLines.join('\n');
            }
        }

        if (configCommands.trim()) {
            const escapedCmds = configCommands.trim().replace(/'/g, "\\'").replace(/\n/g, '\\n');
            msgDiv.innerHTML = formatAIContent(content);
            const actions = document.createElement('div');
            actions.className = 'ai-msg-actions';
            actions.innerHTML = `<button class="ai-msg-action-btn primary" onclick="applyAIConfig('${escapedCmds}')"><i class="fas fa-check"></i> 应用到编辑器</button><button class="ai-msg-action-btn" onclick="pushAIConfig('${escapedCmds}')"><i class="fas fa-paper-plane"></i> 写入设备</button>`;
            msgDiv.appendChild(actions);
        } else {
            msgDiv.innerHTML = formatAIContent(content);
        }
    } else if (role === 'system') {
        msgDiv.style.cssText = 'text-align:center;font-size:12px;color:var(--ai-text-dim);background:none;padding:4px;';
    } else {
        msgDiv.textContent = content;
    }

    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function formatAIContent(content) {
    let html = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    html = html.replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function addAITypingIndicator() {
    const messagesDiv = document.getElementById('aiChatMessages');
    const typing = document.createElement('div');
    typing.className = 'ai-msg assistant';
    typing.id = 'aiTypingIndicator';
    typing.innerHTML = '<div class="ai-typing"><span></span><span></span><span></span></div>';
    messagesDiv.appendChild(typing);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function removeAITypingIndicator() {
    const el = document.getElementById('aiTypingIndicator');
    if (el) el.remove();
}

async function sendAIMessage() {
    if (aiIsSending) return;
    const input = document.getElementById('aiChatInput');
    const prompt = input.value.trim();
    if (!prompt) return;

    const config = getAIConfig();
    if (!config.baseUrl || !config.model) {
        addAIChatMsg('system', '⚠️ 请先配置AI模型（点击上方"模型配置"）');
        toggleAIConfig();
        if (document.getElementById('aiConfigForm').classList.contains('collapsed')) {
            toggleAIConfig();
        }
        return;
    }

    aiIsSending = true;
    document.getElementById('aiSendBtn').disabled = true;
    input.value = '';

    addAIChatMsg('user', prompt);
    aiChatHistory.push({ role: 'user', content: prompt });

    addAITypingIndicator();

    try {
        const res = await fetch('/api/ai_generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                base_url: config.baseUrl,
                api_key: config.apiKey,
                model: config.model,
                messages: aiChatHistory.slice(-10)
            })
        });
        const data = await res.json();
        removeAITypingIndicator();

        if (data.status === 'success') {
            addAIChatMsg('assistant', data.config);
            aiChatHistory.push({ role: 'assistant', content: data.config });
        } else {
            addAIChatMsg('system', '❌ ' + data.msg);
        }
    } catch (e) {
        removeAITypingIndicator();
        addAIChatMsg('system', '❌ 请求失败，请检查后端服务');
    }

    aiIsSending = false;
    document.getElementById('aiSendBtn').disabled = false;
}

function applyAIConfig(commands) {
    const decoded = commands.replace(/\\n/g, '\n').replace(/\\'/g, "'");
    document.getElementById('configTextarea').value = decoded;
    switchPanel('editor');
    addAIChatMsg('system', '✅ 配置已应用到编辑器');
}

function pushAIConfig(commands) {
    const decoded = commands.replace(/\\n/g, '\n').replace(/\\'/g, "'");
    const port = currentDevicePort;
    if (!port) {
        addAIChatMsg('system', '⚠️ 请先选择目标设备');
        return;
    }
    document.getElementById('configTextarea').value = decoded;
    pushCustomConfig();
    addAIChatMsg('system', '📤 正在将AI配置写入设备...');
}

window.onload = () => { initTheme(); changeTech(); loadAIConfig(); document.getElementById('aiChatInput').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAIMessage(); } }); };
