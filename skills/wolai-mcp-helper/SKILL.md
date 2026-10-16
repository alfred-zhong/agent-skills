---
name: wolai-mcp-helper
description: |
  wolai MCP 工具使用手册。当用户提到以下场景时触发（即使只是隐约相关）：
  - 在 wolai 上创建/更新/修改/读取/删除文档、页面、章节（section）、块（block）
  - 调 wolai MCP 工具（list_pages / create_page / get_page_outline / get_section_content / rewrite_section / insert_under_heading / create_block / patch_block_content / update_block / delete_* 等共 27 个工具）
  - 把 Markdown 内容还原到 wolai（md → wolai）
  - 设置块属性（颜色、图标、代码语言、todo 状态、标题级别、块背景色）
  - 设置页面属性（标题、图标、题头图、字体、宽度、目录）
  - 选择 wolai MCP 工具层级（section 工具 vs 局部修补 vs 精细 block 构造）
  本技能基于 wolai 官方 MCP 功能手册整理：核心概念（section/outline）+ 4 级工具优先级（官方建议）+ 27 工具速查表（分 4 类）+ 4 个关键工作流（创建/修改/读取/删除）+ create_block 详解。
---

# wolai MCP Helper 技能 v2

让 AI agent 在调 wolai MCP 时**用对工具、做对流程、填对参数**。基于 wolai 官方 MCP 功能手册（2026-06-11 抓取版）整理。

## 核心能力

1. **工具选择** — 给定任务，定位到 27 个工具中的正确工具（按 §2 优先级决策）
2. **工具调用** — 给定工具，正确填必填 + 常用可选参数
3. **工作流编排** — 多步骤任务按 §4 关键工作流顺序调用
4. **错误处理** — 常见错误码 / 场景 / 修正建议（见 §6）

---

## 1. 核心概念

### 1.1 什么是 section（章节）

在 wolai MCP 工具的语境里，**section = 一个标题 + 它下面直到下一个同级标题之前的所有内容**。

```
# 第一章        ← section 1 的起点
  这是正文...
  - 列表项

## 1.1 背景     ← section 2 的起点
  背景内容...

# 第二章        ← section 3 的起点
  第二章正文...
```

**为什么要有 section 概念** — wolai MCP 的设计思路是**分层读写**，避免每次都加载整页内容。section 是这一分层模型的核心单元。

**section 工具集**（4 个，全部需要 `section_id`）：
- `get_section_content` — 按 section 读取详细内容
- `rewrite_section` — 重写某个 section（可改标题）
- `insert_under_heading` — 在 section 标题下插入内容
- `delete_section` — 删除整个 section（可保留标题）
- `move_section` — 移动 section 到别处

### 1.2 什么是 outline（页面结构索引）

`get_page_outline` 返回页面的**轻量级结构索引**，是 section 的"地图"。

- 一次调用拿到所有 section 的 `section_id` + heading 文字 + 深度 + 预览
- 比 `get_page_blocks` 全量 dump 省 token
- **做结构编辑前必须先调**（因为 section 工具都需要 `section_id`，而 `section_id` 只能从这里拿）

**返回值关键字段**：
- `outline[]` — section/heading 结构列表（空表示无标题）
- `stats.total_blocks` / `stats.total_sections` / `stats.max_depth`
- `meta.truncated` — 是否被截断（超 `max_sections`）

### 1.3 工具层级概念

wolai MCP 按"页面 → 章节 → 块"三层组织：

| 层级 | 工具类别 | 数据量 | 何时用 |
|------|---------|--------|--------|
| Page 层 | `create_page` / `update_page` / `delete_page` / `list_pages` / `search_pages` / `list_builtin_covers` | 最小 | 文档级 CRUD |
| Section 层 | `get_page_outline` / `get_section_content` / `locate_section` / `rewrite_section` / `insert_under_heading` / `delete_section` / `move_section` | 中等 | 章节级读写（**官方推荐优先用**） |
| Block 层 | `get_block` / `create_block` / `patch_block_content` / `update_block` / `replace_block` / `insert_blocks_relative` / `delete_block` / `get_page_blocks` | 完整 | 块级读写（局部精修或必须时） |
| Layout | `create_column_layout` | — | 分栏布局 |

---

## 2. 工具优先级（4 级，官方建议）

**这是本技能最关键的决策规则**。wolai 官方在 README 中明示：

| 优先级 | 类别 | 工具 | 何时用 |
|--------|------|------|--------|
| **1** | 章节级（首选） | `rewrite_section` / `insert_under_heading` / `delete_section` / `move_section` | **能用 section 工具就不用 block 工具**；适合章节级重写、补充、删除、调整顺序 |
| **2** | 局部修补 | `patch_block_content` / `update_block` | section 工具粒度过粗或只改属性时用 |
| **3** | 精细 block 构造（必要时） | `create_block` / `insert_blocks_relative` / `replace_block` / `delete_block` | 需要新建无对应 section 的内容（标题之后追加初始内容、块级微调） |
| **4** | 读取（先 outline 后 section） | `get_page_outline` → `get_section_content` | **先用 outline 拿结构，再按需 section 读局部**；避免一次 `get_page_blocks` 拉全页 |

**关键决策**：
- "修改某段内容" → 优先 `rewrite_section`（不用逐 block 改）
- "在某个标题下补一段" → 优先 `insert_under_heading`（不用 create_block 拼）
- "改一个块的颜色" → `update_block`（不用重写 section）
- "读一个文档" → `get_page_outline` 拿结构，再 `get_section_content` 读局部（不用 `get_page_blocks` 全 dump）

---

## 3. 工具速查表（27 工具分 4 类）

每行：name | 用途 | 必填参数 | 何时用

### 3.1 页面管理（7）

| 工具 | 用途 | 必填参数 | 何时用 |
|------|------|----------|--------|
| `list_pages` | 列出可见顶级页面 | — | 找页面 ID 起点；支持 `category` 筛 private/favorite；`limit` 限数量 |
| `get_page` | 获取页面元信息（标题、图标、设置、子块 ID） | `page_id` | 查页面设置/版本/子块列表；**不要**用 `include_blocks=true` 读内容（用 outline） |
| `create_page` | 在父节点下创建空页面 | `parent_id`, `title` | 创建文档起步；创建后**必须**用 create_block 加内容 |
| `update_page` | 更新页面标题/图标/题头图/设置 | `page_id` + 至少 1 个其他字段 | 重命名/换图标/换题头图/改字体宽度 |
| `delete_page` | 删除页面 | `page_id`；`forever` 永久删 | 文档级删除；`forever=true` 不可恢复 |
| `search_pages` | 按标题关键词搜索 | `query` | 找页面 ID（仅支持单字符串、不支持正则） |
| `list_builtin_covers` | 列出内置题头图分类 | — | 给 `update_page` 选 `builtin_cover_id` |

### 3.2 内容读取（5）

| 工具 | 用途 | 必填参数 | 何时用 |
|------|------|----------|--------|
| `get_page_outline` | 轻量结构索引 | `page_id` | **结构编辑前必调**；控制 `max_depth` / `max_sections` / `max_preview_length` |
| `get_section_content` | 按 section 读详细内容 | `page_id`, `section_id` | 编辑前先读；`include_nested_sections` 控嵌套；`max_blocks` 限量 |
| `locate_section` | 用自然语言定位 section | `page_id`, `query` | 处理"底部的总结""最前面的背景"等模糊指令；`max_matches` 限数量 |
| `get_page_blocks` | 底层全量块 | `page_id` | **仅在必须获取所有 block_id 列表时用**；token 大 |
| `get_block` | 单块精准读 | `block_id` | 验证某块内容；`include_children` 控是否带子块 |

### 3.3 内容编辑（10）

| 工具 | 用途 | 必填参数 | 何时用 |
|------|------|----------|--------|
| `create_block` | 在父块下创建 1+ 块 | `parent_id`, `blocks` | 初始创建内容；块类型见 §5 |
| `move_section` | 移动整个 section | `page_id`, `source_section_id`, `target_section_id` | 章节重排序；`placement` 控前后内/外；`preserve_heading` 控是否带标题 |
| `rewrite_section` | 重写某 section（可改标题） | `page_id`, `section_id`；`heading`/`blocks` 可选 | **章节级重写首选**；先 `get_section_content` 读再写 |
| `insert_under_heading` | 在 section 标题下插入内容 | `page_id`, `target_section_id`, `blocks` | **章节补充首选**；`placement` 控 prepend/append |
| `delete_section` | 删除整个 section | `page_id`, `section_id`；`preserve_heading` 控保留标题 | 章节级删除 |
| `insert_blocks_relative` | 相对某块前后插入 | `anchor_block_id`, `blocks` | section 工具粒度过粗时用；`placement` 控 before/after |
| `patch_block_content` | 修补单块内容（局部） | `block_id`, `patches` | 4 种 op：replace_all / replace_text / prepend_content / append_content；patches 按顺序执行 |
| `replace_block` | 整块替换（可改类型） | `block_id`, `replacement_blocks` | 段落→callout/quote/code/heading 转换；`preserve_children` 可保留子块 |
| `update_block` | 更新块属性 | `block_id` + 至少 1 个其他字段 | 改 `level` / `language` / `checked` / `task_status` / `progress` / `block_front_color` / `block_back_color` |
| `delete_block` | 删除单块 | `block_id`；`forever` 永久删 | 块级删除（孤立块/精细删除）；章节级删除用 `delete_section` |

### 3.4 创建分栏（1）

| 工具 | 用途 | 必填参数 | 何时用 |
|------|------|----------|--------|
| `create_column_layout` | 创建 2-5 栏布局 | `parent_id`, `columns` | 分栏对比/并列展示；返回 `row_id` 和 `column_ids` 用于后续写入内容 |

---

## 4. 关键工作流（4 个）

### 工作流 1：创建新文档

```
1. list_pages（或已知 parent_id）
2. create_page(parent_id, title)          → 拿到新页面 ID
3. update_page(page_id, icon/cover)      → 美化（可选）
4. get_page_outline(page_id)             → 拿到结构（通常此时 outline 为空，因为没有 heading）
5. create_block(parent_id=page_id, blocks=[...])  → 加初始内容（必须用 create_block，因为没有 section）
```

**关键点**：创建新页面后，**必须用 `create_block` 加内容**（不是 section 工具，因为还没有 section）。

**典型 blocks 数组**（给 create_block）：
```json
[
  {"type": "heading", "content": "项目介绍", "level": 2},
  {"type": "text", "content": "这是一个普通文本段落。"},
  {"type": "code", "content": "console.log('hi')", "language": "javascript", "code_setting": {"line_number": true}}
]
```

### 工作流 2：修改现有文档某段（**最常用**）

```
1. get_page_outline(page_id)            → 拿到所有 section_id 和 heading 列表
2. （可选）locate_section(page_id, "底部的总结")  → 模糊定位
3. （推荐）get_section_content(page_id, section_id)  → 读当前内容
4. 决策：
   - 整段重写 → rewrite_section(page_id, section_id, blocks=[...])
   - 在标题下补充 → insert_under_heading(page_id, section_id, blocks=[...])
   - 改某块属性 → update_block(block_id, level/color/...)
   - 改某块内容 → patch_block_content(block_id, patches=[...])
   - 整块换类型 → replace_block(block_id, replacement_blocks=[...])
5. （如改了层级）move_section 调整顺序
```

**关键点**：先 outline 拿结构，**不要**直接 `get_page_blocks` 全 dump。section 工具优先。

### 工作流 3：读取文档

```
1. get_page_outline(page_id)            → 轻量索引，token 省
2. 判断需要：
   - 知道整体结构 → 完事（outline 已够）
   - 读某段详细内容 → get_section_content(page_id, section_id)
   - 模糊位置（如"最后的总结"）→ locate_section(page_id, query)
   - 读特定块 → get_block(block_id)
   - 罕见：需要所有 block_id → get_page_blocks（**慎用**，token 大）
```

**关键点**：**`get_page_blocks` 是底层/高级工具**，AI 文档编辑时**优先用 outline + section_content**。

### 工作流 4：删除文档或某段

```
文档级：delete_page(page_id)            → 默认进回收站；forever=true 永久删
章节级：delete_section(page_id, section_id, preserve_heading=?)  → 整章 or 仅删内容
块级：delete_block(block_id)            → 单块删
```

**关键点**：**先 outline 定位**，再选对应层级工具。`forever=true` 不可恢复。

---

## 5. create_block 详解

`create_block` 是最常用的精细构造工具，单独成章。

### 5.1 支持的块类型（14 种）

| 类型 | 必填字段 | 常用可选 | 备注 |
|------|----------|----------|------|
| `text` | `type`, `content` | — | 普通文本 |
| `heading` | `type`, `content`, `level` | `toggle` | level: 1\|2\|3 |
| `quote` | `type`, `content` | — | 引用 |
| `callout` | `type`, `content` | `icon`, `marquee_mode` | 提示框 |
| `bull_list` | `type`, `content` | — | 无序列表 |
| `enum_list` | `type`, `content` | — | 有序列表 |
| `toggle_list` | `type`, `content` | — | 折叠列表 |
| `todo_list` | `type`, `content` | `checked` | 待办 |
| `todo_list_pro` | `type`, `content` | `task_status` | 高级待办，status: todo/doing/done/cancel |
| `block_equation` | `type`, `content` | — | 块级公式（LaTeX） |
| `code` | `type`, `content`, `language` | `code_setting` | 代码块 |
| `image` / `video` / `audio` / `file` | `type`, `link` | `caption` | 媒体；image/video/audio 用 `link` 传外部 URL |
| `embed` | `type`, `original_link` | `embed_link` | 三方嵌入 |
| `bookmark` | `type`, `link` | — | 书签 |
| `divider` | `type` | — | 分割线 |
| `progress_bar` | `type`, `progress` | `auto_mode`, `hide_number` | 进度条（0-100） |
| `simple_table` | `type`, `table_content` | `table_setting`, `caption` | 表格 |
| `page` | `type` | `content`, `icon` | 页面引用 |

### 5.2 content 字段格式（3 种形态 + 特殊元素）

**形态 1 — 纯字符串**：
```json
{"type": "text", "content": "普通段落"}
```

**形态 2 — 单富文本对象**：
```json
{"type": "text", "content": {"title": "粗体文字", "bold": true}}
```

**形态 3 — 富文本数组**（RichText 与 string 混排）：
```json
{"type": "text", "content": [
  {"title": "粗体", "bold": true},
  " + 普通文字 ",
  {"title": "代码", "inline_code": true}
]}
```

**富文本元素完整字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 文本内容 |
| `bold` | boolean | 粗体 |
| `italic` | boolean | 斜体 |
| `underline` | boolean | 下划线 |
| `strikethrough` | boolean | 删除线 |
| `inline_code` | boolean | 行内代码 |
| `link` | string | 链接 URL |
| `front_color` | string | 文字颜色（见 §5.3 颜色枚举） |
| `back_color` | string | 背景颜色（见 §5.3 颜色枚举） |

**特殊元素**：
- 行内公式：`{"type": "equation", "title": "x^2 + y^2 = 1"}`
- 行内引用：`{"type": "bi_link", "title": "引用标题", "block_id": "块ID"}`

### 5.3 颜色枚举（来自 update_block 文档）

**block_front_color（文字颜色，12 种）**：
`default`, `gray`, `dark_gray`, `brown`, `orange`, `yellow`, `green`, `blue`, `indigo`, `purple`, `pink`, `red`

**block_back_color（背景颜色，12 种）**：
`default_background`, `cultured_background`, `light_gray_background`, `apricot_background`, `vivid_tangerine_background`, `blond_background`, `aero_blue_background`, `uranian_blue_background`, `lavender_blue_background`, `pale_purple_background`, `pink_lavender_background`, `light_pink_background`

### 5.4 code_setting 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `line_number` | boolean | 显示行号 |
| `line_break` | boolean | 自动换行 |
| `ligatures` | boolean | 连字 |
| `preview_format` | "both"/"code"/"mermaid" | 预览格式（仅 language=mermaid 或 ybsz 有效） |

**language 常用值**：python, typescript, javascript, js, jsx, tsx, java, go, rust, c, cpp, csharp, bash, sql, json, yaml, markdown, html, css, mermaid

### 5.5 完整 JSON 示例（7 个）

**示例 1：创建文本和标题**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {"type": "heading", "content": "项目介绍", "level": 2},
    {"type": "text", "content": "这是一个普通文本段落。"}
  ]
}
```

**示例 2：创建代码块**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {
      "type": "code",
      "content": "function hello() {\n  console.log('Hello World');\n}",
      "language": "javascript",
      "code_setting": {"line_number": true}
    }
  ]
}
```

**示例 3：创建带样式的富文本**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {
      "type": "text",
      "content": [
        {"title": "普通文字 "},
        {"title": "粗体文字", "bold": true},
        {"title": " "},
        {"title": "链接文字", "link": "https://example.com", "front_color": "blue"}
      ]
    }
  ]
}
```

**示例 4：创建待办列表**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {"type": "todo_list", "content": "完成需求分析", "checked": false},
    {"type": "todo_list_pro", "content": "编写代码", "task_status": "doing"}
  ]
}
```

**示例 5：创建提示框**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {
      "type": "callout",
      "content": "这是一个重要提示信息",
      "icon": {"type": "emoji", "icon": "💡"}
    }
  ]
}
```

**示例 6：创建表格**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {
      "type": "simple_table",
      "table_content": [
        ["姓名", "年龄", "城市"],
        ["张三", "25", "北京"],
        ["李四", "30", "上海"]
      ],
      "table_setting": {"has_header": true, "column_widths": [100, 80, 120]},
      "caption": "用户信息表"
    }
  ]
}
```

**示例 7：创建图片（外部 URL）**
```json
{
  "parent_id": "页面ID",
  "blocks": [
    {
      "type": "image",
      "link": "https://images.unsplash.com/photo-xxx.jpg",
      "caption": "图片说明文字"
    }
  ]
}
```

### 5.6 注意事项

1. **每个块必须包含 `type` 字段**
2. **在线图片**：通过 `link` 参数传入外部图片 URL 可正常使用
3. **本地文件上传**：`create_upload_session` 返回阿里云内网地址，外部网络无法访问，此功能受限
4. **优先级**：对 AI 文档编辑场景，**优先考虑 `rewrite_section` / `insert_under_heading`**；需要精细构造时才用 `create_block`

---

## 6. 错误处理

| 错误场景 | 原因 | 修正 |
|----------|------|------|
| `page_id invalid` | 父 ID 不存在或属于其他 doc | 先用 `list_pages` / `search_pages` 重新确认 |
| `section_id invalid` | section ID 不是从 `get_page_outline` 来的 | 必须先 outline 拿 section_id |
| 页面无标题结构（`outline: []`） | 页面没有 heading | 这种页面只能用 block 工具（create_block / patch_block_content / update_block），不能用 section 工具 |
| `parent_id` 缺失 | 调用 `create_block` 没传 `parent_id` | parent_id 必填，可用页面 ID 或块 ID |
| `level` 越界 | heading level 不在 1-3 | heading level 只支持 1/2/3（v2 源材料确认） |
| `column_widths` 长度不匹配 | 表格列宽数组长度与列数不一致 | 确保 `column_widths.length === table_content[0].length` |
| `replace_text` 不匹配 | `old_text` 没在块内找到 | 文本必须精确匹配；考虑用 `get_block` 读后重试 |
| `patches` 顺序错 | 多个 patch 写了同一文本 | 多个 patch 按顺序执行，前一个影响后一个；顺序要规划好 |
| `include_blocks=true` 性能差 | 拉了整页 block | **不要**用 `include_blocks=true` 读内容；改用 outline + section_content |
| `delete_page` 误删 | 删错页面 | 默认 `forever=false` 进回收站可恢复；`forever=true` 不可逆 |
| 本地文件上传失败 | `create_upload_session` 返回内网地址 | 外部网络无法访问；改用外部 URL `link` 参数 |

---

## 7. v1 → v2 变更说明 + 维护

### 7.1 v1 vs v2 关键差异

| 维度 | v1（已废弃） | v2（当前） |
|------|-------------|-----------|
| **源材料** | `/tmp/wolai_scrape/`（块类型数据模型） | `/tmp/wolai-mcp-handbook/`（MCP 工具手册） |
| **定位** | 块类型字典 | MCP 工具使用手册 |
| **核心概念** | Block + CreateRichText | Section + Outline + 工具优先级 |
| **章节数** | 9 | 7 |
| **块类型清单** | 19 可用 + 8 禁用（数据模型） | 14 种（按 create_block 文档） |
| **section/outline 概念** | 没提 | 核心章节 |
| **工具优先级** | 没提 | 4 级（官方建议） |
| **工作流示例** | md → wolai 1 个 | 4 个（创建/修改/读取/删除） |
| **v1 commit** | `c0ab579` 已废弃 | — |
| **v2 commit** | — | 见 git log |

### 7.2 v1 中已删除的内容

- §1 块类型速查表 19 可用 + 8 禁用 → 替换为官方 14 类型
- §2 关键枚举 11 个（颜色/对齐/heading 级别等）→ 颜色保留到 §5.3，对齐等删除（官方 create_block 文档未列）
- §3 CreateRichText 三种形态 → 替换为 §5.2 content 格式（含富文本）
- §4 MD → wolai 元素映射表 → 替换为 §4 关键工作流
- §5 陷阱清单 → 替换为 §6 错误处理
- §6 MCP 工具层级使用 → 替换为 §2 工具优先级 + §3 工具速查表

### 7.3 维护说明

- **源材料**：`/Users/alfred/tmp/wolai-mcp-handbook/`（wolai 官方 MCP 功能手册，2026-06-11 抓取版）
- **触发加载**：Claude Code / Codex 通过 `Skill` 工具按需加载
- **软链**：`~/.agents/skills/wolai-mcp-helper` 指向本目录
- **当 wolai 官方更新工具集时**：
  1. 重新抓取官方手册
  2. 对比本技能的 §2 工具优先级 + §3 速查表
  3. 跑端到端测试验证
  4. 重新 commit
- **端到端测试样本**：`/Users/alfred/fun/play-gstack/gstack-skills-analysis.md`（480 行，覆盖 headings/lists/tables/quotes/inline-code/divider/nested-lists 等典型模式）
