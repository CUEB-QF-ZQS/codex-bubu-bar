# Codex Usage Bar

一个 macOS 状态栏小工具，用来显示 Codex 剩余额度：

```text
5h 87% | Wk 98%
```

它每 20 分钟请求一次 Codex App 的 Usage & billing 接口：

```text
https://chatgpt.com/backend-api/wham/usage
```

这个请求只读取额度信息，不运行 `codex exec`，不发送模型 prompt，正常情况下不消耗 Codex 模型 tokens。

## 效果

- 状态栏显示：`小熊图标 + 5h xx% | Wk xx%`
- `5h`：5 小时窗口剩余百分比
- `Wk`：weekly 窗口剩余百分比
- 每 20 分钟自动刷新一次
- 菜单里可以点 `Refresh Now` 立即刷新

## 前置条件

需要本机已经安装并登录 Codex：

```sh
codex login status
```

如果没有登录，先执行：

```sh
codex login
```

还需要 macOS 有 Swift 编译器，一般安装 Xcode Command Line Tools 即可：

```sh
xcode-select --install
```

## 安装

在项目目录执行：

```sh
./scripts/install.sh
```

安装后会生成：

```text
~/Applications/CodexUsageBar.app
~/.local/bin/codex-usage-refresh
~/.local/bin/codex-usage-remaining
~/Library/LaunchAgents/com.madness.codexusagebar.plist
```

安装脚本会自动启动状态栏 App，并配置登录后自启。

## 手动检查

主动刷新一次额度：

```sh
codex-usage-refresh
```

查看当前状态栏文本：

```sh
codex-usage-remaining
```

查看 JSON：

```sh
codex-usage-remaining --json
```

## 卸载

```sh
./scripts/uninstall.sh
```

## 数据保存在哪里

运行状态保存在：

```text
~/.local/state/codex-usage-bar
```

本地快照只保存显示所需字段，例如 plan type 和 rate limit 窗口，不保存邮箱。

## Plan B：让 Codex 帮你重新配置

如果你换电脑、路径乱了，或者状态栏不刷新，可以直接把下面这段提示词发给 Codex：

```text
请帮我在这台 Mac 上配置 Codex Usage Bar。

要求：
1. 项目目录是当前仓库。
2. 先确认 `codex login status` 正常。
3. 执行 `./scripts/install.sh` 安装状态栏 App。
4. 安装后运行 `codex-usage-refresh`，确认它能请求 `https://chatgpt.com/backend-api/wham/usage`。
5. 再运行 `codex-usage-remaining --json`，确认输出里有 `5h xx% | Wk xx%`。
6. 如果刷新失败，检查 `~/.local/state/codex-usage-bar/last-refresh.err.log`。
7. 不要使用 `codex exec` 来刷新额度，避免消耗模型 tokens。
```

## 注意

`/backend-api/wham/usage` 是 Codex App 使用的内部接口，未来可能变化。如果接口失效，脚本会退回读取本地 Codex session 日志里的 `rate_limits` 事件，但这个 fallback 不一定实时。
