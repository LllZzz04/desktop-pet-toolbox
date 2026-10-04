extends RefCounted
func reset(t: SceneTree) -> void:
	t.pet.set_attention(false,Vector2.ZERO);t.pet.request_idle();t.advance(1.8)
	var interaction: Node=t.pet.get_node("InteractionController")
	interaction.click_times.clear();interaction.angry_cooldown_until=0.0
func run(t: SceneTree) -> void:
	var started: Array[String]=[]
	var finished: Array[String]=[]
	var changed: Array[String]=[]
	t.pet.animation_started.connect(func(animation: String):started.append(animation))
	t.pet.animation_finished.connect(func(animation: String):finished.append(animation))
	t.pet.state_changed.connect(func(previous: String,current: String):changed.append(previous+" -> "+current))
	# Full priority chain. Lower-priority requests leave both state and clock intact.
	t.pet.set_attention(true,Vector2(1450,650));t.advance(.3)
	t.pet.notify_click(Vector2(1200,650));t.advance(.1)
	t.check(t.pet.states.current_name=="click","click > attention")
	t.pet.set_attention(true,Vector2(200,650));t.check(t.pet.states.current_name=="click","attention cannot interrupt click")
	t.pet.set_working(true);t.advance(.2);t.check(t.pet.states.current_name=="working","working > click")
	t.pet.notify_success();t.advance(.1);t.check(t.pet.states.current_name=="feedback","feedback > working")
	t.pet.set_working(true);t.check(t.pet.states.current_name=="feedback","working cannot interrupt feedback")
	t.pet.start_drag(Vector2(768,1000));t.advance(.4);t.check(t.pet.states.current_name=="drag_hold","drag > feedback")
	for i in range(20):
		t.pet.update_drag(Vector2(768+sin(i*1.2)*1500,800))
		t.advance(1.0/60.0)
		t.check(absf(t.pet.motion.output.rig_angle)<=5.0001,"fast drag bound")
	t.pet.notify_error();t.pet.set_working(true);t.pet.notify_click(Vector2.ZERO);t.pet.set_attention(true,Vector2.ZERO)
	t.check(t.pet.states.current_name=="drag_hold","drag suppresses all lower APIs")
	t.pet.end_drag();t.advance(1.2)
	t.check(t.pet.states.current_name=="idle" and t.pet.foot_lock.locked,"drag lands to normal idle")
	reset(t)
	# Forced yawn closure is composed after independent blink updates.
	t.pet.play_idle_variant("idle_yawn");t.advance(1.2)
	t.pet.rig.blink_once();t.pet.rig.blink_player.advance(.14)
	t.pet.step(0)
	t.check(not t.pet.rig.eyes_closed,"independent blink reopened its own channel")
	t.check(t.pet.rig.layers.eye_L_closed.visible and t.pet.rig.layers.eye_R_closed.visible,"yawn still forces closed eyes")
	t.check(t.pet.rig.eye_states_valid(),"forced expression exclusivity")
	t.advance(3.2);t.check(t.pet.states.current_name=="idle","yawn exit after forced closure")
	# A normal attention -> idle transition does not reset the base clock.
	t.pet.set_attention(true,Vector2(1450,600));t.advance(.6)
	var clock_before: float=t.pet.base_time
	var max_step: float=0.0
	var last: float=t.pet.rig.bones.head.rotation_degrees
	t.pet.set_attention(false,Vector2.ZERO)
	for i in range(30):
		t.advance(1.0/60.0)
		var angle: float=t.pet.rig.bones.head.rotation_degrees
		max_step=maxf(max_step,absf(angle-last));last=angle
	t.check(max_step<.35,"attention return has no rotation pop")
	t.check(is_equal_approx(t.pet.base_time-clock_before,.5),"base idle clock continues across states")
	t.metrics.attention_exit_max_step_degrees=max_step
	# Cooldown, spacing and random scheduling are independent of motion clips.
	for i in range(100):
		t.pet.states.schedule_variant()
		t.check(t.pet.states.variant_remaining>=12 and t.pet.states.variant_remaining<=30,"variant timer range")
	# All required reusable API methods and signals exist.
	for method in ["play_idle_variant","set_attention","notify_click","start_drag","update_drag","end_drag","set_working","notify_success","notify_error"]:
		t.check(t.pet.has_method(method),"API "+method)
	for signal_name in ["state_changed","animation_started","animation_finished"]:t.check(t.pet.has_signal(signal_name),"signal "+signal_name)
	t.check(started.has("idle_yawn") and finished.has("idle_yawn") and changed.size()>6,"lifecycle signals")
	t.metrics.signal_started=started;t.metrics.signal_finished=finished;t.metrics.signal_state_changed=changed
	# Full real test-scene controls, called via their numeric action handlers.
	var scene: Node2D=load("res://LunaFinalTest.tscn").instantiate()
	scene.get_node("LunaPet").automatic_processing=false;scene.get_node("LunaPet").random_events_enabled=false
	t.root.add_child(scene)
	scene.pet.get_node("InteractionController").mouse_input_enabled=false
	for key in [2,3,4,5,6,7,8,9,0,1]:
		scene.pet.request_idle()
		for i in range(120):scene.pet.step(1.0/60.0)
		scene.trigger(key);scene._process(1.0/60.0);scene.pet.step(1.0/60.0)
		var expected: Dictionary={2:"idle_variant",3:"idle_variant",4:"attention",5:"click",6:"click",7:"drag_start",8:"working",9:"feedback",0:"feedback",1:"idle"}
		t.check(scene.pet.states.current_name==expected[key],"test scene key "+str(key))
		scene.attention_test_until=0;scene.pet.set_attention(false,Vector2.ZERO)
		if key==7:scene.pet.end_drag();scene.drag_test_time=-1
		scene.pet.get_node("InteractionController").click_times.clear();scene.pet.get_node("InteractionController").angry_cooldown_until=0
	scene.queue_free()
	t.metrics.test_scene_numeric_actions=10
