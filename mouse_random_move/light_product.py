from __future__ import annotations

from tkinter import messagebox

from .light_console import LightControlConsoleApp


class NethardLightApp(LightControlConsoleApp):
    def _show_help(self) -> None:
        messagebox.showinfo(
            "使用说明",
            "简易模式：直接设置目标页面、启用功能、普通键组合快捷键、间隔和运行分钟。\n"
            "全量模式：在上述设置之外查看倒计时和完整命令历史。\n\n"
            "快捷键支持 Ctrl、Shift、Alt、Win 多选，并搭配 A-Z 或 0-9；不使用 F 键。\n"
            "组合键完全留空时，键盘动作会随机输入 3–6 个字符。\n\n"
            "模式切换只改变界面，不会重建控制器、取消后台计时器或改变已锁定目标。\n"
            "简易模式默认位于屏幕右上角并保持置顶。\n"
            "启用穿透点击后，按 Ctrl + Shift + Alt + X 可恢复点击；该提示始终显示在界面底部。\n\n"
            f"本地测试页面：{self.server.url}\n"
            f"日志目录：{self.logger.log_dir}",
            parent=self.root,
        )
