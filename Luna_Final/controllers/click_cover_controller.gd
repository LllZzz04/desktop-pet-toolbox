extends Node2D
## Three temporary arm poses. Original textures, UVs and Working are untouched.
const Pose=preload("res://controllers/click_cover_arm_pose.gd")
var arm_pose: Node2D
var target_native: Vector2=Vector2(600,650)
var last_region: String=""
var amount: float=0.0
@onready var pet: Node2D=get_parent()
func _ready() -> void:
	arm_pose=Node2D.new();arm_pose.name="ClickCoverArmPose";arm_pose.set_script(Pose);add_child(arm_pose)
func configure(region: String,world_point: Vector2) -> void:
	last_region=region;target_native=pet.rig.to_local(world_point)
func apply(values: Dictionary) -> void:
	var region: String="head"
	amount=0.0
	for candidate in ["head","chest","legs"]:
		var value: float=clampf(values.get("cover_"+candidate,0.0),0.0,1.0)
		if value>amount:region=candidate;amount=value
	# A higher priority Working takeover smoothly replaces this overlay.
	amount*=1.0-clampf(values.working_fold,0.0,1.0)
	arm_pose.region=region;arm_pose.click_point=target_native
	arm_pose.apply(amount,values,null)
func reset() -> void:
	amount=0.0;last_region="";arm_pose.hide_pose()
