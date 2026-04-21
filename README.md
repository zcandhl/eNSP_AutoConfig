<div align="center">

# eNSP AutoConfig

**华为 eNSP 网络设备自动化配置助手**

[![Version](https://img.shields.io/badge/version-1.2-blue.svg)](https://github.com/zcandhl/eNSP_AutoConfig)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org)

</div>

---

## 项目简介

eNSP AutoConfig 是一款面向华为 eNSP 模拟器的网络设备自动化配置工具。通过 Web 可视化界面，用户可以快速完成 VLAN、OSPF、BGP、ACL、NAT、VRRP、WLAN 等 **15 种**网络技术的配置下发，无需手动逐条输入命令。同时集成 AI 大模型助手，支持自然语言描述需求自动生成设备配置命令。

---

## 功能特性

### 核心能力

- **拓扑自动识别** - 导入 eNSP `.topo` 文件，自动解析设备信息与 Console 端口映射
- **设备智能分类** - 自动识别交换机/路由器/防火墙/无线控制器，动态过滤可用配置类型
- **可视化配置** - 15 种网络技术一键配置，表单化参数输入，自动生成华为 VRP 命令
- **批量配置推送** - Socket 连接设备 Console 端口，批量下发配置命令，自动处理分页和视图切换
- **配置读取** - 读取 `display current-configuration`，支持查看完整运行配置
- **接口自动发现** - 自动获取设备接口列表（物理/虚拟），智能填充接口选择器

### 支持的配置类型

| 技术 | 说明 | 适用设备 |
|:-----|:-----|:---------|
| VLAN | 创建/分配/批量，支持 Access/Trunk/Hybrid | 交换机 |
| 接口 IP | IP 地址配置，交换机自动 `undo portswitch` | 路由器/三层交换机 |
| 静态路由 | 目的网段+下一跳/出接口 | 路由器/三层交换机 |
| OSPF | 区域配置，支持 Stub/NSSA/静默接口 | 路由器/三层交换机 |
| RIP | 基本 RIP 配置 | 路由器/三层交换机 |
| BGP | AS 号/邻居/网络宣告 | 路由器 |
| IS-IS | 网络实体名/接口启用 | 路由器 |
| STP | 模式选择，MSTP 支持域/实例配置 | 交换机 |
| Eth-Trunk | 链路聚合，支持 LACP | 交换机/路由器 |
| DHCP | 接口模式/全局地址池 | 交换机/路由器 |
| 虚拟接口 | Vlanif/Loopback | 三层交换机/路由器 |
| ACL | 标准(2000-2999)/扩展(3000-3999) | 全部设备 |
| NAT | Easy IP/Outbound | 路由器/防火墙 |
| VRRP | 虚拟网关，支持抢占/认证 | 路由器/三层交换机 |
| WLAN | SSID/安全策略/VAP/AP 组 | AC 无线控制器 |

### AI 智能助手

- **多模型支持** - DeepSeek / OpenAI / 通义千问 / 智谱 GLM / Moonshot / Ollama 本地
- **一键应用** - AI 生成的配置可一键应用到编辑器或直接写入设备
- **多轮对话** - 保留上下文，支持追问和修改
- **零配置本地运行** - 通过 Ollama 可完全离线使用

---

## 快速开始

### 环境要求

| 项目 | 要求 |
|:-----|:-----|
| 操作系统 | Windows 7+ |
| Python | 3.8+ |
| eNSP | V100R003C00 及以上 |
| 浏览器 | Chrome / Edge / Firefox |

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python app.py
```

浏览器自动打开 http://127.0.0.1:5001

### 使用流程

1. 启动 eNSP，打开网络拓扑，启动所有设备
2. 在 eNSP 中导出拓扑文件（.topo）
3. 在 Web 页面左侧上传拓扑文件，选择目标设备
4. 选择配置类型 → 填写参数 → 生成并推送配置

---

## 项目结构

```
eNSP_AutoConfig/
├── app.py                  # Flask 应用入口
├── core_logic.py           # 核心业务逻辑
├── device_info_reader.py   # 设备信息读取
├── ai_handler.py          # AI 功能处理
├── template_manager.py     # 模板管理
├── history_manager.py     # 历史记录管理
├── build.py               # PyInstaller 打包脚本
├── requirements.txt       # Python 依赖
├── templates/
│   └── index.html        # 主页面
└── static/
    ├── css/style.css     # 样式文件
    └── js/script.js     # 前端交互逻辑
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|:-----|:-----|:-----|
| 前端 | HTML + CSS + Vanilla JS | 零框架依赖，轻量高效 |
| 后端 | Flask | Python Web 框架 |
| 通信 | Socket TCP | 连接 eNSP Console 端口 |
| AI | OpenAI 兼容 API | 零额外依赖 |
| 打包 | PyInstaller | 生成 Windows 单文件 EXE |

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star**

</div>
