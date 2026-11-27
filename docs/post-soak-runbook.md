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
- 如果 gate 不是 `exit 0`，先运行 `& '.\3d\tools\collect_soak_evidence.ps1' -OutDir 'docs\soak-evidence'` 保存现场，再判断是进程消失、checkpoint stale 还是字段无效；不要用新进程覆盖现场。

## 0.5 P1 坏 manifest 回归（分支验证）

P1 纯解析代码在 `build\worktrees\fix-sprite-parser` 分支，未合入 `main`。浸泡结束后先编只含纯解析的测试，不产出生产 exe：

```powershell
Set-Location 'F:\WhaleGirlPet\build\worktrees\fix-sprite-parser'
$gxx = (Get-ChildItem 'F:\WhaleGirlPet\.toolchains\w64devkit' -Recurse -Filter 'g++.exe' | Select-Object -First 1).FullName
& $gxx -std=c++17 -O2 -I '3d' `
  '3d\tests\test_sprite_manifest.cpp' `
  '3d\sprite_manifest.cpp' `
  -o 'build\test_sprite_manifest.exe'
& '.\build\test_sprite_manifest.exe'
```

预期：`17/17 passed`。夹具在 `3d\tests\fixtures\sprite_manifest\cases.json`；不覆盖生产 `3d\whale3d.exe`，不启动 `whale3d.exe`。

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

判定：点击穿透失败时，不能把 `docs/sprite-layer.md` 的“卡面不进入 `hitTest`”写成已通过。

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

### 5.1 Release notes

- 正式说明用 `docs\releases\v3.2.0-sprite.md`，不要另写一份短文案；
- 上传前把最终文件大小、SHA256、tag 写回该文件和 `docs\release-assets-3.2.0-sprite.json`；
- 如果资产没有重建，先核对两份文件里的哈希与实际文件一致，不要只改说明。

### 5.2 资产重算与 verifier

```powershell
Set-Location 'F:\WhaleGirlPet'
Get-FileHash -Algorithm SHA256 -LiteralPath `
  '3d\whale3d.exe', `
  '3d\whale3d-whale-girl-v3.2-sprite.zip', `
  'dist\3d\WhaleGirlPet-Setup-3.2.0-sprite.exe'
& '.\.venv\Scripts\python.exe' '3d\tools\verify_release_assets.py'
```

- 要求 verifier `exit 0`，`docs\release-asset-verify.md` 的 38 项全 PASS；
- 安装器 `.sha256` sidecar 必须与安装器同目录、同哈希；
- 安装器内部 payload 仍未解包核对，不能把 verifier PASS 当成“安装器内容逐字节确认”。

### 5.3 上传顺序

只有 24h gate、17 卡、点击穿透、2D 冻结包、安装器五项都有证据后才上传：

1. 确认 tag `v3.2.0-sprite` 指向最终发布提交，不复用 `v3.2.0-dev`；
2. 创建 Release，说明文件用 `docs\releases\v3.2.0-sprite.md`；
3. 先上传安装器 `WhaleGirlPet-Setup-3.2.0-sprite.exe` 和 `.sha256` sidecar；
4. 再上传便携 ZIP `whale3d-whale-girl-v3.2-sprite.zip`；
5. 最后上传 `3d\whale3d.exe` 作为单独 exe 资产；
6. 上传后重新下载至少安装器和 ZIP，核对远端 SHA256 与本地一致。

不要运行 `release-assets.yml`；不要用 `--clobber` 覆盖已有 Release；不要在发布说明里写“24h 长稳通过”，除非 `check_soak_final.py` 已 `exit 0`。

## 失败回滚

- 17 卡中某张裁切/方向错：先看 `manifest` rect 和图集内容，再决定是否重建图集；
- 点击穿透失败：检查 `ShellUi::updateWindowRegion` 和 `WndProc` 的 `WM_NCHITTEST`，不要在 24h 期间改；
- 2D 冻结包读不到卡：检查 `WhaleGirlPet.spec` datas 和冻结目录结构；
- 安装器启动失败：先看安装目录 `assets\2d_bridge` 是否存在，再看 `whale3d.log` 的 `Sprite layer unavailable` 原因。
