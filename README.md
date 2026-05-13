# 游戏冒烟测试脚本

## 简介

自动化 SLG 游戏主线冒烟测试。支持 ADB（模拟器）和 Unity Editor 两种输入后端。

## 功能

- 自动识别游戏状态（大地图/副本/结算/对话）
- 自动领取任务奖励
- 自动导航 + 摇杆跑路
- 自动进入副本（全自动战斗）
- 自动结算返回

## 安装

```bash
pip install -r requirements.txt
```

## 使用

### 第一步：校准坐标

先用校准工具设置 UI 元素位置：

```bash
# ADB 模式（模拟器）
python calibrate.py --backend adb --serial 127.0.0.1:5555

# Unity Editor 模式
python calibrate.py --backend unity --url http://127.0.0.1:8765
```

在校准界面：
- 按 `1` 设置摇杆位置（按住出摇杆的区域）
- 按 `2` 设置任务按钮位置
- 按 `3` 设置副本入口位置
- 按 `4` 设置副本确认按钮位置
- 按 `5` 设置结算返回按钮位置
- 按 `s` 保存配置
- 按 `q` 退出

### 第二步：准备模板图片

截取游戏中的 UI 元素，放入 `templates/` 目录：

| 文件名 | 说明 |
|--------|------|
| `dungeon_entry.png` | 副本入口按钮 |
| `dungeon_confirm.png` | 副本确认/进入按钮 |
| `settlement_return.png` | 结算画面返回按钮 |
| `battle_hud.png` | 战斗中的 UI 元素（血条/技能栏等） |
| `dialog_box.png` | 对话框特征 |

### 第三步：运行测试

```bash
# ADB 模式 - 雷电模拟器
python main.py --backend adb --serial 127.0.0.1:5555

# ADB 模式 - MuMu 模拟器
python main.py --backend adb --serial 127.0.0.1:7555

# ADB 模式 - 夜神模拟器
python main.py --backend adb --serial 127.0.0.1:62001

# Unity Editor 模式
python main.py --backend unity --url http://127.0.0.1:8765

# 运行 10 分钟后自动停止
python main.py --backend adb --duration 600

# 干跑模式（只检测状态，不操作）
python main.py --backend adb --dry-run
```

## Unity Editor 集成

1. 将 `unity_scripts/GameTestServer.cs` 复制到 Unity 项目的 `Assets/Editor/` 目录
2. 在 Unity 菜单栏点击 `Tools > GameTestServer > Start`
3. 脚本会在 `http://127.0.0.1:8765` 启动 HTTP 接口

## 项目结构

```
game_test_bot/
├── config.py              # 配置（坐标、阈值）
├── backend/
│   ├── __init__.py
│   ├── base.py            # 输入后端抽象基类
│   ├── adb_backend.py     # ADB 后端（雷电/MuMu/夜神）
│   └── unity_backend.py   # Unity Editor HTTP 后端
├── vision.py              # 画面识别（模板匹配 + 颜色检测）
├── state_machine.py       # 状态机主逻辑
├── main.py                # 主入口
├── calibrate.py           # 坐标校准工具
├── requirements.txt       # Python 依赖
├── config.json            # 运行时配置（校准后自动生成）
├── templates/             # UI 模板图片
└── unity_scripts/
    └── GameTestServer.cs  # Unity HTTP 接口脚本
```

## 状态机流程

```
大地图
  ├─ 任务可领奖 → 点击领奖
  ├─ 任务未完成 → 点击导航 → 摇杆跑路 → 重复检查
  └─ 副本入口可见 → 点击进入 → 准备界面 → 确认
       → 战斗（全自动）→ 结算 → 返回 → 大地图
```

## 自定义配置

编辑 `config.json` 或直接修改 `config.py` 中的默认值：

- `run_duration_sec`：每次跑路时长（默认 3 秒）
- `run_max_attempts`：最大跑路次数（默认 10 次）
- `navigation_wait`：导航镜头移动等待时间（默认 2 秒）
- 颜色阈值：用于任务状态检测

## 常见问题

**Q: ADB 连接失败？**
- 确认模拟器已开启 ADB 调试
- 检查端口：雷电=5555, MuMu=7555, 夜神=62001
- 尝试 `adb connect 127.0.0.1:5555`

**Q: 状态识别不准？**
- 用截图工具截取 UI 元素放入 `templates/` 目录
- 调整 `config.py` 中的匹配阈值

**Q: 摇杆方向不对？**
- 重新校准摇杆位置
- 检查 `joystick_drag_max` 参数

**Q: Unity Editor 连接失败？**
- 确认 `GameTestServer.cs` 已放入 `Assets/Editor/`
- 确认已点击 `Tools > GameTestServer > Start`
- 检查端口 8765 是否被占用
