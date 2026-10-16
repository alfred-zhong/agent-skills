---
name: export-html
description: |
  将 markdown 或纯文本文件导出为精美的自包含 HTML 页面。使用 html-anything 项目的模板系统。
  触发词：导出 HTML、export html、markdown 转 HTML、文本转 HTML、txt 转 HTML、生成 HTML、渲染 HTML、/export-html
  参数：
    --template, -t <id>   指定模板 ID（如 article-magazine、deck-pitch）
    --output, -o <path>   指定输出路径（默认与输入同名的 .html）
    --list-templates      列出所有可用模板
---

# export-html 技能

将 markdown 或纯文本文件通过 AI 生成为精美的、自包含的单文件 HTML。模板来源于 `html-anything` 项目（`/Users/alfred/Repo/html-anything/next/src/lib/templates/skills/`）。

## 流程

### 1. 解析参数

从用户输入中提取：
- **输入文件路径**（必需）：markdown 或纯文本文件路径（支持 `.md`、`.txt`、`.log` 等）
- **模板 ID** (`--template` / `-t`)：可选
- **输出路径** (`--output` / `-o`)：可选，默认与输入同目录同名的 `.html` 文件
- **列出模板** (`--list-templates`)：列出可用模板后结束

### 2. 选择模板

**如果用户已通过 `--template` / `-t` 明确指定了模板 ID**，直接使用该模板，跳过此步骤。

**如果用户没有指定模板**，执行以下步骤：

---

#### 第一步：分析文档内容

读取用户指定的输入文件，快速分析其内容类型和风格：
- **类型**：文章/博客、技术文档、数据报告、产品说明、会议纪要、演示文稿...
- **风格**：正式/轻松、图文并茂/文字为主、数据密集/观点驱动...
- **篇幅**：短（<500字）、中（500-2000字）、长（>2000字）

#### 第二步：展示推荐组 + 内容推荐

读取 `templates.md`，展示两个表格：

**⭐ 推荐组**（项目 `recommended` 字段定义的 13 个模板，完整展示：编号、模板 ID、名称、简介四列）

**🎯 为你推荐** — 根据文档内容从全部模板中挑选 3-5 个最匹配的，标注 `R1`-`R5` 编号，简要说明推荐理由：

| 编号 | 模板 ID | 名称 | 推荐理由 |
|------|---------|------|----------|
| R1 | `xxx` | 📖 名称 | 适合你的xxx内容，因为... |
| ... | ... | ... | ... |

两个表格展示完毕后，附上提示：

> 直接回复编号即可。推荐组用 F1-F13，内容推荐用 R1-R5。都不满意？回复「更多」查看全部 81 个模板。

#### 第三步：用户选择

用户可能回复：
- 推荐组编号（`F1`-`F13`）
- 内容推荐编号（`R1`-`R5`）
- 模板 ID 字符串（如 `deck-pitch`）
- 「更多」/「全部」→ 进入第四步

收到有效选择后解析出模板 ID，继续后续流程。

#### 第四步：展示完整列表（仅在用户要求时）

如果用户回复「更多」或表示不够，则展示 `templates.md` 中除推荐组外的全部分类表格（含编号、模板 ID、名称、简介）。**不要分页、不要用 AskUserQuestion。** 展示后让用户回复编号或模板 ID。

### 3. 列出模板（如果用户要求）

直接读取并展示 `templates.md` 的内容，该文件包含全部模板的分类表格。

### 4. 读取模板

读取 `/Users/alfred/Repo/html-anything/next/src/lib/templates/skills/<template-id>/SKILL.md`，提取：
- frontmatter 中的元数据（`zh_name` / `en_name` / `emoji` / `description` / `category` / `scenario` / `aspect_hint` / `featured` / `recommended` / `tags`，以及可选的 `example_*`）
- `---` 之后的正文（模板设计指令）

### 5. 读取用户内容

读取用户指定的文件内容。支持以下格式：
- **Markdown 文件**（`.md`）：按标准 markdown 语法解析，保留标题层级、列表、代码块、表格等结构。
- **纯文本文件**（`.txt`、`.log` 等）：直接读取全文，保留原始换行和缩进。在生成 HTML 时，根据内容语义自动推断结构（例如：连续空行分隔段落、以数字/破折号开头的行识别为列表、缩进块识别为代码等）。

读取后，将内容传递给生成步骤。对于纯文本文件，需在 prompt 中注明"这是一个纯文本文件，请根据内容语义推断结构"。

### 6. 生成 HTML

按照以下完整指令生成 HTML。指令要点与 html-anything 项目 `next/src/lib/templates/shared.ts` 的 `SHARED_DESIGN_DIRECTIVES` 对齐，另额外补充了「暗色模式」一条。唯一有意保留的实质差异是**落盘方式**：本技能用 Write 工具直接写文件，而 Web 端由前端捕获 stdout，因此那边明确要求"禁止使用文件系统工具"。

---

## 生成指令

你是世界级的视觉设计师 + 资深前端工程师。请输出一份**自包含的单文件 HTML**，要求：

【内容驱动数量 — 最高优先级，覆盖模板里的任何数字】
- 模板只定义"可用版面 / 风格 / 配色 / 字体 / 组件库"，**不定义** slide / 帧 / 卡片 / section 的数量。
- 输出的 slide / frame / card / section 数量**完全由用户内容的实际长度和信息结构决定**。必须**完整覆盖**用户内容的每一个要点、章节、数据组，**不许总结、压缩、丢弃信息**。
- 如果模板正文里写了类似"挑 6-10 张组成 deck / 输出 6-10 帧 / 3-6 张卡片"的数字，**一律视为短示例下的参考下限，不是上限**。短内容可以低于该范围，长内容应远超该范围 —— 用户给了 12k 字符的内容，输出 4-6 张是**严重错误**。
- 模板里写的"N 个锁死版面 / N 个磁带式版面 / N 个 layout"指的是**可复用的版式池**，同一个版式允许在不同内容上多次出现（例如 KPI Tower 可以连续用 3 次承载不同章节的数据），不是页数上限。
- 推荐做法：先把用户内容按语义切成若干段（章节标题 / 论点 / 数据组 / 列表项 / 步骤），每一段 → 至少一个独立的 slide / section / card，然后再从模板的版式池里给每一段挑最合适的版面。宁可多页也不要把多个独立要点硬塞进一页。

【硬性技术要求】
- 文档以 `<!DOCTYPE html>` 开头，末尾以 `</html>` 结束。
- 在 `<head>` 中通过 CDN 引入 Tailwind v3 Play（`https://cdn.tailwindcss.com`）与所需的 Google Fonts。
- 不要引用任何外部图片 URL（除非你能保证 URL 长期有效；优先使用 CSS / SVG 内联绘制）。
- 必要的脚本（图表、动画）通过 jsdelivr CDN 引入；保持单文件可双击打开即用。
- 用 Write 工具写入磁盘，文件内容必须是**纯 HTML**：不要用 markdown 代码围栏包裹，不要任何解释性文字，第一个字符必须是 `<`。

【设计准则 — 世界级标准】
- 排版：中文优先 `Noto Sans SC` / `Noto Serif SC`，英文 `Inter` / `Manrope` / `SF Pro` 风格。
- 色彩：使用 1 个主色 + 2 个中性色 + 至多 1 个强调色；大胆留白；不使用纯黑纯白（#000/#fff），改用 `#0a0a0a` / `#fafafa`。
- 网格：8 px 基线；段落最大宽度 65 ch；标题与正文有清晰的层级。
- 微观细节：圆角统一（rounded-xl/2xl），投影柔和（shadow-sm/lg），边框 1px `#e5e7eb` / `#262626`。
- 动效：仅在必要处使用 `transition-all` 或入场 fade-in；不要喧宾夺主。
- 无障碍：颜色对比度 ≥ 4.5；重要交互有 focus 态。
- 暗色模式：优先支持系统暗色模式（prefers-color-scheme），或提供切换按钮。

【内容真实性】
- **必须使用用户提供的真实数据**，不要编造、不要 lorem ipsum、不要 "Your text here"。
- 如果用户数据是结构化数据（CSV/JSON），请提取关键洞察并以图表/表格呈现。
- 中文与英文混排时，中英文之间留半角空格（盘古之白）。

【模板专用指令】
（此处插入模板 SKILL.md 的 body 内容）

---

### 7. 保存输出

将生成的 HTML 写入输出路径。完成后告知用户文件路径和大小。

## 使用示例

```
/export-html ~/blog/my-article.md
/export-html ~/blog/my-article.md --template deck-pitch
/export-html ~/blog/my-article.md -t article-magazine -o ~/output/custom.html
/export-html ~/notes/log.txt -t blog-post
/export-html --list-templates
```

## 注意事项

- 模板目录路径：`/Users/alfred/Repo/html-anything/next/src/lib/templates/skills/`
- 如果用户没有指定模板，以 Markdown 表格展示全部模板，让用户直接回复模板 ID 选择
- 输入文件支持 markdown（`.md`）和纯文本（`.txt`、`.log` 等），纯文本文件会自动推断结构
- 生成的 HTML 是自包含的（通过 CDN 引入 Tailwind 和字体），可双击直接在浏览器打开
- 本技能的模板清单（`templates.md`）是 html-anything 模板注册表的快照。项目更新后核对两处：该目录下的模板文件夹数（当前 81）、以及带 `recommended:` 字段的模板集合（当前 13 个）；两者任一变化就同步 `templates.md` 与本文档中的数量表述。项目自带的 CLI（`html-anything convert|auto`，需先 `pnpm -F @html-anything/cli build`）也能做同类转换，但会另起一个 AI agent 子进程，本技能不依赖它。
