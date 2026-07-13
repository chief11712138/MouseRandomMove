# Mouse Random Move

Mouse Random Move 是一个面向 Windows 11 的单窗口鼠标与键盘输入模拟工具。它会打开一个本机测试页面，只向用户明确选中的 Chrome 测试窗口发送随机移动、点击、滚轮和键盘动作，并记录每次动作的页面确认结果。

## 功能概览

- 枚举当前所有可见 Chrome 顶层窗口。
- 下拉框只显示窗口标题，不暴露 HWND、进程 ID 等内部编号。
- 同名窗口会追加“同名窗口 1/2”等可读后缀，方便区分。
- 每次运行只锁定一个选中的 Chrome 窗口，不会广播到其他窗口。
- 运行期间禁止切换目标窗口，避免误操作。
- 如果目标窗口关闭、标题改变，或离开本机测试页面，任务会立即停止。
- 支持随机鼠标移动、单击、滚轮和普通字母数字键盘输入。
- 配套测试页面运行在 `127.0.0.1`，用于记录并回传浏览器事件。
- 桌面端会把动作发送、页面确认和错误信息写入 CSV 日志。

## 安全边界

程序会列出可见的 Chrome 窗口，便于用户识别目标；但只有标题包含以下文本的本机测试页面可以接收输入：

```text
Mouse Random Move Test
```

普通网页、登录页面、工作平台和第三方应用不会接收测试指令。Chrome 仍然是当前版本的目标浏览器，项目名称中的 Mouse Random Move 指的是工具的用途，而不是浏览器替代品。

## 项目结构

```text
main.py
mouse_random_move/
  app.py                     Tkinter 桌面界面
  config.py                  运行配置校验
  controller.py              单窗口运行控制器
  chrome_launcher.py         Chrome 启动与测试页打开
  event_log.py               CSV 审计日志
  paths.py                   源码/EXE 资源路径
  win32/
    chrome_windows.py        Chrome 窗口枚举与可读标题
    input_sender.py          Win32 输入发送
    dpi.py                   Windows DPI 适配
  web/
    server.py                本地 HTTP/API 服务
  frontend/
    index.html               配套检测页面
    styles.css               页面样式
    app.js                   事件检测与回传
tests/
  test_config.py
  test_window_labels.py
```

## 运行方式

1. 在 Windows 11 中安装 64 位 Python 3.12 或更新版本。
2. 确认已安装 Google Chrome。
3. 在项目根目录运行：

```powershell
python main.py
```

4. 点击“打开配套测试页”，程序会在 Chrome 新窗口中打开本机测试页面。
5. 点击“刷新列表”，选择标题类似 `Mouse Random Move Test - Google Chrome` 的窗口。
6. 先点击“发送一次”确认动作和页面回传正常，再按需要启动连续运行。

## 打包 EXE

如果项目中包含打包脚本，可在 PowerShell 中运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build.ps1
```

建议输出文件命名为：

```text
dist\MouseRandomMove.exe
```

## Hyper-V 注意事项

- 宿主机和客户机都使用 Windows 11 时，输入只会发生在客户机桌面会话中。
- 客户机必须保持解锁，不能处于暂停、保存或睡眠状态。
- 建议使用增强会话模式，并保持合理显示缩放。
- 程序会先把选定 Chrome 窗口激活到前台，再发送动作。
- 不需要管理员权限、外网访问或浏览器扩展。
- Chrome 窗口过小时会拒绝执行，以避免点击浏览器工具栏。

## 日志

默认日志目录：

```text
%LOCALAPPDATA%\MouseRandomMove\logs
```

每个日志文件按日期生成，记录开始、停止、动作发送、页面确认和错误信息。
