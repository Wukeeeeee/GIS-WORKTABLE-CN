# 提交检查清单（submission-checklist.md）

> 目标赛事：**2026 上海开源软件应用创新大赛**（主办：开源中国）。
> 官方来源：https://www.oschina.net/os2026/ （2026-10-13 检索）。
> ⚠️ 截止时间官网不同位置出现过「10 月 11 日」与「10 月 16 日 24:00」两种表述，**以你的报名确认邮件为准**——这是第一优先待确认项。

## A. 官方必交材料（官网参赛指南原文归纳）

| 材料 | 要求（官方） | 状态 |
| --- | --- | --- |
| 代码仓库链接 | 包含完整可运行的代码 | ✅ https://github.com/Wukeeeeee/GIS-WORKTABLE-CN （待确认是否要求公开仓库与特定许可证——官方资格审核包含"开源协议与知识产权合规"核验） |
| 作品介绍文档 | 推荐 PDF；含项目背景、技术架构、应用场景、创新点 | 🟡 源文件已就绪：`docs/competition/project-introduction.md`（未发现官方模板与页数限制——**待确认**） |
| 作品演示视频链接 | 需展示核心功能与使用流程 | ❌ 未录制。脚本：`docs/competition/demo-script.md` |
| 提交方式 | 材料打包附件发送 oscc@oschina.cn | ⏳ 需本人操作 |

## B. 已完成且有证据

- [x] 五层分层测试全部通过：2026-10-13，`run_layered_tests.py --mode regression`，L1–L5 全 PASSED（单进程 18/18；环境 Windows 11 + Python 3.13，提交号见 git log）。
- [x] 全量 backend pytest：见 B 节末尾执行记录（待填入最终数字）。
- [x] 密钥泄露扫描：backend/ 与 frontend/js/ 无硬编码 sk-/AK/token；Key 走用户凭据管理（localStorage + 后端转发），有 test_credential_security.py 覆盖。
- [x] LICENSE 为 MIT，README 徽章一致。
- [x] 作品介绍文档源文件、演示脚本、截图清单已创建（docs/competition/）。
- [x] CN 仓 README 修正：clone 地址指向本仓、端口 8010、Issue 入口指向本仓（与代码一致）。

## C. 需要实际运行验证（录制/提交前）

- [ ] 干净环境安装复现：`git clone` → 建 venv → `pip install -r backend/requirements.txt` → 启动 8010（README 声明"手动安装命令尚未在全新环境验证"，若来不及至少在本机跑通一次并记录）。
- [ ] 离线启动演示：断网刷新页面，UI/3D 正常（demo-script 镜头 4）。
- [ ] AI 链路实测：配置模型服务后完整跑一次「边界 → 缓冲」自然语言任务。
- [ ] 地图合规目检：台湾省/藏南/南海区域在 2D+3D 下目检，对照自然资源部标准地图服务（bzdt.ch.mnr.gov.cn）。
- [ ] 演示档位冒烟：`GISWTB_PROFILE=competition` 启动，确认仅启用本地离线包与已缓存数据。

## D. 需要我本人补充/操作

- [ ] 确认报名确认邮件中的截止时间、材料格式细节（页数/大小/命名）、赛道（默认建议：**开源 AI 工具赛道**；若做百度地图"15 分钟生活圈"命题需另按命题任务书）。
- [ ] 按 screenshots.md 拍摄 10 张真实截图，插入 project-introduction.md「待补充截图」处。
- [ ] 按 demo-script.md 录制视频并上传，取公开链接。
- [ ] 将 project-introduction.md 导出为 PDF（建议 Typora/VS Code 插件 + Mermaid 渲染，或 pandoc；架构图用 mermaid-cli 渲染）。
- [ ] 推送 CN 仓最新提交（当前 main 领先 origin，含测试修复与参赛材料；**我没有也不会自动推送**）。
- [ ] 打包：仓库链接 + PDF + 视频链接 → 发送 oscc@oschina.cn（截止前）。
- [ ] 确认团队信息/负责人报名表已填写（个人参赛也需明确负责人）。

## E. 需要组委会确认（未在官网明确，不得臆断）

- [ ] 作品介绍 PDF 是否有官方模板、页数/文件大小上限。
- [ ] 演示视频时长上限与可接受的托管平台。
- [ ] CN 发行版仓库（fork 关系）参赛是否需额外说明与主仓关系；原创性声明格式。
- [ ] 截止时间的最终口径（10-11 vs 10-16 24:00）。

## F. 风险与说明

- Layer 5 E2E 测试在无模型服务环境会失败（需真实或 mock LLM 端点）；本次已改为 mock 驱动，离线可通过。
- `datav_boundary` 相关测试依赖 DataV 网络（或本地缓存），纯离线 CI 可能跳过/失败——提交前在本机跑通即可，文档已注明。
- 桌面 Electron 版为实验性，视频与文档中不作重点承诺。
