# 发布文档链接检查

时间：2026-11-27 16:00 左右  
范围：README、CHANGELOG、v3.2.0-sprite 两份 Release 文档、post-soak runbook、证据索引、CI 审计、浸泡记录、sprite-layer、工具链预检、gate 预检。  
方式：只读解析 Markdown `[]()` 与 HTML `href` / `src`，相对路径按文件所在目录解析；未访问外链。

## 结果

```text
files=11 links_checked=14 dead=0
EXIT_CODE=0
```

- 14 个本地链接/资源全部存在；
- 没有发现死链；
- README 的 `assets/ui/pet.ico` 等 HTML 图片引用也已检查。

## 未覆盖

- 外部 URL（http/https）未做网络可达性检查；
- 反引号里的路径不是 Markdown 链接，未纳入本次检查；
- 锚点只检查了目标文件是否存在，没有逐条验证标题锚点；
- 未来才会生成的 `docs/_3d_visible_17_cards.png`、`docs/2d-card-visible-qa.json`、`docs/click-through-result.json` 仍按“待补”处理，不属于死链。

## 结论

发布文档的本地链接当前干净；这只是文档层检查，不代表外部 Release 链接或未来产物已存在。
