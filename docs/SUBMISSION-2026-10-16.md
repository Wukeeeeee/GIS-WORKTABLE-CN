# GIS-WORKTABLE-CN 提交说明（2026-10-16）

## 提交材料
- 源码包：`output/GIS-WORKTABLE-CN-demo-2026-10-16.zip`
- 启动：解压到可写目录，双击 `start.bat`；首次运行需联网安装依赖。
- 停止：双击 `stop.bat`。
- 操作指南：`docs/DELIVERY_REPLICATION_GUIDE.md`。
- 演示流程：`docs/competition/demo-script.md`。
- 复现数据：`data/sample_delivery_test.geojson`。

## 本次交付内容
Windows 自动安装与启动、运行时依赖检查、重复启动保护、失效虚拟环境备份与恢复、下载故障指引，以及本地数据导入、空间分析和导出链路。

提交前补充：启动锁等待超时后明确退出；旧环境备份失败时保留环境并退出；混合几何 Shapefile 导出明确提示拆分或改用 GeoJSON，避免静默丢失要素。

## 当前验证结果
本轮执行启动依赖测试、交付安全回归测试及五层测试，共 25 项通过。
`git diff --check` 用于检查改动空白格式；打包器执行源码密钥模式检查及服务目录过滤。
历史浏览器验收记录见 `docs/portability-check-2026-10-16.md`，本轮未重新执行浏览器验收或破坏性虚拟环境恢复测试。

## 已知边界
- 未在第二台物理电脑或干净虚拟机上验证安装。
- 未配置有效商业模型密钥，真实模型调用未验证；本地手动分析不依赖模型密钥。
- 不含离线依赖包；首次安装需要网络。
- 并发浏览器防抖仍为时间戳检查，不承诺严格并发下只打开一个标签。

## 建议 Git 提交信息
`fix: harden Windows bootstrap and prepare CN delivery package`

源码包不包含本机 `.venv`、`.bootstrap`、密钥、运行会话及 `output` 目录；校验清单位于压缩包旁。
