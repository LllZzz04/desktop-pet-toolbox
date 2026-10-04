extends "res://states/base.gd"
var animation: String="click_question"
var bias: float=0.0
func enter(payload: Dictionary) -> void:
	super.enter(payload);animation=payload.animation
	var native: Vector2=pet.to_local(payload.mouse)
	bias=clampf((native.x-772.0)/500.0,-1.0,1.0)*0.4
	if animation.begins_with("click_angry_"):
		pet.get_node("ClickCoverController").configure(payload.get("region","head"),payload.mouse)
	pet.motion.play(animation,0.1)
func update(delta: float) -> void:
	super.update(delta)
	var envelope: float=sin(PI*clampf(elapsed/pet.motion.length(),0.0,1.0))
	pet.motion.overrides={"head_angle":bias*envelope}
	if elapsed>=pet.motion.length():
		pet.animation_finished.emit(animation);pet.states.return_to_idle()
