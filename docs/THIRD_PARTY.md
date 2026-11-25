# 第三方与参考声明

本项目 `app/skeletal.py`（v3.0.13 起的游戏引擎式 2D 骨骼动画）**没有复制任何第三方源码**，
全部代码为本项目自行编写；仅在**架构设计**上参考了以下开源项目的公开文档与实现思路。
Spine 运行时**未使用**（许可限制见下）。

## 一、设计参考（思路借鉴，代码自写）

| 项目 | 许可证 | 参考了什么 | 链接 |
|---|---|---|---|
| Godot Engine 4.x（`Skeleton2D` / `Bone2D` / `Polygon2D`） | MIT | 骨架树结构（每根骨落在"起点"、角度相对父骨）、用顶点权重把整张 sprite 绑到多根骨、关节处用权重过渡带避免硬折 | https://docs.godotengine.org/en/stable/tutorials/animation/2d_skeletons.html |
| Inochi2D | BSD 2-Clause | 2D rigging 的整体分层：模型 = 网格 + 变形器/骨骼 + 参数驱动动画；确认"开源 2D rigging"的可行边界（它是新格式，不兼容 Live2D） | https://inochi2d.com |

两者的许可证都允许商业使用与再分发；本项目既不复制其代码、也不打包其二进制，
因此不附带其许可证文本，仅为学术/工程上的出处声明。

## 二、明确未采用

| 项目 | 原因 |
|---|---|
| Spine Runtime（Esoteric Software） | Runtimes 虽公开源码，但许可要求"产品的每个用户自行持有 Spine Editor 授权"，且再分发必须附带其许可。桌宠是免费分发的桌面程序，不适合承担该义务。 |
| Live2D Cubism SDK | 专有许可，商用/分发需授权，且本机素材为整张 PNG，无 Cubism 模型文件。 |

## 三、本项目自己的实现（可对照查证）

- `app/anim_engine.py`（v3.0.11）：缓动函数、轨道关键帧、动作剪辑、事件点
- `app/rig.py`（v3.0.12）：两骨腿部网格蒙皮（髋→膝），三角形仿射绘制
- `app/skeletal.py`（v3.0.13）：通用骨架（Skeleton）+ 顶点权重（Skin）+ 动画剪辑（Clip）
  + 播放器（Player）+ 渲染（LBS 顶点形变 + 逐三角形仿射贴图）

## 三之二、v3.0.20 调研过的项目（只借鉴机制，未引入代码）

安全方向：

- VirusTotal/yara（10062★）：借「strings + condition」的规则形状，未引入 C 库或 yara-python。
- Cisco-Talos/clamav（7733★，GPLv2）：借「引擎与签名库分离、白名单先行」，未搬引擎（GPL 与本项目分发不兼容）。
- Neo23x0/Loki（3809★）：借「hash → 路径 → 规则」的判定顺序，代码为自写。
- Yara-Rules/rules（4966★）、YARA-Rules 社区规则：格式参考，未打包任何规则文件。
- fire1ce/eicar-standard-antivirus-test-files（266★）：EICAR 串本身是业界公开的测试常量，非版权素材。

动画方向：

- EsotericSoftware/spine-runtimes（5381★）：借 mix duration、track 排队、timeScale 三个概念；
  Spine Runtime 受商业授权约束，本项目**未使用其任何代码**（v3.0.13 起即此口径）。
- Inochi2D/inochi2d（1887★，BSD-2）、Inochi2D/inochi-creator（1269★，BSD-2）：只作设计参考，
  未拷贝代码；本项目骨骼与蒙皮为自写（`app/skeletal.py`）。


## 四、素材

立绘、表情、皮肤图均为本项目自制（AI 生成 + 手工挑选），不含第三方版权素材。
字体使用系统字体（微软雅黑等），仅在本地渲染，不随安装包分发。
