# 3.2.0-sprite 安装器 smoke 记录

日期：2026-11-28  
状态：**PASS**

## 安装

```powershell
$setup = 'F:\WhaleGirlPet\dist\3d\WhaleGirlPet-Setup-3.2.0-sprite.exe'
$dir = 'F:\WhaleGirlPet\build\installer-smoke-final-3.2.0-sprite'
& $setup /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="$dir"
```

- 安装退出码：`0`
- 安装器大小：`4,791,958 B`
- 安装器 SHA256：`CA6C2525FCB50D21699F512AECFCB18CFEBDA37337C9DE07EC5554E5A6974A45`

## 安装后哈希

| 文件 | 大小 | SHA256 |
|---|---:|---|
| `whale3d.exe` | 1,370,112 B | `74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893` |
| `assets/2d_bridge/atlas.png` | 357,857 B | `918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958` |
| `assets/2d_bridge/manifest.json` | 5,354 B | `EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D` |

## 启动与卸载

- 安装后的 `whale3d.exe` 已用于 17 卡可见验收和点击穿透测试；两项均通过。
- 卸载退出码：`0`。
- 临时安装目录卸载后为空并删除。

## 边界

- 本 smoke 不是逐字节解包安装器内部文件；它验证的是真实安装流程、安装目录内容、哈希和卸载路径。
- 安装器和 exe 当前为 `NotSigned`。
