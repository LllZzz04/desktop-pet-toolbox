extends RefCounted
func run(t: SceneTree) -> void:
	t.pet.start_drag(Vector2(768,1000));t.check(not t.pet.foot_lock.locked,"drag releases lock")
	t.pet.update_drag(Vector2(970,840));t.advance(.4)
	t.check(t.pet.states.current_name=="drag_hold","start then hold")
	t.check(t.pet.global_position.y<0,"picked up")
	var max_angle: float=0.0
	for i in range(60):
		t.pet.update_drag(Vector2(970+sin(i*.3)*300,840+cos(i*.2)*80))
		t.advance(1.0/60.0)
		max_angle=maxf(max_angle,absf(t.pet.motion.output.rig_angle))
	t.check(max_angle<=5.0001,"bounded spring sway")
	t.pet.notify_success();t.check(t.pet.states.current_name=="drag_hold","drag suppresses feedback")
	t.pet.end_drag();t.check(t.pet.states.current_name=="land","release plays land")
	t.advance(.4)
	t.check(t.pet.foot_lock.locked,"lock restored at contact")
	var contact: Array[Vector2]=t.feet()
	var max_drift: float=0.0
	for i in range(90):
		t.advance(1.0/60.0)
		var p: Array[Vector2]=t.feet()
		max_drift=maxf(max_drift,maxf(p[0].distance_to(contact[0]),p[1].distance_to(contact[1])))
	t.check(max_drift==0.0,"feet fixed after contact")
	t.check(contact[0].y==2095.0 and contact[1].y==2095.0,"ground foot pivots restored")
	t.check(t.pet.states.current_name=="idle","land returns to idle")
	# Release during the pickup animation is also supported.
	t.pet.start_drag(Vector2(768,1000));t.advance(.05);t.pet.end_drag();t.advance(1.2)
	t.check(t.pet.foot_lock.locked and t.pet.states.current_name=="idle","early release is safe")
	t.metrics.drag_body_max_degrees=max_angle
	t.metrics.post_contact_foot_drift_px=max_drift
