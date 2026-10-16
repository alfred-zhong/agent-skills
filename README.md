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

## 仓库约定

- 技能放在 `skills/<name>/`，这是 CLI 的标准发现路径（也支持 `skills/<category>/<name>/`）。**不要**放到仓库根目录，那样只能靠兜底的递归搜索。
- `SKILL.md` 的 frontmatter 写 `name` + `description`（模型可见，决定何时自动触发），description 里列触发分支和触发词。
- 能落成脚本的逻辑一律落成脚本放 `scripts/`，`SKILL.md` 只写步骤、判据和边界，参数细节交给 `--help`。
- 脚本只依赖标准库；需要额外依赖时在 SKILL.md 里写明。
