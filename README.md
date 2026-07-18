# Nethard Music

Nethard Music（项目原名 Mouse Random Move）是一个面向 Windows 11 的单窗口输入自动化工具。它只向用户明确选择的一个可见 Chrome 顶层窗口发送鼠标移动、单击、滚轮或键盘动作，并提供亮色高对比界面、后台状态显示和可恢复的鼠标穿透模式。

## 主要功能

- 枚举可见 Chrome 顶层窗口，并用可读名称区分同名窗口。
- 开始运行前自动聚焦目标；运行期间锁定目标，避免输入发送到其他窗口。
- 支持随机鼠标移动、单击、滚轮和键盘输入。
- 键盘快捷键支持任意组合的 `Ctrl / Shift / Alt / Win + A-Z / 0-9`，不使用 F 功能键。
- 快捷键完全留空时，键盘动作会随机输入 3–6 个字母或数字。
- 操作间隔可设置最小值和最大值；运行分钟设为 `0` 时持续运行。
- 使用 ttkbootstrap 的亮色高对比主题，提供全量模式和简易模式。
- 支持 40%–100% 透明度、长期置顶和鼠标穿透点击。
- 内置本地测试页面，可确认测试页收到的浏览器事件。
- 将启动、停止、动作发送、页面确认和错误写入本地 CSV 日志。

## 界面模式

### 简易模式

简易模式尽量利用整个窗口，适合长期置顶并在不切换焦点时查看和操作。界面显示：

- 当前是否正在运行；
- 占用整行的目标页面名称；
- 当前启用的移动、单击、滚轮和键盘功能；
- 可编辑的运行快捷键、操作间隔和运行分钟；
- 开始、停止、发送一次、透明度、置顶和穿透点击控制。

切换界面模式只改变布局，不会重建控制器、取消后台计时器或改变已经锁定的目标。

### 全量模式

全量模式在完整配置之外显示目标状态、下次动作倒计时、最近动作、测试页事件状态和已发送命令历史，适合配置与排查。

## 穿透点击与恢复

启用“穿透点击”后，鼠标点击会穿过 Nethard Music 窗口并作用于后方窗口。

恢复快捷键固定为：

```text
Ctrl + Shift + Alt + X
```

该快捷键会一直显示在简易模式底部和全量模式的窗口设置区域。全局恢复热键只在穿透模式启用期间注册；按下后会立即关闭穿透并恢复正常点击。如果快捷键已被其他程序占用，程序不会进入穿透模式。

## 系统要求

- Windows 11；
- 64 位 Python 3.12 或更高版本；
- Google Chrome；
- PowerShell。

## 安装与运行

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

程序启动后会打开本地测试页。完成验证后可关闭测试页，点击“刷新列表”，再选择实际目标 Chrome 页面。

## 使用流程

1. 选择目标 Chrome 页面。
2. 选择要启用的动作。
3. 如需固定键盘组合，选择至少一个修饰键和一个 `A-Z` 或 `0-9` 主键；不需要时全部留空。
4. 设置操作间隔和运行分钟。
5. 点击“发送一次”验证配置，或点击“开始”连续运行。
6. 点击“停止”结束任务。

输入是 Windows 的真实鼠标和键盘输入。请勿选择包含未保存内容、支付操作或其他重要数据的页面。目标窗口关闭、失效或过小时，任务会停止或拒绝发送。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖配置校验、普通键组合、输入事件顺序、倒计时、单窗口控制、简易模式布局和穿透恢复。

## 构建 EXE

先关闭正在运行的 `Nethard Music.exe`。最简单的方式是在资源管理器中双击：

```text
build.cmd
```

`build.cmd` 会绕过 PowerShell 执行策略、调用 `build.ps1`，并在成功或失败后等待按下 Enter，因此错误信息不会一闪而过。

也可以直接从 PowerShell 执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

如果系统已将 `.ps1` 关联到 PowerShell，也可以直接双击 `build.ps1`；脚本会尝试识别资源管理器启动方式并保留窗口。

脚本会自动：

1. 查找 64 位 Python 3.12 或更高版本；
2. 在缺失时创建项目内的 `.venv`；
3. 根据 `requirements.txt` 安装或更新构建依赖；
4. 运行 PyInstaller；
5. 将结果命名为：

```text
dist\Nethard Music.exe
```

首次构建需要能够安装 Python 依赖。后续构建会复用 `.venv`，只有依赖文件发生变化时才重新安装。

`build/`、`dist/`、虚拟环境、Python 缓存和 IDE 本地配置均为可再生成文件，不纳入 Git。

## 日志

默认日志目录：

```text
%LOCALAPPDATA%\MouseRandomMove\logs
```

每个 CSV 文件按日期生成，记录运行配置、目标、动作、确认结果和错误。

## 项目结构

```text
main.py                              程序入口
build.cmd                            双击构建入口（保留结果窗口）
build.ps1                            自动准备环境并构建 EXE
Mouse Random Move.spec               PyInstaller 正式配置
mouse_random_move/
  app.py                             窗口、运行状态和调度基础
  light_console.py                   亮色全量/简易界面
  light_product.py                   产品帮助信息
  click_through_app.py               穿透点击与安全恢复热键
  config.py                          配置解析与校验
  controller.py                      单目标动作控制
  chrome_launcher.py                 Chrome 与测试页启动
  event_log.py                       CSV 日志
  paths.py                           源码和打包资源路径
  frontend/                          本地事件测试页面
  web/server.py                      本地测试服务
  win32/
    chrome_windows.py                Chrome 窗口枚举
    dpi.py                           DPI 适配
    input_sender.py                  鼠标、滚轮和普通组合键发送
tests/                               单元测试
```
