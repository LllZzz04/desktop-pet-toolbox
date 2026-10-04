# 源素材与运行时素材

正式全画布素材共 34 层，均为 1536×2304。素材由 Phase2 的完整正式图层加已确认的六个 Phase3.6 脸部修复层组成，没有新绘制或重新生成。

`source/Luna_Idle_Aligned.psd` 是保留的原始 PSD，字节不变。后续眼睛、嘴部修复及专用手势等没有回写到这份历史 PSD。当前正式全画布素材在 `layers/`；新增局部姿势和表情在 `assets/`。

`runtime_layers/` 是实际工程使用的已确认运行时贴图，全部字节沿用 Phase4.17。保留原裁剪、透明 padding、世界位置和透明边缘颜色处理，不重新裁剪、缩放、镜像或旋转。

`data/runtime_manifest.json` 保存每层 crop_rect、source_size、runtime_size、world_origin、pivot、draw_order 和 parent_bone；只更新源素材路径及最终绑定说明。`data/layer_manifest.json` 更新了当前正式层的文件路径、内容边界和哈希。

| 分组 | 完整图层名称 |
|---|---|
| Head · 6 层 | face_base、mouth、eye_R_open、eye_R_closed、eye_L_open、eye_L_closed |
| Hair · 9 层 | back_hair、hair_tip_R、hair_tip_L、side_hair_R、side_hair_L、bang_R、bang_L、bang_center、ahoge |
| Cape · 5 层 | cape_R_tail、cape_L_tail、cape_R_upper、cape_L_upper、cape_neck |
| Body · 8 层 | leg_L、leg_R、skirt、torso、arm_R、arm_L、hand_R、hand_L |
| Accessory · 6 层 | tail_charm_R、tail_charm_L、cape_charm_R、cape_charm_L、hair_accessory、neck_accessory |

绘制顺序请读 layer_manifest 和 draw_order。

实际绑定以 `LunaRig.tscn` 为准：双腿及指定头发、披风采用 Polygon2D；其余先用 Sprite2D。专用 Working 和防护姿势通过局部袖臂覆盖方案衔接，不改动基础 Idle。

脚底区域保持 100% foot 权重；眨眼层互斥。旧版本、旧预览和原始阶段报告保留在工作区历史目录，不混入最终版常用入口。
