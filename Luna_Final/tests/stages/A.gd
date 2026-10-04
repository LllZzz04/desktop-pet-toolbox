extends RefCounted
func run(t: SceneTree) -> void:
	var initial: Array[Vector2]=t.feet()
	var max_drift: float=0.0
	for animation in ["idle_look_around","idle_yawn"]:
		t.check(t.pet.play_idle_variant(animation),"variant API "+animation)
		var total: float=float(t.pet.motion.catalog[animation].length)+0.4
		var count: int=int(total*60)
		for i in range(count):
			t.advance(1.0/60.0,i%4==0)
			var feet: Array[Vector2]=t.feet()
			max_drift=maxf(max_drift,maxf(feet[0].distance_to(initial[0]),feet[1].distance_to(initial[1])))
			if t.pet.states.current_name=="idle_variant":t.check(absf(t.pet.rig.bones.head.rotation_degrees)<=2.0001,"look/yawn head limit")
		t.check(t.pet.states.current_name=="idle","variant returns to idle")
		t.pet.rig.blink_player.stop();t.pet.rig.eyes_closed=false
	for i in range(4):
		t.pet.play_idle_variant();t.advance(4.9)
	var history: Array=t.pet.states.variant_history
	for i in range(3,history.size()):t.check(history[i]!=history[i-1],"random variants do not repeat")
	t.check(max_drift==0.0,"variants retain exact foot lock")
	t.metrics.variants_foot_drift_px=max_drift
	t.metrics.variant_history=history
	t.check(t.pet.expressions.additions.has("mouth_yawn"),"local yawn material loaded")
