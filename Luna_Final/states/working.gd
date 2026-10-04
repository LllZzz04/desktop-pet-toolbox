extends "res://states/base.gd"
var exiting: bool=false
func enter(payload: Dictionary) -> void:
	super.enter(payload);exiting=bool(payload.get("exit",false))
	pet.motion.play("working_exit" if exiting else "working_loop",0.08 if exiting else 0.3)
func update(delta: float) -> void:
	super.update(delta)
	if exiting and elapsed>=0.4:
		pet.animation_finished.emit("working_exit");pet.states.return_to_idle()
