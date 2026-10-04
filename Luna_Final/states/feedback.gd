extends "res://states/base.gd"
var animation: String="feedback_success"
func enter(payload: Dictionary) -> void:
	super.enter(payload);animation=payload.animation
	pet.motion.play(animation,0.08 if animation=="feedback_success" else 0.12)
func update(delta: float) -> void:
	super.update(delta)
	if animation=="feedback_success":
		if elapsed>=0.15 and elapsed<0.65 and pet.foot_lock.locked:pet.foot_lock.release()
		if elapsed>=0.65 and not pet.foot_lock.locked:pet.foot_lock.request_restore()
	if elapsed>=pet.motion.length():
		pet.animation_finished.emit(animation);pet.states.return_to_idle()
