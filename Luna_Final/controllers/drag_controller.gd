extends Node
var cursor: Vector2
var previous_cursor: Vector2
var grab_offset: Vector2
var velocity: Vector2=Vector2.ZERO
var mouse_velocity: Vector2=Vector2.ZERO
var ground_y: float=0.0
var land_start: Vector2
var landing_x: float=0.0
var land_lift: float=0.0
var land_angle: float=0.0
var sway: float=0.0
@onready var pet: Node2D=get_parent()
func start_drag(position: Vector2) -> void:
	if pet.states.current_name in ["drag_start","drag_hold","land"]:return
	cursor=position;previous_cursor=position;grab_offset=position-pet.global_position
	ground_y=pet.global_position.y;velocity=Vector2.ZERO;mouse_velocity=Vector2.ZERO;sway=0.0
	pet.foot_lock.release();pet.states.request("drag_start",{},true)
func update_drag(position: Vector2) -> void:cursor=position
func end_drag() -> void:
	if pet.states.current_name not in ["drag_start","drag_hold"]:return
	land_start=pet.global_position;land_lift=pet.motion.output.root_y;land_angle=pet.motion.output.rig_angle
	landing_x=cursor.x-grab_offset.x
	velocity=Vector2.ZERO;pet.states.request("land",{},true)
func suspended(delta: float) -> void:
	var desired: Vector2=cursor-grab_offset
	desired.y=minf(desired.y,ground_y-8.0*absf(pet.global_scale.y))
	var remaining: float=delta
	while remaining>0.000001:
		var step: float=minf(remaining,1.0/120.0)
		velocity+=((desired-pet.global_position)*121.0-velocity*22.0)*step
		pet.global_position+=velocity*step;remaining-=step
	var measured: Vector2=(cursor-previous_cursor)/maxf(delta,0.0001)
	previous_cursor=cursor
	mouse_velocity=mouse_velocity.lerp(measured.limit_length(900.0),1.0-exp(-delta*8.0))
	var target: float=clampf(mouse_velocity.x*0.009,-5.0,5.0)
	sway=lerpf(sway,target,1.0-exp(-delta*7.0))
	pet.motion.overrides={"rig_angle":sway,"head_angle":-sway*0.35,
		"hair_side_L":-sway*0.14,"hair_side_R":-sway*0.13,
		"hair_tip_L":-sway*0.22,"hair_tip_R":-sway*0.2,
		"cape_tail_L":-sway*0.22,"cape_tail_R":-sway*0.20,
		"cape_upper_L":-sway*0.07,"cape_upper_R":-sway*0.07,
		"ahoge":-sway*0.12,"ahoge_tip":-sway*0.22,
		"hip_L":sway*0.08,"hip_R":sway*0.07,"foot_L":sway*0.12,"foot_R":sway*0.1,
		"forearm_L":-sway*0.30,"forearm_R":-sway*0.27,"hand_L":-sway*0.4,"hand_R":-sway*0.35}
func landing(time: float) -> void:
	var progress: float=clampf(time/0.35,0.0,1.0)
	var weight: float=smoothstep(0.0,1.0,progress)
	pet.global_position=Vector2(landing_x if progress>=1.0 else lerpf(land_start.x,landing_x,weight),ground_y if progress>=1.0 else lerpf(land_start.y,ground_y,weight))
	pet.motion.overrides={"root_y":land_lift*(1.0-weight),"rig_angle":land_angle*(1.0-weight)}
	if progress>=1.0 and not pet.foot_lock.locked:pet.foot_lock.request_restore()
