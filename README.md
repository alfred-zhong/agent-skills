# agent-skills

个人 agent skills 集合。每个子目录是一个独立 skill：`SKILL.md` 是入口，`scripts/` 放可执行脚本。

## 安装

用 [vercel-labs/skills](https://github.com/vercel-labs/skills) 的 CLI 安装：

```bash
npx skills add alfred-zhong/agent-skills --list                 # 先看仓库里有哪些
npx skills add alfred-zhong/agent-skills -g -a kimi-code-cli -y # 装到 ~/.agents/skills/
npx skills add alfred-zhong/agent-skills --skill route-cp -g    # 只装一个
```

`-g` 装到用户级（全局可用），不带则装到当前项目的 `.agents/skills/`。装完需要**新开一个会话**才会被加载。

更新 / 卸载：

```bash
npx skills update route-cp
npx skills remove route-cp
```

## 已有 skills

| Skill | 用途 |
|---|---|
| [`route-cp`](skills/route-cp/SKILL.md) | 给轨迹（KML / GPX）按地形标 CP 点并导出带 `<wpt>` 的 GPX |
| [`export-html`](skills/export-html/SKILL.md) | markdown / 纯文本 → 自包含单文件 HTML |
| [`officecli`](skills/officecli/SKILL.md) | 用 officecli CLI 读写 .docx / .xlsx / .pptx |
| [`orbstack-helper`](skills/orbstack-helper/SKILL.md) | OrbStack Linux 虚拟机（`orb` / `orbctl`）的创建与运维 |
| [`wolai-mcp-helper`](skills/wolai-mcp-helper/SKILL.md) | wolai MCP 工具的选型与工作流手册 |
| [`answer-me-with-html`](skills/answer-me-with-html/SKILL.md) | 把回答渲染成单页可视化 HTML（含架构图 / 流程图 / 视频），产物落在系统临时目录 |

> `export-html` / `officecli` / `orbstack-helper` / `wolai-mcp-helper` 于 2026-10-16 从内部技能仓整体迁入，内容保持原样未改写（含少量 `/Users/alfred/...` 绝对路径）。

> `answer-me-with-html` 于 2026-10-20 从上游 [QingYunA/answer-me-with-html](https://github.com/QingYunA/answer-me-with-html) v0.5.5（MIT）移植：CLI 原样 vendored 在 `scripts/vendor/am-cli.mjs`，`scripts/am.mjs` 只是启动器，把上游默认的 `~/.answer-me-with-html` 数据目录改到 `$TMPDIR/answer-me-with-html/<uid>/`，并关闭会自动指向上游的版本检查。要升级上游 CLI，替换 `scripts/vendor/am-cli.mjs` 并同步 `SKILL.md` / `references/` 即可；字体许可 `licenses/OFL-Bangers.txt` 随技能保留。

## 仓库约定

- 技能放在 `skills/<name>/`，这是 CLI 的标准发现路径（也支持 `skills/<category>/<name>/`）。**不要**放到仓库根目录，那样只能靠兜底的递归搜索。
- `SKILL.md` 的 frontmatter 写 `name` + `description`（模型可见，决定何时自动触发），description 里列触发分支和触发词。
- 能落成脚本的逻辑一律落成脚本放 `scripts/`，`SKILL.md` 只写步骤、判据和边界，参数细节交给 `--help`。
- 脚本只依赖标准库；需要额外依赖时在 SKILL.md 里写明。
