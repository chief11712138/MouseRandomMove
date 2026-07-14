# Mouse Random Move

Mouse Random Move 是一个面向 Windows 11 的单窗口鼠标与键盘输入模拟工具。它可以向用户明确选中的任意可见 Chrome 顶层窗口发送随机移动、点击、滚轮和键盘动作。本机测试页面是可选的，用于验证并记录浏览器事件。

## 功能概览

- 枚举当前所有可见 Chrome 顶层窗口。
- 下拉框只显示窗口标题，不暴露 HWND、进程 ID 等内部编号。
- 同名窗口会追加“同名窗口 1/2”等可读后缀，方便区分。
- 每次运行只锁定一个选中的 Chrome 窗口，不会广播到其他窗口。
- 运行期间禁止切换目标窗口，避免误操作。
- 如果目标窗口关闭或不再是 Chrome 窗口，任务会立即停止。
- 支持随机鼠标移动、单击、滚轮和普通字母数字键盘输入。
- “下一次操作”按秒实时倒计时。
- 固定高度的滚动区域会显示每一条已发送命令及发送时间。
- 可选的配套测试页面运行在 `127.0.0.1`，用于记录并回传浏览器事件。
- 桌面端会把动作发送、可用的页面确认和错误信息写入 CSV 日志。

## 目标窗口与安全提示

程序会列出可见的 Chrome 顶层窗口。选择目标并开始后，每次运行仍只锁定一个窗口，不会向其他窗口广播。输入是真实的系统鼠标和键盘输入，因此请避免选择含有未保存内容、支付操作或其他重要数据的页面。

标题包含以下文本的本机测试页面还可以回传事件确认：

```text
Mouse Random Move Test
```

其他 Chrome 页面可以接收输入，但无法向本地程序回传确认，所以界面只报告“已发送”。Chrome 仍然是当前版本的目标浏览器，项目名称中的 Mouse Random Move 指的是工具的用途，而不是浏览器替代品。

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
  test_countdown.py
  test_controller.py
  test_window_labels.py
```

## 运行方式

1. 在 Windows 11 中安装 64 位 Python 3.12 或更新版本。
2. 确认已安装 Google Chrome。
3. 在项目根目录运行：

```powershell
python main.py
```

4. 程序会自动打开并选中配套测试页；先点击“发送一次”，确认动作和页面回传正常。
5. 验证完成后关闭测试页。
6. 点击“刷新列表”，选择实际需要操作的 Chrome 窗口。
7. 配置动作与间隔后点击“开始”。

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
