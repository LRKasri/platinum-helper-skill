# platinum-helper · 白金小助手生成器

[中文](#中文) · [English](#english)

---

## 中文

### 这是什么

能够生成html清单式跑图白金攻略的skill

**输入**：攻略网址；**输出**：html文件

支持两种语言：

- **中文版**：用游戏的官方中文名，右上角一键切换到英文原文；
- **英文版**：纯英文，不需要翻译，消耗的 token 大约只有中文版的三分之一。

### 生成的页面里有什么

- **路线**：按区域 → 步骤排列，一个勾选就是一个东西（物品、首领、存档点、NPC），标题只写名字，做法写在下面，附截图和视频链接。
- **不漏东西**：流程攻略没写的首领，按 PowerPyx 首领攻略的顺序插进路线；首领掉落的收集品紧跟在首领后面。
- **易错过**：只标 PowerPyx 原文写了会错过的内容，以及路线图里列出的易错过奖杯。
- **奖杯指南的步骤**：存档 / 读档时机、结局分支、不可回头点做成提示卡，放在路线里对应的位置；剧情奖杯出现在解锁的地方。多结局游戏的整套方案沿路线铺开，从上往下照着做就能拿全结局。
- **成就页**：每个奖杯的说明；收集类和「击败所有头目」类奖杯是清单，和路线上的勾选双向同步。
- **白金模式 / 全收集模式**：白金模式只统计拿白金需要的东西。
- **搜索、筛选（未完成 / 易错过 / 奖杯相关）、进度保存在浏览器里**，可以导出和导入。

### 需要什么

- Claude Code，或其他支持 Agent Skills 的工具（Codex、DeepSeek Harness等）。在 Claude Code 里会用并行子代理，最快（claude code自吹自擂环节）
- Python 3（只用标准库；装了 Pillow 会压缩截图）
- 能访问 powerpyx.com 的网络。中文版还会查中文 wiki 和攻略站，用来确定官方中文名
- 可选：Playwright + Chromium，用于截图质检。

### 安装

任选一种：

```bash
# A. 克隆仓库，在仓库目录里运行 claude（Claude Code 会自动发现 .claude/skills/ 下的 skill）
git clone https://github.com/<owner>/<repo>.git && cd <repo> && claude

# B. 装成个人 skill，所有项目都能用
cp -r .claude/skills/platinum-helper ~/.claude/skills/
```

### 在其他工具中使用

skill 用的是公开的 Agent Skills 格式（一个带 `SKILL.md` 的文件夹），把整个 `platinum-helper/` 文件夹复制到对应工具的 skills 目录即可：

| 工具 | 项目级目录 | 个人级目录 | 备注 |
|---|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | 本仓库默认位置，克隆即用 |
| OpenAI Codex | `.agents/skills/`（当前目录到仓库根目录都会扫描） | `~/.agents/skills/` | 输入 `/skills` 或 `$` 调用，也会按描述自动选用 |
| [DeepSeek Harness](https://www.deepseek.com/en/harness/) | `.dsh/skills/` 或 `.agents/skills/` | `~/.dsh/skills/` 或 `~/.agents/skills/` | `npx @deepseek-ai/dsh web` 启动（需要 Node.js），也有 macOS / Windows 桌面版；支持子代理 |
| 腾讯 CodeBuddy Code | `.codebuddy/skills/` | `~/.codebuddy/skills/` | |

```bash
# 例：装成个人 skill，Codex 和 DeepSeek Harness 都会读 ~/.agents/skills/
mkdir -p ~/.agents/skills && cp -r .claude/skills/platinum-helper ~/.agents/skills/

# 例：腾讯 CodeBuddy 项目级
mkdir -p .codebuddy/skills && cp -r .claude/skills/platinum-helper .codebuddy/skills/
```

### 用法

在 Claude Code（或你用的工具）里直接说：

> 帮我做《只狼：影逝二度》的白金小助手：<br>
> https://www.powerpyx.com/sekiro-shadows-die-twice-trophy-guide-roadmap/<br>
> https://www.powerpyx.com/sekiro-shadows-die-twice-full-walkthrough-all-areas/

- **要英文版**：「做一个**英文版**的白金小助手：<两个网址>」
- **只有trophy guide的网页**：只发trophy guide也行，它会自己找 PowerPyx 的收集攻略或全流程攻略。

它会一口气跑完全部流程：

```
抓取 → 解析 → 查官方中文名 → 翻译 → 拆成单个勾选 → 组装 → 标奖杯前置 → 放入奖杯指南步骤 → 截图质检
```

英文版没有查名和翻译这两步。跑完后会汇报结果、不确定的译名和发现的问题。一个完整游戏大约 1–2 小时。

**输出**：`<游戏>/<游戏>_platinum_helper.html`，用手机浏览器打开即可。中间数据保存在 `<游戏>/build/`，以后修改不用重跑。

### 目录

```
.claude/skills/platinum-helper/
├── SKILL.md          主流程与默认质量规则
├── scripts/          抓取、解析、组装、质检脚本（Python 标准库）
├── references/       各阶段说明：翻译、拆实体、奖杯前置、步骤卡片、英文版流程、game.json 字段、踩过的坑
├── assets/           页面模板 template.html
└── examples/         已做过的游戏配置（明末、影之刃零、只狼、剑星），新游戏照着改
```

### 注意

- 页面内容来自 [PowerPyx](https://www.powerpyx.com) 的攻略（中文版是翻译）。请仅供个人使用，保留页面里注明的来源；公开转载或商用前请先取得 PowerPyx 的许可。
- 不要发布 `build/` 文件夹，里面是下载的原始网页。
- 勾选进度存在浏览器本地，换设备前请用「⋯ → 导出进度」备份。

### 感谢

- 小黑盒影之刃零全成就全收集攻略工具的作者@[一君yijun](https://www.xiaoheihe.cn/app/user/profile/26db6861f6cf?user_id=26db6861f6cf&h_src=heyboxapp) 发现非常好用，感谢无偿使用！不用再怕支线断了哪里没有全收集。
- [Powerpyx](https://www.powerpyx.com/) 非常好用的奖杯guide网站！

---

## English

### What it is

A skill that generates checklist-style HTML route guides for earning a platinum.

**Input**: guide URLs; **Output**: an HTML file

Two languages are supported:

- **Chinese**: uses the game's official Chinese names, with a one-tap switch to the English original in the top-right corner;
- **English**: English only, no translation needed, using roughly a third of the tokens of the Chinese version.

### What the page contains

- **Route**: arranged by region → step, one checkbox per thing (item, boss, save point, NPC). The title is just the name; how to get it is written underneath, with screenshots and video links.
- **Nothing missed**: bosses the walkthrough doesn't cover are inserted into the route in the order of PowerPyx's boss guide; collectibles a boss drops come right after that boss.
- **Missables**: only what PowerPyx's own text says can be missed, plus the missable trophies listed in the roadmap.
- **Trophy guide steps**: when to save / reload, ending branches and points of no return become cards at the matching spot in the route; story trophies appear where they unlock. For games with multiple endings, the whole plan is laid out along the route — follow it from top to bottom to get every ending.
- **Trophy tab**: notes for every trophy; collection trophies and "defeat all bosses" trophies are checklists, synced both ways with the route checkboxes.
- **Platinum / 100% mode**: platinum mode only counts what the platinum needs.
- **Search, filters (not done / missable / trophy-related), and progress saved in the browser**, with export and import.

### Requirements

- Claude Code, or another tool that supports Agent Skills (Codex, DeepSeek Harness, etc.). Claude Code runs parallel subagents, which is fastest (Claude says this...)
- Python 3 (standard library only; with Pillow installed, screenshots get compressed)
- Network access to powerpyx.com. The Chinese version also checks Chinese wikis and guide sites to confirm official Chinese names
- Optional: Playwright + Chromium, for screenshot QA.

### Install

Pick one:

```bash
# A. Clone the repo and run claude inside it (Claude Code finds skills under .claude/skills/ automatically)
git clone https://github.com/<owner>/<repo>.git && cd <repo> && claude

# B. Install as a personal skill, available in all your projects
cp -r .claude/skills/platinum-helper ~/.claude/skills/
```

### Other agent tools

The skill uses the open Agent Skills format (a folder containing `SKILL.md`). Just copy the whole `platinum-helper/` folder into the matching tool's skills directory:

| Tool | Project-level directory | User-level directory | Notes |
|---|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | Default location in this repo; works right after cloning |
| OpenAI Codex | `.agents/skills/` (scanned from the current directory up to the repo root) | `~/.agents/skills/` | Type `/skills` or `$` to invoke it; it is also picked automatically from its description |
| [DeepSeek Harness](https://www.deepseek.com/en/harness/) | `.dsh/skills/` or `.agents/skills/` | `~/.dsh/skills/` or `~/.agents/skills/` | Start with `npx @deepseek-ai/dsh web` (requires Node.js); desktop apps for macOS / Windows too; supports subagents |
| Tencent CodeBuddy Code | `.codebuddy/skills/` | `~/.codebuddy/skills/` | |

```bash
# Example: personal install — Codex and DeepSeek Harness both read ~/.agents/skills/
mkdir -p ~/.agents/skills && cp -r .claude/skills/platinum-helper ~/.agents/skills/

# Example: Tencent CodeBuddy, project-level
mkdir -p .codebuddy/skills && cp -r .claude/skills/platinum-helper .codebuddy/skills/
```

### Usage

Just say this in Claude Code (or whichever tool you use):

> Make a platinum helper for Sekiro: Shadows Die Twice:<br>
> https://www.powerpyx.com/sekiro-shadows-die-twice-trophy-guide-roadmap/<br>
> https://www.powerpyx.com/sekiro-shadows-die-twice-full-walkthrough-all-areas/

- **English version**: "Make an **English** platinum helper: <two URLs>"
- **Only have the trophy guide page**: sending just the trophy guide is fine; it finds PowerPyx's collectibles guide or full walkthrough on its own.

It runs the whole pipeline in one go:

```
fetch → parse → look up official Chinese names → translate → split into single checkboxes → assemble → mark trophy prerequisites → add trophy guide steps → screenshot QA
```

The English version skips the name lookup and translation steps. When it finishes, it reports the result, any uncertain translations and the problems it found. A full game takes about 1–2 hours.

**Output**: `<game>/<game>_platinum_helper.html` — just open it in a phone browser. Intermediate data is kept in `<game>/build/`, so later changes don't need a full re-run.

### Layout

```
.claude/skills/platinum-helper/
├── SKILL.md          main workflow and default quality rules
├── scripts/          fetch, parse, assemble and QA scripts (Python standard library)
├── references/       per-stage guides: translation, entity splitting, trophy prerequisites, step cards,
│                     English workflow, game.json fields, known pitfalls
├── assets/           page template (template.html)
└── examples/         configs of games already done (Wuchang, Phantom Blade Zero, Sekiro, Stellar Blade) — adapt one for a new game
```

### Notes

- Page content comes from [PowerPyx](https://www.powerpyx.com) guides (the Chinese version is a translation). Please keep it for personal use and keep the source credit shown on the page; get PowerPyx's permission before republishing it or using it commercially.
- Don't publish the `build/` folder; it contains the downloaded source pages.
- Progress is stored locally in your browser; back it up with "⋯ → Export progress (JSON file)" before switching devices.

### Thanks

- @[一君yijun](https://www.xiaoheihe.cn/app/user/profile/26db6861f6cf?user_id=26db6861f6cf&h_src=heyboxapp), author of the Phantom Blade Zero all-achievements / all-collectibles guide tool on Xiaoheihe (小黑盒): found it really handy — thank you for making it free to use! No more worrying about breaking a side quest or missing a collectible.
- [PowerPyx](https://www.powerpyx.com/): a really great trophy guide site!
