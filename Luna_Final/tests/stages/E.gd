extends RefCounted
func run(t: SceneTree) -> void:
	var original: Array[Vector2]=t.feet()
	t.pet.set_working(true);t.advance(.5);t.pet.notify_success()
	t.check(t.pet.states.current_name=="feedback","success overrides working")
	var lift: float=0.0
	for i in range(90):
		t.advance(1.0/60.0)
		lift=maxf(lift,original[0].y-t.feet()[0].y)
	t.check(lift>=21.99 and lift<=22.01,"22px success celebration jump")
	t.check(t.feet()==original and t.pet.foot_lock.locked,"success restores exact ground feet")
	t.check(t.pet.states.current_name=="idle","working-success-idle")
	t.pet.set_working(true);t.advance(.5);t.pet.notify_error();t.advance(1.8)
	t.check(t.pet.states.current_name=="idle","working-error-idle")
	t.check(t.feet()==original,"error keeps feet locked")
	t.check(t.pet.motion.output.glasses==0 and t.pet.motion.output.panel==0,"feedback dismisses work props")
	t.metrics.success_lift_px=lift;t.metrics.success_final_foot_drift_px=0.0
