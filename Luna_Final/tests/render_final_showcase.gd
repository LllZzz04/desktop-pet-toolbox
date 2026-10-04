extends SceneTree
var viewport: SubViewport
var scene: Node2D
var pet: Node2D
var frames: Array=[]
const FPS: int=20
const FRAME_COUNT: int=888
func _initialize() -> void:call_deferred("run")
func capture(path: String) -> bool:
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image().save_png(path)==OK
func run() -> void:
	if DisplayServer.get_name()=="headless":quit(1);return
	viewport=SubViewport.new();viewport.size=Vector2i(960,800);viewport.transparent_bg=false
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	scene=load("res://LunaFinalTest.tscn").instantiate()
	scene.get_node("LunaPet").automatic_processing=false;scene.get_node("LunaPet").random_events_enabled=false
	viewport.add_child(scene);scene.set_process(false);pet=scene.pet
	scene.start_demo();scene.demo_time=0.0
	DirAccess.make_dir_recursive_absolute("res://preview/raw_final_showcase")
	var exclusive: bool=true
	var unique_clips: Array[String]=[]
	var max_locked_foot_drift: float=0.0
	for index in range(FRAME_COUNT):
		var delta: float=1.0/FPS
		scene._process(delta);pet.step(delta)
		# Fixed blink timing makes the exported demonstration reproducible.
		# The running project keeps the approved independent random Blink timer.
		if index in [56,116,198,260,320,400,478,570,634,730,824]:pet.rig.blink_once()
		if not await capture("res://preview/raw_final_showcase/frame_%04d.png"%index):quit(1);return
		var clip: String="idle_normal" if pet.motion.clip.is_empty() else pet.motion.clip
		if not unique_clips.has(clip):unique_clips.append(clip)
		exclusive=exclusive and pet.rig.eye_states_valid()
		if pet.foot_lock.locked:max_locked_foot_drift=maxf(max_locked_foot_drift,pet.foot_lock.maximum_drift())
		frames.append({"time":(index+1.0)/FPS,"state":pet.states.current_name,"clip":clip,"foot_locked":pet.foot_lock.locked})
		if index%100==0:print("FINAL_SHOWCASE_FRAME ",index,"/",FRAME_COUNT)
	var required: Array[String]=["idle_normal","idle_look_around","idle_yawn","click_question","click_annoyed","click_angry_head","click_angry_chest","click_angry_legs","drag_start","drag_hold","land","working_loop","feedback_success","feedback_error"]
	var missing: Array[String]=[]
	for clip in required:
		if not unique_clips.has(clip):missing.append(clip)
	# Independently verify the real-time random Blink timer in the final project.
	scene.stop_demo();scene.attention_test_until=0;scene.drag_test_time=-1;scene.set_process(false)
	pet.set_attention(false,Vector2.ZERO);pet.request_idle()
	for i in range(90):pet.step(1.0/60.0)
	pet.automatic_processing=true;pet.random_events_enabled=false
	pet.get_node("InteractionController").mouse_input_enabled=false
	pet.rig.random_blink_enabled=true;pet.rig._schedule_blink()
	var begin: int=Time.get_ticks_msec()
	var blinks: int=0;var was_closed: bool=false;var live_frames: int=0
	while Time.get_ticks_msec()-begin<8000:
		await process_frame;live_frames+=1
		if pet.rig.eyes_closed and not was_closed:blinks+=1
		was_closed=pet.rig.eyes_closed
		exclusive=exclusive and pet.rig.eye_states_valid()
		if pet.foot_lock.locked:max_locked_foot_drift=maxf(max_locked_foot_drift,pet.foot_lock.maximum_drift())
	var passed: bool=missing.is_empty() and exclusive and max_locked_foot_drift==0.0 and blinks>=1
	var report: Dictionary={"pass":passed,"real_gpu":true,"renderer":RenderingServer.get_video_adapter_name(),"fps":FPS,"frames":FRAME_COUNT,"duration":44.4,"size":[960,800],"unique_clips":unique_clips,"missing_clips":missing,"eyes_exclusive":exclusive,"maximum_locked_foot_drift_px":max_locked_foot_drift,"live_random_blink":{"seconds":8,"frames":live_frames,"blinks":blinks,"intervals":pet.rig.blink_intervals},"timeline":frames}
	FileAccess.open("res://data/final_showcase_validation.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("FINAL_SHOWCASE_COMPLETE pass=",passed," clips=",unique_clips);quit(0 if passed else 1)
