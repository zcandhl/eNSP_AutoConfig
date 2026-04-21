# GitHub 上传指南

## 准备工作

### 1. 在 GitHub 创建仓库
1. 登录 GitHub (https://github.com)
2. 点击右上角 **+** → **New repository**
3. 填写仓库信息：
   - **Repository name**: `eNSP_AutoConfig`
   - **Description**: 华为 eNSP 网络设备自动化配置助手
   - **Private/Public**: 选择 Public（公开）或 Private（私有）
   - **不要勾选** "Add a README file"（我们已有 README.md）
   - **不要勾选** "Add .gitignore"（我们已有 .gitignore）
4. 点击 **Create repository**

### 2. 本地初始化 Git（PowerShell）
```powershell
# 进入项目目录
cd f:\eNSP_AutoConfig

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交所有更改
git commit -m "Initial commit: eNSP AutoConfig v1.2"

# 重命名主分支为 main
git branch -M main

# 添加远程仓库（将 YOUR_USERNAME 替换为您的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/eNSP_AutoConfig.git

# 推送到 GitHub
git push -u origin main
```

### 3. 首次推送后
如果提示输入用户名和密码：
- **用户名**：您的 GitHub 用户名
- **密码**：使用 **Personal Access Token**（不是密码！）

生成 Token 方法：
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 **Generate new token**
3. 勾选 `repo` 权限
4. 复制生成的 Token（只显示一次！）

---

## 常用 Git 命令

```powershell
# 查看状态
git status

# 查看更改
git diff

# 添加文件
git add filename.py

# 提交
git commit -m "描述"

# 推送
git push

# 拉取
git pull
```
