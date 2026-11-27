# 24 小时浸泡结束后的执行手册

用途：24h 浸泡 `soak_24h_sprite_task` 结束后，按顺序做最终核验、17 卡可见验收、点击穿透、2D 冻结包和安装器回归。  
**本手册不要在当前浸泡运行期间执行**；执行前先确认 PID 7816 已退出。

## 0. 先看结论，不要先开第二个 3D

```powershell
Set-Location 'F:\WhaleGirlPet'
& '.\3d\tools\check_soak_status.ps1'
& '.\3d\tools\check_soak_status.ps1' -Json
& '.\.venv\Scripts\python.exe' '3d\tools\check_soak_final.py'
```

判定：

- `check_soak_final.py` 必须 `exit 0`、`valid=True`、`status=done`、`alive_after_soak=True`。
- 样本数应接近 `2881`；少于 `2879` 需要说明原因。
- 只有 `status=done` 且上述都满足，才把这一轮写成“24h 通过”；否则只能写“未完成/无效”。
- 先归档 `3d/longrun_soak_24h_sprite_task.json`、`.log`、`.err.log` 和 `docs/soak-midrun-2026-11-27.md`，再开新进程。

## 1. 17 张卡可见验收

单实例批处理（推荐）：

```powershell
Set-Location 'F:\WhaleGirlPet'
& '.\.venv\Scripts\python.exe' '3d\tools\check_cards_visible.py'
```

脚本会先拒绝在已有 `whale3d.exe` 时启动，确保只开一个临时实例；然后按顺序发送 17 张卡，保存整窗截图和卡面裁图，生成：

- `docs/_3d_visible_17_cards.png`（contact sheet）
- `docs/2d-card-visible-qa.json`（逐卡文件与坐标）
- `docs/_3d_visible_card_<id>.png` / `..._crop.png`

预检状态（2026-11-27）：已通过 `py_compile`、`--help`；用当前 PID 7816 验证时脚本正确拒绝启动，没有生成第二个 3D。

备选：用 `emotion_longrun.py` 逐卡跑 8 秒，强制显示单卡并保存可见帧：

```powershell
$env:WHALE3D_LONGRUN_SECONDS='8'
$env:WHALE3D_LONGRUN_SAMPLE='2'
$env:WHALE3D_LONGRUN_OFFSCREEN='0'
$env:WHALE3D_LONGRUN_CARD_TTL='6000'
```

每张卡设置：

- `WHALE3D_LONGRUN_CARD`：`expression/idle` 等 17 个 id；
- `WHALE3D_LONGRUN_TAG`：`card_expr_idle_...`，只能用小写字母/数字/下划线；
- 运行 `.\.venv\Scripts\python.exe 3d\tools\emotion_longrun.py`。

17 个 id：

`expression/idle`、`expression/happy`、`expression/eat`、`expression/walk`、`expression/sleep`、`expression/sleepy`、`expression/shy`、`expression/angry`、`expression/curious`、`expression/pat`、`action/wave`、`action/dance`、`action/type`、`action/balloon`、`action/fireworks`、`action/lion`、`action/change`。

批量执行：

```powershell
$cards = @(
  'expression/idle','expression/happy','expression/eat','expression/walk',
  'expression/sleep','expression/sleepy','expression/shy','expression/angry',
  'expression/curious','expression/pat','action/wave','action/dance',
  'action/type','action/balloon','action/fireworks','action/lion','action/change'
)
$env:WHALE3D_LONGRUN_SECONDS='8'
$env:WHALE3D_LONGRUN_SAMPLE='2'
$env:WHALE3D_LONGRUN_OFFSCREEN='0'
$env:WHALE3D_LONGRUN_CARD_TTL='6000'
foreach ($card in $cards) {
  $env:WHALE3D_LONGRUN_CARD = $card
  $env:WHALE3D_LONGRUN_TAG = 'card_' + ($card -replace '/', '_')
  & '.\.venv\Scripts\python.exe' '3d\tools\emotion_longrun.py'
  if ($LASTEXITCODE -ne 0) { throw "card failed: $card" }
}
```

验收点：

- 日志 `Sprite layer: ready`；
- 日志出现对应 `Sprite card: <id>`；
- `docs/_3d_longrun_card_..._anim_a.png` 或 `_mid.png` 中卡面完整、正向、无整张图集网格；
- 17 张全过后，生成一张 17 卡 contact sheet，写入 `docs/2d-card-visible-qa.md`。

## 2. 卡面点击穿透

自动化探测（推荐，必须在浸泡结束后运行）：

```powershell
Set-Location 'F:\WhaleGirlPet'
& '.\.venv\Scripts\python.exe' '3d\tools\check_click_through.py' --click
```

脚本会启动一个临时 3D、显示 `expression/happy`，在卡面中心放一个测试目标窗口，执行一次真实左键点击，并把结果写到 `docs/click-through-result.json`。判定：

- `card_hit_test` 必须是 `-1`（`HTTRANSPARENT`）；
- `target.received` 必须是 `true`；
- 两项都满足脚本才 `exit 0`。

预检状态（2026-11-27）：脚本已做 `py_compile`，并用当前 PID 7816 做了 `--pid` 干跑；它正确识别到离屏卡面并返回 `exit 2`，没有执行点击，也没有启动第二个 3D。真实点击等浸泡结束再做。

不要拿当前 24h 浸泡窗口做这个测试；脚本默认只操作自己启动的临时进程，`--pid` 模式也不会结束目标进程。

手动交叉验证（脚本失败或需要看现场时）：

1. 启动 3D，设 `WHALE3D_CARD=expression/happy`、`WHALE3D_CARD_TTL=10000`、`WHALE3D_SPRITE_TRACE=1`。
2. 从日志读取 `Sprite rect: (x,y w,h)`；卡面在客户区右下角。
3. 在卡面中心放一个可点击的测试窗口，用真实鼠标点一下卡面中心。
4. 预期：点击落到测试窗口，不触发 3D 拖拽/托盘/设置。
5. 同时记录 `WindowFromPoint`、`WM_NCHITTEST` 返回值和测试窗口是否收到点击。

判定：点击穿透失败时，不能把 `docs/sprite-layer.md` 的“卡面不抢点击”写成已通过。

## 3. 2D PyInstaller 冻结包

构建阶段不要启动冻结版；构建完成后再单独启动一次，确认 `assets/2d_bridge` 在包内：

```powershell
Set-Location 'F:\WhaleGirlPet'
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean WhaleGirlPet.spec
```

检查：

- 输出目录存在 `assets\2d_bridge\atlas.png`、`manifest.json`；
- 冻结版启动后 `AssetBridge` 能读到 17 卡；
- 冻结版发 `action/wave`，3D 日志出现 `source=P_2D card=action/wave`；
- 不把旧 2D 进程和当前 3D 混在一起判断。

## 4. 安装器回归

使用临时目录，避免影响现有安装：

```powershell
$setup = 'F:\WhaleGirlPet\dist\3d\WhaleGirlPet-Setup-3.2.0-sprite.exe'
$dir = 'F:\WhaleGirlPet\build\install-sprite-final'
& $setup /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="$dir"
```

检查：

- 安装退出码 0；`$dir\assets\2d_bridge` 存在；
- 启动安装后的 `whale3d.exe`，日志 `Sprite layer: ready`；
- `WHALE3D_CARD=expression/happy` 可见；
- 卸载退出码 0，临时目录清理干净。

## 5. Release 前最后一道门

- 运行 `& '.\.venv\Scripts\python.exe' '3d\tools\verify_release_assets.py'`，要求 exit 0，并核对 `docs/release-asset-verify.md` 的 38 项全 PASS；
- 重算 exe、ZIP、安装器 SHA256，与 `docs/release-3.2.0-sprite.md` 对照；
- 确认 17 卡可见验收、点击穿透、2D 冻结包、安装器四项都有证据；
- 再决定 tag（建议 `v3.2.0-sprite`）和是否发布；不要复用 `v3.2.0-dev`；
- 发布前不要把 `v3.2.0-sprite` 写成“24h 长稳通过”，除非 `check_soak_final.py` 已通过。

## 失败回滚

- 17 卡中某张裁切/方向错：先看 `manifest` rect 和图集内容，再决定是否重建图集；
- 点击穿透失败：检查 `ShellUi::updateWindowRegion` 和 `WndProc` 的 `WM_NCHITTEST`，不要在 24h 期间改；
- 2D 冻结包读不到卡：检查 `WhaleGirlPet.spec` datas 和冻结目录结构；
- 安装器启动失败：先看安装目录 `assets\2d_bridge` 是否存在，再看 `whale3d.log` 的 `Sprite layer unavailable` 原因。
