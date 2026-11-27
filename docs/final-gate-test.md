# `check_soak_final.py` 合成测试记录

测试时间：2026-11-27（24h 浸泡运行期间，仅读临时 fixture，不碰 PID 7816）  
被测脚本：`3d/tools/check_soak_final.py`  
测试脚本：`3d/tools/test_check_soak_final.py`

目的：确认最终 gate 在有效完成、进程已死、字段缺失、样本不足、仍在运行和 checkpoint 缺失时返回正确退出码，避免 24h 结束后误判。

## 测试方法

`test_check_soak_final.py` 为每个用例生成唯一 tag：

- 临时文件只在 `3d` 下创建 `longrun_<tag>.json`；
- 调用真实 `check_soak_final.py --tag <tag>` 作为子进程；
- 断言退出码和关键 issue 文本；
- `finally` 删除临时 JSON，不修改生产 checkpoint。

基础有效 fixture：`status=done`、`finished_at` 存在、`alive_after_soak=true`、无 `error`、60 秒、3 个样本。其余用例在此基础上单点改坏。

## 结果

8/8 通过：

| 场景 | 期望 | 实际 |
|---|---|---|
| 有效完成 | exit 0 | exit 0 |
| `alive_after_soak=false` | exit 1 | exit 1，`alive_after_soak is not true` |
| `error` 非空 | exit 1 | exit 1，`error: synthetic failure` |
| `finished_at` 缺失 | exit 1 | exit 1，`finished_at missing` |
| `sample_count` 不一致 | exit 1 | exit 1，`sample_count 4 != samples length 3` |
| 样本数不足 | exit 1 | exit 1，`sample count 3 < expected 2881` |
| `status=running` | exit 3 | exit 3 |
| checkpoint 缺失 | exit 2 | exit 2，`missing checkpoint` |

运行命令：

```powershell
Set-Location 'F:\WhaleGirlPet'
& '.\.venv\Scripts\python.exe' '3d\tools\test_check_soak_final.py'
```

## 未覆盖

- 真实 24h 完成后的 `finish` 记录（要等 2026-11-28 13:51 后）；
- `finished_at` 格式非法、`samples` 为空等更边缘组合；
- Windows 任务计划程序返回码与实际进程状态的交叉验证。

## 结论

8 条路径符合脚本声明；该脚本可以作为 24h 结束后的第一道 gate，但不能替代真实 24h 运行。
