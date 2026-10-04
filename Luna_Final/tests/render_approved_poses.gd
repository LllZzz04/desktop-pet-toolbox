extends SceneTree
var viewport: SubViewport
var pet: Node2D
var paths: Array[String]=[]
func _initialize() -> void:call_deferred("run")
func make_pet() -> void:
	pet=load("res://LunaPet.tscn").instantiate();pet.automatic_processing=false;pet.random_events_enabled=false
	viewport.add_child(pet);pet.get_node("InteractionController").mouse_input_enabled=false
func capture(name: String) -> void:
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var path: String="res://preview/regression/"+name
	if viewport.get_texture().get_image().save_png(path)!=OK:quit(1);return
	paths.append(path)
func advance(seconds: float) -> void:
	var count: int=maxi(1,int(ceil(seconds*120.0)))
	for i in range(count):pet.step(seconds/count)
func run() -> void:
	if DisplayServer.get_name()=="headless":quit(1);return
	viewport=SubViewport.new();viewport.size=Vector2i(1536,2304);viewport.transparent_bg=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	DirAccess.make_dir_recursive_absolute("res://preview/regression")
	make_pet();pet.rest_pose();await capture("rest_pose_gpu.png")
	for i in [0,48,96,144,192]:
		pet.motion.reset();pet.composer.apply(pet.motion.output,i/30.0)
		await capture("normal_%03d_gpu.png"%i)
	pet.set_working(true)
	for i in range(30):pet.step(1.0/60.0)
	# Same sampling recipe as the approved runtime panel-order screenshot.
	for i in range(9):
		for layer in pet.rig.layers.values():layer.visible=true
		pet.motion.play("working_loop",0);pet.motion.blend_clock=1.0
		pet.motion.advance(maxf(i*.4,0.00001));pet.composer.apply(pet.motion.output,i*.4)
	for layer in pet.rig.layers.values():layer.visible=true
	pet.motion.play("working_loop",0);pet.motion.blend_clock=1.0;pet.motion.advance(1.3);pet.composer.apply(pet.motion.output,1.3)
	await capture("working_panel_front_native.png")
	pet.queue_free();await process_frame;make_pet();pet.rest_pose()
	var targets: Dictionary={"head":Vector2(600,650),"chest":Vector2(772,1070),"legs":Vector2(700,1650)}
	for region in ["head","chest","legs"]:
		pet.request_idle();pet.clock+=3.0;pet.rig.eyes_closed=false
		for j in range(40):pet.step(.05)
		for i in range(76):
			if i in [10,12,14,16,18,20]:pet.notify_click(pet.rig.to_global(targets[region]))
			if i==30:pet.rig.blink_once()
			pet.step(.05)
			if i==34:await capture("angry_cover_%s.png"%region)
	pet.queue_free();await process_frame;make_pet();advance(.5);pet.notify_success();advance(.44)
	await capture("success_pose_apex.png")
	print("FINAL_APPROVED_POSES_COMPLETE ",paths.size());quit()
