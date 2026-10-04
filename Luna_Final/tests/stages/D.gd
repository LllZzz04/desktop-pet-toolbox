extends RefCounted
func run(t: SceneTree) -> void:
	var original: Array[Vector2]=t.feet()
	t.pet.set_working(true);t.advance(.5)
	t.check(t.pet.states.current_name=="working","working API")
	t.check(t.pet.motion.output.glasses==1.0 and t.pet.motion.output.panel==1.0,"working props")
	t.check(is_equal_approx(t.pet.motion.output.breathing_strength,.22),"weak breathing")
	t.pet.notify_click(Vector2(700,600));t.pet.set_attention(true,Vector2(900,600))
	t.check(t.pet.states.current_name=="working","working suppresses click/attention")
	t.check(not t.pet.play_idle_variant(),"working suppresses variants")
	t.pet.rig.blink_player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	t.pet.rig.blink_once();t.pet.rig.blink_player.advance(.06);t.pet.expressions.apply(t.pet.motion.output)
	t.check(t.pet.rig.eyes_closed and t.pet.rig.eye_states_valid(),"working blink closes exclusively")
	t.pet.rig.blink_player.advance(.14);t.pet.expressions.apply(t.pet.motion.output)
	t.check(not t.pet.rig.eyes_closed,"working blink reopens")
	t.advance(6.4)
	t.check(t.pet.states.current_name=="working" and t.feet()==original,"indefinite work loop with fixed feet")
	t.pet.set_working(false);t.advance(.6)
	t.check(t.pet.states.current_name=="idle","working exit completes")
	t.check(t.pet.motion.output.glasses==0.0 and t.pet.motion.output.panel==0.0,"props leave without modifying rig")
	t.check(t.feet()==original,"working/exiting foot lock")
	t.metrics.working_foot_drift_px=0.0
	t.metrics.blink_compatible=true
