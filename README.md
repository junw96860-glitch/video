# 自动生成竖屏(9:16)视频脚本工作流

这个仓库包含一个 GitHub Actions 工作流，帮你自动生成结构化、可落地的"竖屏 9:16"视频脚本（Markdown），并以 Pull Request 形式提交到仓库。

功能
- 手动触发（workflow_dispatch）生成视频脚本
- 可配置主题、受众、时长、风格与画幅比例（默认 9:16）
- 使用大模型生成分场景/分镜脚本、时间码、画面指引、字幕安全区规范与发布元数据

准备工作
1. 在仓库 Settings > Secrets and variables > Actions 添加：
   - OPENAI_API_KEY（必填）
   - OPENAI_BASE_URL（选填，若使用 OpenAI 兼容的自建或代理）
   - OPENAI_ORG_ID（选填）
2. Python 依赖在 Actions 内自动安装，无需本地准备。

模型与服务要求
- 支持 Chat Completions（chat.completions）接口（SDK 使用 openai>=1.40.0）。
- 中文生成质量良好，上下文窗口≥8k tokens 为佳。
- 稳定可用、速率限制合理（Actions 运行中避免超时/429）。
- 可选 OpenAI 兼容服务，设置 OPENAI_BASE_URL 即可。
- 如需 Azure OpenAI，请联系维护者改用 AzureOpenAI 客户端并设置 api_version。

如何使用
1. 在 GitHub 的 Actions 页面选择 "Generate Video Script (9:16)"
2. 点击 "Run workflow"，填写参数：
   - topic（必填）
   - target_audience（选填）
   - duration_minutes（选填，默认 5）
   - style（选填）
   - aspect_ratio（默认 9:16）
   - references（可多行）
   - openai_model（默认 gpt-4o-mini）
   - dry_run（仅生成不提交）
3. 运行完成后（非 dry_run），会自动创建 PR，脚本位于 content/scripts/YYYY-MM-DD-<slug>.md。

竖屏规范要点
- 基准分辨率 1080x1920（9:16），字幕与 UI 安全区预留：左右≥90px、底部≥250px。
- 字幕不超过两行，关键词可加粗/上色；镜头每3-6秒有变化，增强节奏感。
- 提供 B-roll 可替代方向（关键词/素材网站/实拍或录屏），并标注纵向适配。

常见问题
- 报错 OPENAI_API_KEY not set：请先配置仓库 Secret。
- PR 创建失败：检查仓库分支保护策略，或暂时启用 dry_run 调试。
