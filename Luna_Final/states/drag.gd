extends "res://states/base.gd"
func enter(payload: Dictionary) -> void:
	super.enter(payload)
	pet.motion.play(name,0.1 if name=="land" else (0.12 if name=="drag_start" else 0.08))
func update(delta: float) -> void:
	super.update(delta)
	var drag: Node=pet.get_node("DragController")
	if name=="land":
		drag.landing(elapsed)
		if elapsed>=0.85:
			pet.animation_finished.emit("land");pet.states.return_to_idle()
	else:
		drag.suspended(delta)
		if name=="drag_start" and elapsed>=0.28:
			pet.animation_finished.emit("drag_start");pet.states.request("drag_hold",{},true)
