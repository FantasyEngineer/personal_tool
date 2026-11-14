# 系统工具箱（Toolbox）

<img src="assets/icon.png" width="96" alt="Toolbox icon">

[![build](https://github.com/FantasyEngineer/personal_tool/actions/workflows/build.yml/badge.svg)](https://github.com/FantasyEngineer/personal_tool/actions/workflows/build.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个用 PyQt5 写的跨平台桌面工具箱，把日常开发和系统运维里零散的小工具收进同一个窗口。单文件代码（`toolbox.py`），Windows / macOS 都能跑。

## 功能

### 系统与桌面

- **网络诊断**：Ping、路由追踪、DNS 查询、端口扫描、网络测速；目标地址跨页签同步
- **进程管理**：查看进程列表与端口占用，按名称过滤，结束进程
- **配置**：环境变量、进程内变量、Git 配置、软件镜像源、SSH 密钥、SSH 主机、显示开关（隐藏文件/扩展名）
- **截图贴图**：区域截图、标注、本地 OCR（旁窗查看、编辑与选中复制，保留截图）、剪贴板贴图、桌面置顶
- **取色器**：独立屏幕取色入口，全屏放大镜，HEX / RGB 复制
- **图片处理**：质量压缩、按比例调整尺寸（含一寸/二寸等证件照预设）、格式转换
- **防黑屏**：阻止系统休眠与屏幕关闭
- **文字雨**：Matrix 风格全屏动画

### 编码与安全

- **编解码**：Base64、URL、Unicode 转义
- **加解密**：
  - JWT：解析、校验签名（HS/RS/PS/ES 系列）、检查过期时间
  - AES：AES-256-GCM / AES-128-GCM / AES-256-CBC / AES-256-CTR，支持口令派生密钥
  - RSA：生成密钥对、OAEP 加密 / 解密、签名 / 验签
  - HMAC、口令哈希（PBKDF2-SHA256 / scrypt）、随机密钥生成
- **哈希计算**：MD5 / SHA1 / SHA256 / SHA512，支持文本和文件（可拖拽）

### 文本与数据

- **数据格式**：JSON / XML 格式化与校验、JSON ↔ YAML 转换
- **文本工具**：行排序/去重/统计重复（uniq -c）、命名风格转换、合并拆分与 SQL IN 列表，选区实时统计（字节数、缩进、不可见字符）；文本对比支持行内高亮、忽略空白/大小写、差异跳转、复制 unified diff
- **正则测试**：常用预设、实时匹配与高亮

### 时间与日程

- **日期时间**：时间戳 ↔ 日期互转（秒/毫秒/微秒/纳秒自动识别，ISO 8601、RFC 2822、HTTP Date、自定义格式）、时间间隔与工作日、时间加减、多时区对照（含夏令时）
- **Cron 表达式**：执行计划、书写规范
- **提醒事项**：定时提醒、每天/工作日/仅一次、稍后提醒

### 数值计算

- **数字转换**：进制转换、罗马数字、金额大写
- **单位转换**、**商余计算**、**房贷计算器**

### 开发辅助

- **开发速查**：Docker、Linux、SSH、Vim、Windows、Git 命令和 HTTP 状态码，统一搜索、分类筛选与点击复制
- **chmod 权限**：八进制与符号互转、权限位勾选
- **颜色**：HEX / RGB / HSL 互转
- **生成器**：二维码、条形码、UUID、随机数

旧工具名称仍可搜索，最近使用与自定义排序会自动迁移。记录区在「最近使用 / 搜索记录」间切换，首页最多展示 5 项，全部菜单可查看、移除或清空记录。最近使用保留 12 项，搜索记录保留 8 项；仅记录有匹配结果且已回车确认或打开工具的搜索词，不记录输入过程。底部状态栏显示 CPU、内存、本机 IP（点击复制），设置内提供快捷键、首页排序、缓存目录和更新入口。

## 下载

到 [Releases](https://github.com/FantasyEngineer/personal_tool/releases) 页面下载：

| 平台 | 文件 | 说明 |
| --- | --- | --- |
| Windows 10/11 x64 | `Toolbox-windows.exe` | 单文件，双击即用，无需安装 |
| macOS | `Toolbox-macos.zip` | 解压得到 `Toolbox.app`，拖进「应用程序」 |

首次运行提示的处理：

- **Windows**：未签名的 exe 可能被 SmartScreen 拦截，点「更多信息 → 仍要运行」。
- **macOS**：应用目前是 ad-hoc 签名，首次打开需在图标上右键 →「打开」。

## 从源码运行

需要 Python 3.9+（CI 使用 3.11）。

```bash
git clone https://github.com/FantasyEngineer/personal_tool.git
cd personal_tool

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python toolbox.py
```

## 自行打包

```bash
pip install pyinstaller
pyinstaller --noconfirm toolbox.spec
```

产物：

- Windows：`dist/Toolbox.exe`（单文件）
- macOS：`dist/Toolbox/Toolbox.app`

也可以直接运行 `./build_local.sh`，它会创建虚拟环境、安装依赖并打包当前平台。

## 发版

版本号以 git tag 为唯一来源，只需打标签推送，无需手动下载/上传安装包：

```bash
git tag v1.0.11 && git push origin v1.0.11
```

[`.github/workflows/build.yml`](.github/workflows/build.yml) 在 macOS 和 Windows 原生 runner 上分别构建：

- 推送到 `main`：只构建并上传构建产物（artifact），不发版
- 推送 `v*` 标签：把 tag 版本号注入应用 → 构建 → 发布 GitHub Release → 上传安装包到 Cloudflare R2 → 自动生成 `version.json` 并提交到 Gitee/GitHub 仓库 `main` 分支，应用随即能检测到更新
- 安装包按版本存放（`releases/<tag>/Toolbox-macos.zip`、`releases/<tag>/Toolbox-windows.zip`），历史版本的下载链接不会失效
- `version.json` 的 `changelog` 优先取附注 tag 的说明（`git tag -a`），否则自动汇总上一个 tag 到本次的提交记录
- Windows 发布物通过 [SignPath](https://signpath.org/) 签名（需在仓库 Secrets 中配置 `SIGNPATH_API_TOKEN`，Variables 中配置组织/项目/策略；未配置时自动跳过）

发版依赖以下仓库 Secrets：

| Secret | 说明 |
| --- | --- |
| `R2_ACCOUNT_ID` | Cloudflare 账户 ID |
| `R2_ACCESS_KEY_ID` | R2 API Token 的 Access Key ID |
| `R2_SECRET_ACCESS_KEY` | R2 API Token 的 Secret Access Key |
| `R2_BUCKET` | 存放安装包的桶名 |
| `R2_PUBLIC_BASE_URL` | 桶绑定的公开访问域名，如 `https://dl.example.com` |
| `GITEE_TOKEN` | Gitee 私人令牌（勾选 `projects` 权限），仅用于回写 `version.json` |

## 项目结构

```
toolbox.py            # 全部界面与逻辑
toolbox.spec          # PyInstaller 打包配置
assets/               # 图标与图标生成脚本
requirements.txt      # 运行依赖
build_local.sh        # 本地一键打包
.github/workflows/    # CI（构建、发布、签名）
```

## 技术栈

PyQt5 · qrcode · Pillow · PyYAML · cryptography · PyInstaller

## 许可证

[MIT](LICENSE)
