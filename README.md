# skills

个人 agent skills 集合。每个子目录是一个独立 skill，`SKILL.md` 是入口，`scripts/` 放可执行脚本。

## 安装 / 同步

Skill 由 Kimi Code 从 `~/.agents/skills/` 加载。本仓库是源，安装到本地：

```bash
./install.sh            # 全部同步
./install.sh route-cp   # 只同步一个
```

`install.sh` 用 `rsync --delete` 覆盖目标目录，仓库里改完再跑一次即可。装完需要**新开一个会话**才会被加载。

## 已有 skills

| Skill | 用途 |
|---|---|
| [`route-cp`](route-cp/SKILL.md) | 给轨迹（KML / GPX）按地形标 CP 点并导出带 `<wpt>` 的 GPX |

## 约定

- `SKILL.md` 的 frontmatter 写 `name` + `description`（模型可见，决定何时自动触发），description 里列触发分支和触发词。
- 能落成脚本的逻辑一律落成脚本放 `scripts/`，`SKILL.md` 只写步骤、判据和边界，参数细节交给 `--help`。
- 脚本只依赖标准库；需要额外依赖时在 SKILL.md 里写明。
