# LunaPet 接口

入口为 `LunaPet.tscn`。动画资源与状态、眨眼、表情、特效及骨架叠加逻辑分开。

| 方法 | 用法 |
|---|---|
| `play_idle_variant(requested="") -> bool` | Idle 时播放指定 `idle_look_around` 或 `idle_yawn`；空字符串由现有调度器选择，不连续重复 |
| `set_attention(enabled, mouse_position)` | 平滑注意鼠标；离开时返回 Idle |
| `notify_click(mouse_position)` | 按当前部位及时间窗口累积点击；升级疑问、不满和部位防护 |
| `start_drag(mouse_position)` | 暂时释放脚底固定并进入提起动作 |
| `update_drag(mouse_position)` | 更新拖拽目标；原有弹性和速度限幅继续生效 |
| `end_drag()` | 落地缓冲后恢复脚底固定 |
| `set_working(enabled)` | 进入无限工作循环；退出时播放 0.4 秒恢复动作 |
| `notify_success()` | 1.3 秒成功庆祝；Working → Success → Idle |
| `notify_error()` | 1.4 秒错误反馈；Working → Error → Idle |
| `request_idle()` | 请求安全返回 Idle；正在落地或反馈时允许动作正常结束 |

`rest_pose()` 仅用于验收静止姿势，它会停止眨眼计时，不作为宿主的日常 Idle 请求。日常请使用 `request_idle()`。

鼠标位置均为 **全局画布坐标**，而非原图局部坐标。例如测试点可通过 `pet.rig.to_global(Vector2(700,1650))` 转换。PySide 等宿主应先转换自己的屏幕坐标；本工程不包含跨进程传输协议。

## 信号

- `state_changed(previous_state, current_state)`：状态切换。
- `animation_started(animation_name)`：动作开始，包含独立 Blink。
- `animation_finished(animation_name)`：动作结束，包含独立 Blink。

## 优先级与混合

从高到低：Drag / Land 100 → Feedback 80 → Working 60 → Click 40 → Attention 20 → Idle Variant 10 → Idle 0。

低优先级请求不会重启高优先级动作。头发、呆毛和披风继续叠加；眨眼独立运行，哈欠等强制闭眼表情优先显示。同侧 open / closed 互斥。

正常站立固定脚底。Drag 和 Success 起跳暂时释放固定；落地后恢复。动画输入通过各控制器限幅，不应直接覆写骨骼以绕过原有安全边界。
