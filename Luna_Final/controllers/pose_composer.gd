extends Node
@onready var pet: Node2D=get_parent()
@onready var rig: Node2D=$"../Rig"
func _ready() -> void:
	# Runtime alias only. The packed Phase3.7 rig and original curves stay intact.
	rig.idle_player.get_animation_library("").add_animation("idle_normal",load("res://animations/idle/idle_normal.tres"))
func apply(values: Dictionary,time: float) -> void:
	for bone in rig.bones.values():bone.transform=bone.rest
	rig.idle_player.play("idle_normal");rig.idle_player.seek(fposmod(time,6.4),true);rig.idle_player.pause()
	var strength: float=clampf(values.breathing_strength,0.0,1.0)
	var chest: Bone2D=rig.bones.chest
	chest.position.y=lerpf(chest.rest.origin.y,chest.position.y,strength)
	chest.scale.y=lerpf(1.0,chest.scale.y,strength)
	rig.bones.head.position.y+=values.head_y
	chest.position.y+=values.chest_y
	rig.bones.pelvis.position+=Vector2(values.pelvis_x,values.pelvis_y)
	var mapping: Dictionary={"head":"head_angle","chest":"chest_angle","ahoge_root":"ahoge",
		"ahoge_tip":"ahoge_tip","hair_side_L":"hair_side_L","hair_side_R":"hair_side_R",
		"hair_tip_L":"hair_tip_L","hair_tip_R":"hair_tip_R","cape_L_root":"cape_upper_L",
		"cape_R_root":"cape_upper_R","cape_L_mid":"cape_tail_L","cape_R_mid":"cape_tail_R"}
	for name in ["shoulder_L","shoulder_R","forearm_L","forearm_R","hand_L","hand_R","hip_L","hip_R","knee_L","knee_R","foot_L","foot_R"]:mapping[name]=name
	for name in mapping:rig.bones[name].rotation+=deg_to_rad(values[mapping[name]])
	# A shallow frontal crouch: pelvis lowers, knees yield inward, shoes stay locked.
	# Use a blended channel so higher-priority takeovers recover without a pose pop.
	var crouch: float=clampf(values.get("leg_crouch",0.0),0.0,1.0)
	if crouch>0.0:
		for side in ["L","R"]:
			rig.bones["knee_"+side].position+=Vector2(-10.0 if side=="L" else 10.0,-16.0)*crouch
	for side in ["L","R"]:
		var elbow: Bone2D=rig.bones["forearm_"+side]
		elbow.rotation=clampf(elbow.rotation,-deg_to_rad(52.0),deg_to_rad(52.0))
		var bent: bool=absf(elbow.rotation)>0.00001
		rig.layers["arm_"+side].visible=not bent
		rig.layers["arm_"+side+"_deform"].visible=bent
	rig.bones.hand_L.position.x+=values.hand_L_x
	rig.bones.hand_R.position.x+=values.hand_R_x
	# Bounds apply only to overlay states; idle_normal retains every original value.
	if pet.states.current_name!="idle" or absf(values.head_angle)>0.00001:
		var head_limit: float=2.0 if pet.states.current_name=="idle_variant" else 3.0
		rig.bones.head.rotation=clampf(rig.bones.head.rotation,-deg_to_rad(head_limit),deg_to_rad(head_limit))
	for name in ["cape_L_root","cape_R_root","cape_L_mid","cape_R_mid"]:
		rig.bones[name].rotation=clampf(rig.bones[name].rotation,-deg_to_rad(4.7),deg_to_rad(4.7))
	# Success adds delayed offsets within the already tested hair / ahoge bounds.
	if pet.motion.clip=="feedback_success":
		for name in ["hair_side_L","hair_side_R","hair_tip_L","hair_tip_R"]:
			rig.bones[name].rotation=clampf(rig.bones[name].rotation,-deg_to_rad(2.0),deg_to_rad(2.0))
		rig.bones.ahoge_root.rotation=clampf(rig.bones.ahoge_root.rotation,-deg_to_rad(3.0),deg_to_rad(3.0))
		rig.bones.ahoge_tip.rotation=clampf(rig.bones.ahoge_tip.rotation,-deg_to_rad(6.0),deg_to_rad(6.0))
	var angle: float=deg_to_rad(clampf(values.rig_angle,-5.0,5.0))
	var pivot:=Vector2(768,1100)
	rig.rotation=angle;rig.position=pivot-pivot.rotated(angle)+Vector2(0,values.root_y)
	pet.expressions.apply(values)
	if pet.has_node("EffectLayer"):pet.get_node("EffectLayer").apply(values)
	if pet.has_node("WritingController"):pet.get_node("WritingController").apply(values,pet.motion.clock)
	if pet.has_node("ClickCoverController"):pet.get_node("ClickCoverController").apply(values)
