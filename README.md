# huawei-bloom

[English](README.en.md) | **繁體中文**

為 **Claude Code** 與 **Codex CLI** 加上華為風格的花瓣開場、HUAWEI 首頁與品牌 header。  
不修改 app 的設定檔、憑證或外掛；不安裝 daemon，也不寫入快取。

<p align="center">
  <img src="docs/home-claude.png" alt="huawei-bloom 的 Claude Code 首頁" width="680">
</p>

<p align="center"><sub>Claude Code · 繁體中文 · 95×55</sub></p>

## 亮點

- 官方八瓣花輪廓與 HUAWEI 向量字標，使用 octant 字形呈現
- 啟動時播放一次 Bloom；之後在有空白區域時，每 8 秒緩慢掃光
- Header 換成 `盤古·Claude` / `盤古 · Codex`，Claude 圖示換成小花
- 中文自動切換繁體 / 簡體；依 locale 判斷，也可用環境變數指定
- `/clear` 後首頁回歸；非空提交會停止 ambient 並清掉背景 art
- 直接指令、非 TTY、`--raw` 完全繞過 wrapper
- 不改 Claude Code / Codex 的設定、憑證、插件或權限

## 效果

<p align="center">
  <img src="docs/home-codex.png" alt="huawei-bloom 的 Codex 首頁" width="680">
</p>

<p align="center"><sub>Codex · 繁體中文 · 111×55</sub></p>

## 需求

- macOS 或 Linux，Python 3.9+
- Unicode + truecolor 終端機；Ghostty 建議開啟 octant 字形
- 終端機字型需要支援所選的中文（繁體或簡體）
- tmux 可用；tmux 內會自動查詢實際終端機類型

## 安裝

最簡單的方式是把命令連結到單一 checkout：

```sh
mkdir -p ~/.local/bin
ln -sf /path/to/huawei-bloom/huawei-bloom ~/.local/bin/huawei-bloom
```

如果使用複製安裝，checkout 仍是唯一來源；更新後重新同步即可：

```sh
INSTALL=~/.local/lib/huawei-bloom
mkdir -p "$INSTALL" ~/.local/bin
rsync -a --exclude=__pycache__ agent_theme "$INSTALL"/
cp huawei-bloom README.md README.en.md LICENSE NOTICE "$INSTALL"/
ln -sf "$INSTALL/huawei-bloom" ~/.local/bin/huawei-bloom
```

加入 shell function，讓平常的 `claude` / `codex` 自動經過主題：

```zsh
_huawei_bloom() {
  local app=$1; shift
  (( $+commands[huawei-bloom] )) && { command huawei-bloom "$app" "$@"; return; }
  command "$app" "$@"
}
claude() { _huawei_bloom claude "$@"; }
codex() { _huawei_bloom codex "$@"; }
```

`command claude` / `command codex` 永遠可以繞過 wrapper。  
移除 shell function、`~/.local/bin/huawei-bloom` 和安裝目錄即可解除安裝。

## 使用

```sh
huawei-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

| 選項 | 預設 | 用途 |
| --- | --- | --- |
| `--logo` / `--no-logo` | 開 | 只切換 header 圖示；Claude 小花、Codex `✿` |
| `--header` / `--no-header` | 開 | Header 名稱：`盤古·Claude` / `盤古 · Codex` |
| `--title` / `--no-title` | 關 | 視窗標題；預設關閉以保留 tmux pane 搜尋 |
| `--home` / `--no-home` | 開 | Bloom、ambient 與首頁；`--no-home` 會關閉整個 overlay，Codex 恢復原生 welcome |
| `--raw` | 關 | 完全不經過 wrapper |
| `--check` |  | 檢查內建 pattern、渲染引擎、binary 與版本 |

Element flags、`--raw`、`--check` 可以放在 app 名稱前或後；  
`--help` / `--version` 只在 app 名稱前由 wrapper 處理，放在 app 後面會傳給 app。  
`--` 之後的參數一律傳給 app。

## 行為

- 全新 session：播放一次 Bloom，但 header 和輸入區立即可用，動畫不阻塞輸入。
- `claude -c`、`--resume`、`codex resume` / `fork`、或命令列直接給 prompt：不播放入場動畫。
- 空白 Enter：不中斷動畫。
- 非空提交：停止 ambient，清除背景 art；不會把首頁畫到對話上。
- `/clear`：首頁與 ambient 回來。
- 直接 / 非互動指令：不建立 PTY，直接執行原程式。
- Codex 首頁開啟時，使用本次 session 的 `-c tui.effects.welcome=false` 與 `-c tui.show_tooltips=false`；不寫入設定檔。

## 繁體 / 簡體

預設依 locale 自動選擇：

- `zh_TW` / `zh_HK` / `zh_MO` → 繁體
- `zh_CN` / `zh_SG` → 簡體
- 非中文 locale → 繁體

強制指定：

```sh
AGENT_THEME_LANG=zh-Hant huawei-bloom claude
AGENT_THEME_LANG=zh-Hans huawei-bloom codex
```

## 環境變數

| 變數 | 預設 | 用途 |
| --- | --- | --- |
| `AGENT_THEME_GLYPHS` | 自動 | `octant` 或 `quadrant`；自動偵測 Ghostty，包含 tmux 內 |
| `AGENT_THEME_PALETTE` | 自動 | `light` 或 `dark`；先看 `COLORFGBG`，再看 macOS 外觀 |
| `AGENT_THEME_CELL_RATIO` | 自動，回退 `2.12` | 終端機字元格高寬比；有像素尺寸時自動計算 |
| `AGENT_THEME_LANG` | 自動，回退繁體 | `zh-Hant` 或 `zh-Hans` |
| `AGENT_THEME_DEBUG` | 未設定 | 將 overlay timing 寫入指定檔案；預設不寫 log |

在 tmux 中若 `automatic-rename` 開啟，視窗名會是 `claude` / `codex`，而不是 Python；  
手動命名的視窗不會被覆蓋，乾淨退出時會在名稱仍是 wrapper 設定值時恢復 `automatic-rename`。  
底層 `#{pane_current_command}` 仍是 Python，狀態列請用 `#{window_name}` / `#W`。

## 驗證

```sh
python3 -m unittest discover -s tests -v
./huawei-bloom --check claude
./huawei-bloom --check codex
```

`--check` 檢查內建 fixture、overlay / Bloom 引擎、binary 與版本；它不會啟動互動 session，也無法偵測真實 TUI 的未來渲染變化。渲染器改變時會 fail-open，不會破壞輸出。

## 專案結構

```text
huawei-bloom              executable entry point
agent_theme/
  cli.py                  參數、help、--check、process entry
  apps.py                 Claude / Codex profile、pattern、參數策略
  i18n.py                 繁體 / 簡體字串
  replacer.py             streaming byte replacement
  launcher.py             PTY loop、signal、terminal restore
  supervisor.py           foreground process group / hangup mirroring
  terminal.py             winsize、glyph / palette / tmux detection
  animation.py            Bloom / ambient compositor
  overlay.py              screen model / home painting
  intro.py                Bloom scene
  art.py                  vector mark、wordmark、lockup、palette
  assets/art.json         vector data
docs/                      README screenshots
```

## 來源與授權

Bloom 引擎、overlay 模型與華為風格圖稿改作自
[pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme)，
上游程式碼為 MIT，commit
`cefaa53080dd625be9bcc8060051fbbf2dc89723`。

程式碼與版面依 MIT 授權；HUAWEI、華為花瓣標誌與 HUAWEI 字標是華為技術有限公司的商標，不在 MIT 授權範圍內。本專案與 Huawei、Anthropic、OpenAI 均無隸屬關係。

## 限制

- byte-level 品牌替換對應目前的 Claude Code 2.1.x 與 Codex 0.163.x renderer；`--check` 只能檢查本地 fixture 與 binary 是否存在，不能偵測真實 TUI 改版。
- 首頁需要空白列；太窄、太矮或被 Codex help list 佔滿的 pane 可能沒有首頁。
- `/clear` 後因為 echo 列佔位，首頁可能重新縮放。
- 僅支援 POSIX；Windows 不支援。
