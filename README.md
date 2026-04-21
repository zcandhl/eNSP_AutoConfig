<div align="center">

# eNSP AutoConfig

**华为 eNSP 网络设备自动化配置助手**

[![Version](https://img.shields.io/badge/version-1.2-blue.svg)](https://github.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用指南](#-使用指南) • [技术架构](#-技术架构) • [AI 集成](#-ai-集成)

</div>

---

## 📝 项目简介

eNSP AutoConfig 是一款面向华为 eNSP 模拟器的网络设备自动化配置工具。通过 Web 可视化界面，用户可以快速完成 VLAN、OSPF、BGP、ACL、NAT、VRRP、WLAN 等 **15 种**网络技术的配置下发，无需手动逐条输入命令。同时集成 AI 大模型助手，支持自然语言描述需求自动生成设备配置命令。

> **为什么做这个项目？** 在网络工程学习和实验中，使用华为 eNSP 模拟器配置设备需要逐条输入命令，效率低且容易出错。本项目旨在通过可视化界面 + 自动化脚本 + AI 辅助，大幅提升网络配置效率。

## ✨ 功能特性

### 🔌 核心能力

- **拓扑自动识别** — 导入 eNSP `.topo` 文件，自动解析设备信息与 Console 端口映射
- **设备智能分类** — 自动识别交换机/路由器/防火墙/无线控制器，动态过滤可用配置类型
- **可视化配置** — 15 种网络技术一键配置，表单化参数输入，自动生成华为 VRP 命令
- **批量配置推送** — Socket 连接设备 Console 端口，批量下发配置命令，自动处理分页和视图切换
- **配置读取与编辑** — 读取 `display current-configuration`，支持在线编辑和增量推送
- **接口自动发现** — 自动获取设备接口列表（物理/虚拟），智能填充接口选择器

### 📡 支持的配置类型

| 技术 | 说明 | 适用设备 |
|:-----|:-----|:---------|
| VLAN | 创建 / 分配 / 批量，支持 Access/Trunk/Hybrid | 交换机 |
| 接口 IP | IP 地址配置，交换机自动 `undo portswitch` | 路由器 / 三层交换机 |
| 静态路由 | 目的网段 + 下一跳 / 出接口 | 路由器 / 三层交换机 |
| OSPF | 区域配置，支持 Stub / NSSA / 静默接口 | 路由器 / 三层交换机 |
| RIP | 基本 RIP 配置 | 路由器 / 三层交换机 |
| BGP | AS 号 / 邻居 / 网络宣告 | 路由器 |
| IS-IS | 网络实体名 / 接口启用 | 路由器 |
| STP | 模式选择，MSTP 支持域 / 实例配置 | 交换机 |
| Eth-Trunk | 链路聚合，支持 LACP | 交换机 / 路由器 |
| DHCP | 接口模式 / 全局地址池 | 交换机 / 路由器 |
| 虚拟接口 | Vlanif / Loopback | 三层交换机 / 路由器 |
| ACL | 标准 (2000-2999) / 扩展 (3000-3999) | 全部设备 |
| NAT | Easy IP / Outbound | 路由器 / 防火墙 |
| VRRP | 虚拟网关，支持抢占 / 认证 | 路由器 / 三层交换机 |
| WLAN | SSID / 安全策略 / VAP / AP 组 | AC 无线控制器 |

### 🤖 AI 智能助手

- **右侧独立面板** — 对话式交互，不干扰主操作区域
- **多模型支持** — DeepSeek / OpenAI / 通义千问 / 智谱 GLM / Moonshot / Ollama 本地
- **一键应用** — AI 生成的配置可一键应用到编辑器或直接写入设备
- **多轮对话** — 保留上下文，支持追问和修改
- **零配置本地运行** — 通过 Ollama 可完全离线使用

### 🎨 界面特性

- **4 种主题** — 深蓝（默认）/ 明亮 / 科技绿 / 暗紫
- **三栏布局** — 侧边栏 + 配置区 + AI 面板，类 IDE 设计
- **响应式** — 适配不同屏幕尺寸
- **配置模板** — 保存 / 加载常用配置模板
- **操作历史** — 记录所有配置操作

---

## 🚀 快速开始

### 环境要求

| 项目 | 要求 |
|:-----|:-----|
| 操作系统 | Windows 7+ |
| Python | 3.8+（源码运行时需要） |
| eNSP | V100R003C00 及以上 |
| 浏览器 | Chrome / Edge / Firefox |

### 方式一：直接运行 EXE（推荐）

> 无需安装 Python，开箱即用

1. 从 [Releases](https://github.com) 下载最新版 `eNSP_AutoConfig.exe`
2. 双击运行，等待服务启动
3. 浏览器自动打开 `http://127.0.0.1:5001`
4. 在 eNSP 中启动目标设备（设备图标变绿）
5. 导出拓扑文件并上传到页面

### 方式二：源码运行

```bash
# 克隆仓库
git clone https://github.com/xxx/eNSP_AutoConfig.git
cd eNSP_AutoConfig

# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

浏览器访问 http://127.0.0.1:5001

### 方式三：自行打包 EXE

```bash
pip install pyinstaller
python build.py
```

生成的 EXE 位于 `dist/` 目录。

---

## 📖 使用指南

### 基本流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1.启动 eNSP │───▶│  2.导出拓扑  │───▶│  3.上传拓扑  │───▶│  4.配置下发  │
│  启动设备    │    │  .topo 文件  │    │  选择设备    │    │  一键推送    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

1. **启动 eNSP** — 打开网络拓扑，启动所有设备（等待设备图标变绿）
2. **导出拓扑** — 在 eNSP 中导出拓扑文件（.topo）
3. **上传拓扑** — 在 Web 页面左侧上传拓扑文件，选择目标设备
4. **配置下发** — 选择配置类型 → 填写参数 → 读取接口 → 生成并推送配置

### 设备分类体系

程序自动根据设备型号进行分类，并动态过滤可用的配置类型：

| 类别 | 典型型号 | 可用技术 |
|:-----|:---------|:---------|
| 二层交换机 | S1700 / S2700 / S3700 | VLAN / STP / Eth-Trunk / DHCP / ACL |
| 三层交换机 | S5700 / S5720 / CE6800 / CE12800 | 二层全部 + 路由 / OSPF / VRRP |
| 路由器 | AR1220 / AR2220 / AR3260 / NE40E | 接口 IP / 路由 / OSPF / BGP / NAT / VRRP |
| 防火墙 | USG6000V / USG9500V | 接口 IP / 路由 / OSPF / ACL / NAT |
| 无线控制器 | AC6005 / AC6605 | VLAN / DHCP / WLAN |

### AI 配置生成

1. 点击右侧 AI 面板（或右下角浮动按钮）
2. 在"模型配置"中填写 API 信息（或选择预设提供商）
3. 在输入框描述配置需求，如：`配置VLAN10，将GE0/0/1设为Access口`
4. AI 生成配置后，点击"应用到编辑器"预览，或"写入设备"直接推送

---

## 🤖 AI 集成

### 支持的模型提供商

| 提供商 | Base URL | 默认模型 | 需要 API Key |
|:-------|:---------|:---------|:------------:|
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat | ✅ |
| OpenAI | `https://api.openai.com/v1` | gpt-4o-mini | ✅ |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-turbo | ✅ |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash | ✅ |
| Moonshot | `https://api.moonshot.cn/v1` | moonshot-v1-8k | ✅ |
| Ollama | `http://localhost:11434/v1` | qwen2.5:7b | ❌ |

### 本地模型（Ollama）

完全离线运行，无需 API Key：

```bash
# 安装 Ollama
# https://ollama.ai

# 拉取模型
ollama pull qwen2.5:7b

# 在 AI 面板选择 "Ollama (本地)" 即可使用
```

### API 接口说明

后端采用 OpenAI 兼容格式，用户只需填写 Base URL 到 `/v1` 为止，程序自动拼接 `/chat/completions`：

```
Base URL              +  /chat/completions  =  实际请求地址
https://api.xxx.com/v1   /chat/completions    https://api.xxx.com/v1/chat/completions
```

---

## 🏗️ 技术架构

### 技术栈

| 层级 | 技术 | 说明 |
|:-----|:-----|:-----|
| 前端 | HTML + CSS + Vanilla JS | 零框架依赖，轻量高效 |
| 后端 | Flask | Python Web 框架 |
| 通信 | Socket TCP | 连接 eNSP Console 端口 |
| AI | OpenAI 兼容 API | `urllib.request` 零额外依赖 |
| 打包 | PyInstaller | 生成 Windows 单文件 EXE |

### 项目结构

```
eNSP_AutoConfig/
├── app.py                # Flask 应用入口（API 路由 + Tkinter 启动器）
├── core_logic.py         # 核心业务逻辑（配置生成 / Socket 通信 / 设备分类）
├── build.py              # PyInstaller 打包脚本
├── requirements.txt      # Python 依赖
├── README.md             # 项目文档
├── templates/
│   └── index.html        # 主页面模板
├── static/
│   ├── css/
│   │   └── style.css     # 样式表（4 主题 CSS 变量驱动）
│   └── js/
│       └── script.js     # 前端交互逻辑
└── history/              # 操作历史存储
```

### Socket 通信可靠性

与 eNSP 设备的通信是本项目的核心难点，我们做了以下优化：

| 问题 | 解决方案 |
|:-----|:---------|
| 提示符匹配失败 | 正则 `[<\[][^\s\]>]+[>\]]` 支持所有华为提示符格式 |
| `---- More ----` 分页 | 自动检测并发送空格翻页 |
| 命令错位 | 批量发送模式（每 10 条一批），模拟粘贴配置 |
| 视图层级混乱 | `_ensure_user_view()` 自动检测并恢复到用户视图 |
| Console 口 `screen-length` 报错 | 先进入 `system-view` 再执行 |

---

## ⚠️ 注意事项

1. **设备必须已启动** — eNSP 中设备图标为绿色才可连接
2. **端口不冲突** — 确保 5001 端口未被占用
3. **Console 端口映射** — eNSP 通过本地端口映射到设备 Console，拓扑文件中包含映射信息
4. **交换机接口配 IP** — 物理接口需先执行 `undo portswitch` 切换为三层接口，程序自动处理
5. **WLAN 配置** — 仅适用于 AC 设备，AP 通过 AC 下发配置
6. **AI 配置审查** — AI 生成的配置建议先"应用到编辑器"预览，确认无误后再"写入设备"

---

## 🛠️ 开发

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 开发模式启动（带控制台日志）
python app.py
```

### 打包发布

```bash
pip install pyinstaller
python build.py
# 输出: dist/eNSP_AutoConfig.exe
```

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star**

</div>
#   e N S P _ A u t o C o n f i g  
 #   e N S P _ A u t o C o n f i g  
 