# 快速上手

1. 将 `Luna_Final.zip` 完整解压到一个可写入的本地目录。
2. 双击 `Start_Luna.cmd`。首次启动会先导入素材。
3. 按 Space 开始约 44.4 秒的自动循环演示；按数字键或按钮可以单独预览。
4. 关闭预览窗口即结束程序。

本包附带 Windows 64 位 Godot 4.7.2，无需依赖旁边的 Phase 工程。请保持 `tools/godot/` 内两个程序一起存在。

## 开发入口

`LunaFinalTest.tscn` 是演示场景；在自己的场景中实例化 `LunaPet.tscn` 即可复用角色。所有鼠标坐标接口接受 Godot 的全局画布坐标。角色原画布为 1536×2304；预览缩放是 0.28，不会改变正式贴图。

若由宿主转发鼠标事件，应关闭 `InteractionController.mouse_input_enabled`，避免一次点击被重复处理。正常情况下保留 `automatic_processing=true`，由 Godot 自行更新。

原始 PSD 保留于 `source/`。当前可运行效果以 `runtime_layers/`、`assets/`、动画和控制器为准；原 PSD 没有合并后续局部表情和手势更新。

## 验证

在 PowerShell 中执行 `./Run_Verification.ps1` 可重新运行自动测试。结果写入 `data/`。

提供 Pillow、NumPy 环境的 Python 后，执行 `./Run_Verification.ps1 -PythonPath <python路径>` 还会检查文件冻结哈希、裁剪信息和现有画面证据。

重新截取实际 Godot 画面：增加 `-RenderPreviews`。重新导出 MP4 时，安装 FFmpeg 并加入 PATH，或单独调用 `tools/export_final_previews.py --ffmpeg <ffmpeg路径>`。这些工具只用于重新验收和导出，观看动画无需 Python 或 FFmpeg。
