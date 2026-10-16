<p align="center">
  <img src="frontend/assets/logo-readme.png" alt="GIS WorkTable-CN" width="300">
</p>

# GIS WorkTable-CN

**本仓库为参加上海开源大赛的参赛项目仓库。**

> 参赛届次、赛道与奖项等信息：**待补充**（以赛事官方材料为准，本仓库不自行标注）。
项目定位：结合自然语言 AI Agent 与手动 GIS 工具的开源工作台，面向空间数据接入、分析、地图核验与成果导出；当前为**面向本机运行的 CN 演示项目**，默认按 CN 档启动并只监听 `127.0.0.1`。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](backend/requirements.txt)

## 这是什么

GIS WorkTable-CN 把「导入数据 → 空间分析 → 地图核验 → 成果导出」放在同一个浏览器界面里，并提供两条并行入口：一条是图形面板与斜杠命令，一条是自然语言 AI 助手——两者调用**同一套 GIS 工具与同一条图层产物通道**。

- **主要用户**：需要快速核验空间数据与结果的分析人员；做空间分析原型验证与课程作业的师生；希望在轻量浏览器环境中完成 GIS 流程的开发者。
- **解决的问题**：
  1. 国内数据源适配成本高：高德、天地图、DataV 等返回 GCJ-02 坐标与各自的数据结构，进入分析链路前需要坐标转换与字段归一，本项目在工具层统一处理。
  2. 一条分析链路要在多个软件之间搬运文件：本项目把常用环节沉淀为可被 AI 编排的工具，并把每次执行记入处理历史，可一键重跑。
  3. 专业桌面软件部署与授权成本高：浏览器打开即用，数据与密钥留在本机。

![工作台界面：左侧图层与工具面板，中央地图](docs/images/worktable.png)

> 截图为真实运行界面。本仓库暂无演示视频链接，故不提供视频。

## 一个可复现的案例：本地 GeoJSON 缓冲分析（不需要模型密钥）

| 阶段 | 内容 |
| --- | --- |
| **输入数据** | 一个小型面要素 GeoJSON（几百到几千个要素即可），经「数据 → 上传」导入；也可使用内置示例或自行绘制的面 |
| **操作过程** | ① 上传后图层自动上图并进入图层面板； ② 打开「工具 → 空间分析」选择缓冲区，指定图层、距离与单位后运行； ③ 在结果图层上打开属性表查看字段； ④ 需要时再让 AI 解读**已有图层**（此步才需要模型密钥） |
| **结果产物** | 新的结果图层（缓冲区面）+ 属性表；结果可导出为 GeoJSON / Shapefile；工程可保存为 `.giswork`，处理历史中可一键重跑 |
| **如何核对** | 图层面板核对结果图层的名称与要素数；属性表核对字段；`output/` 与 `cache/history/` 核对落盘文件是否存在 |

需要说明：**产物存在不等于分析结论正确**。缓冲距离、单位、坐标系与数据质量都会影响结果，请按实际数据设置并独立复核；本仓库不提供任何"结果保证"。

## 三个核心特点

1. **AI 与手动入口复用同一套 GIS 工具。** 图形面板、斜杠命令与自然语言助手走同一个工具注册表和同一条图层通道：手动做的结果可以继续交给 AI 处理，AI 产出的图层也能用手动工具继续核验。
2. **结果以图层与文件交付，并提供产物核对。** 每次工具执行（含手动直连）都会记录工具名、参数、产物与成败，可重跑；结果落到图层、属性表与 `output/` 文件，便于逐项核对，而不是只给一段文字结论。
3. **CN 数据访问配置与本地分析支持。** 数据请求经 `backend/services/network_policy.py` 逐跳检查（HTTPS + 域名白名单）；CN 档不注册境外在线数据工具；本地数据导入与手动分析链路不依赖境外服务，也不依赖模型密钥。

## 技术架构

浏览器端（原生 HTML/CSS/JS；Leaflet 2D 与 CesiumJS 3D 共享同一份图层状态）+ 本机 FastAPI 后端（REST 与 SSE 流式接口）+ LangGraph ReAct Agent（把需求编排成工具调用链）+ GIS 工具注册表 + 领域服务与本地 SQLite/文件存储。

模块划分、调用链与关键机制见 **[架构说明](docs/architecture.md)**；完整功能与工具清单见 **[功能说明](docs/features.md)**。

## 快速开始（Windows，已验证）

### 1. 环境要求

- Python 3.11 或更高版本
- 现代浏览器（Chrome / Edge）
- Node.js 仅桌面版需要，Web 版不需要

### 2. 安装依赖

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r backend\requirements.txt
```

依赖安装需要联网。目标机器无法联网时，需提前准备离线依赖（如已装好依赖的虚拟环境或本地 wheel）。

### 3. 启动与停止

```bat
start.bat     :: 选择端口 → 启动后端 → 打开浏览器（已固定 CN 档）
stop.bat      :: 停止本项目的后端服务
```

`start.bat` 通过 `backend.launcher` 选择端口（默认 `8010`，可用环境变量 `GIS_PORT` 指定）；若端口被其他项目占用会直接报错，不会自动切换端口，以保持浏览器本地存储地址稳定。等价的手动命令：

```bat
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

### 4. 配置模型密钥（仅 AI 功能需要）

在「设置 → AI 模型」中选择 DeepSeek 或智谱并填入**演示者自己的**密钥；也可使用本机运行的 OpenAI 兼容服务。密钥只保存在浏览器本地并随请求发往本机后端，提交包内不含任何私人密钥。CN 档下模型请求同样受目标地址白名单限制。

### 5. 各能力对密钥与网络的依赖

| 能力 | 是否需要模型密钥 | 是否需要网络 / 凭据 |
| --- | --- | --- |
| 本地文件导入、手动空间分析、属性表、工程保存与导出 | 不需要 | 不需要（分析在本机完成） |
| AI 助手（自然语言编排工具、解读已有图层） | 需要 | 需要能访问所配置的模型服务 |
| 高德 / 天地图底图，在线数据接入（POI、行政区边界、地铁线等） | 不需要 | 需要网络；部分服务需要密钥或受配额限制 |
| 境外在线数据（OSM 路网、境外天气与地震等） |  | CN 档不注册这些工具，见 [CN 数据请求排查](docs/cn-network-audit.md) |

## 验证方式

- **测试**：`python scripts/run_layered_tests.py --mode fast`（分层测试；另有 `integration` 与 `regression` / `all` 模式）。完整命令与分层含义见 [分层测试指南](docs/layered-testing-guide.md)。
  当前验证记录（截至 2026-10-16）：相关测试累计 **255 项通过、4 项境外样例测试因 CN 策略跳过——**这是"通过的用例数"，不是"全部测试数"。
- **提交包自检**：`python scripts/package_cn_demo.py` 生成演示源码包，包含 ZIP 校验、敏感目录排除、数据库完整性与解压后启动检查；细节见 [CN 演示版提交说明](docs/cn-demo-submission.md)。
- **界面自检**：上传示例数据 → 执行一次缓冲 → 结果出现在图层面板与 `output/` 目录，即为一次完整链路验证。

## 当前限制

- **本机演示定位**：未提供公网部署所需的账号认证与完整权限隔离，不建议将服务改为公网监听。
- **依赖现场条件**：底图、在线数据与模型服务受网络、配额与凭据影响，可能不可用。
- **白名单不是合规认证**：`network_policy.py` 中的域名白名单是产品配置，不代表服务的数据授权、测绘资质或个人数据处理合规；高德底图已接入显示坐标转换，数据源边界精度仍需独立核验。
- **入口级策略**：该策略作用于应用入口，不等同于操作系统网络隔离；需要全进程阻断的部署应另配出站网关或防火墙。
- **功能状态区分**：已实现的功能见 [功能说明](docs/features.md)，已验证范围见 [工具验证记录](docs/tool-validation.md)，计划中的内容见 [路线图](docs/ROADMAP.md)。

## 数据源与部署档位

| 档位 | 用途 | 行为 |
| --- | --- | --- |
| `cn`（默认） | 本机演示与日常使用 | 不注册境外在线数据工具；数据请求走国内白名单 |
| `competition` | 比赛 / 展示 | 在 `cn` 基础上进一步收紧（含路网下载等外部在线工具） |
| `intl` | 开放模式 | 启用完整数据源，需要更完整的网络条件 |

`start.bat` 已固定 `GISWTB_PROFILE=cn`。档位含义与加固细节见 [CN 数据请求排查](docs/cn-network-audit.md)。

## 许可证与第三方数据

本项目以 **MIT** 协议开源，见 [LICENSE](LICENSE)。第三方依赖与许可证索引见 [发布流程 · 第三方依赖与许可证](docs/release-guide.md)。

地图与数据版权归各数据提供方所有（高德、天地图、DataV 等），使用前请自行确认其授权范围与配额；服务目录中的条目不代表服务始终可用。

## 更多文档

| 文档 | 内容 |
| --- | --- |
| [架构说明](docs/architecture.md) | 模块划分与调用链 |
| [功能说明](docs/features.md) | 完整功能与工具清单 |
| [分析工具使用手册](docs/USER_GUIDE_ANALYSIS_TOOLS.md) | 分析工具面板参数与用法 |
| [分层测试指南](docs/layered-testing-guide.md) | 测试分层与完整命令 |
| [工具验证记录](docs/tool-validation.md) | 已验证 / 未验证范围 |
| [CN 演示版提交说明](docs/cn-demo-submission.md) | 启动、演示流程与打包 |
| [CN 数据请求排查](docs/cn-network-audit.md) | 数据访问加固与边界 |
| [项目介绍（作品材料）](docs/competition/project-introduction.md) | 背景、场景、创新点与规划 |
| [演示脚本](docs/competition/demo-script.md) · [截图清单](docs/competition/screenshots.md) | 演示与截图采集 |
| [路线图](docs/ROADMAP.md) | 规划中的工作 |
| [贡献指南](CONTRIBUTING.md) · [命名与描述规范](docs/repository-standards.md) · [更新日志](CHANGELOG.md) | 协作与变更记录 |

## 维护者与反馈

问题与建议请提交 [Issue](https://github.com/Wukeeeeee/GIS-WORKTABLE-CN/issues)，尽量附最小复现数据与运行环境。维护者为 [@Wukeeeeee](https://github.com/Wukeeeeee)（项目作者）。
