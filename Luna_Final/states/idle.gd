extends "res://states/base.gd"
var animation: String=""
func enter(payload: Dictionary) -> void:
	super.enter(payload)
	animation=String(payload.get("animation","")) if name=="idle_variant" else ""
	pet.motion.play(animation,float(payload.get("transition",0.2)))
func update(delta: float) -> void:
	super.update(delta)
	if name=="idle_variant" and elapsed>=pet.motion.length():
		pet.animation_finished.emit(animation)
		if animation=="idle_yawn":pet.rig.blink_once()
		pet.states.return_to_idle()
