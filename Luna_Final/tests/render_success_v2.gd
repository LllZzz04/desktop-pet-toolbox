extends SceneTree
var viewport: SubViewport
var pet: Node2D
var records: Dictionary={}
const POSES: Dictionary={"charge":0.12,"takeoff":0.28,"apex":0.44,"landing":0.67,"proud_nod":1.02}
func _initialize() -> void:call_deferred("run")
func make_pet() -> Node2D:
	var result: Node2D=load("res://LunaPet.tscn").instantiate()
	result.automatic_processing=false;result.random_events_enabled=false;viewport.add_child(result)
	result.get_node("InteractionController").mouse_input_enabled=false
	return result
func advance(seconds: float) -> void:
	var count: int=maxi(1,int(ceil(seconds*120.0)))
	for i in range(count):pet.step(seconds/count)
func capture(path: String) -> void:
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	if viewport.get_texture().get_image().save_png(path)!=OK:
		printerr("Capture failed: ",path);quit(1)
func snapshot() -> Dictionary:
	var feet: Dictionary={}
	for side in ["L","R"]:
		var p: Vector2=pet.rig.bones["foot_"+side].global_position
		feet[side]=[p.x,p.y]
	return {"state":pet.states.current_name,"clip":pet.motion.clip,"channels":pet.motion.output.duplicate(),"feet":feet,"foot_locked":pet.foot_lock.locked}
func run() -> void:
	if DisplayServer.get_name()=="headless":quit(1);return
	viewport=SubViewport.new();viewport.size=Vector2i(1536,2304);viewport.transparent_bg=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	DirAccess.make_dir_recursive_absolute("res://preview/raw_success_v2")
	pet=make_pet();pet.step(0.0)
	for frame in range(193):
		if frame>0:pet.step(1.0/30.0)
		if frame==15:pet.notify_success()
		if frame==108:pet.rig.blink_once()
		await capture("res://preview/raw_success_v2/frame_%03d.png"%frame)
		if frame==0 or frame==192:records["loop_frame_"+str(frame)]=snapshot()
	pet.queue_free();await process_frame
	var keyposes: Dictionary={}
	for name in POSES:
		pet=make_pet();advance(.5);pet.notify_success();advance(POSES[name])
		await capture("res://preview/success_pose_%s.png"%name)
		keyposes[name]=snapshot();keyposes[name].time=POSES[name]
		pet.queue_free();await process_frame
	pet=make_pet();pet.set_working(true);advance(1.2);pet.notify_success();advance(.44)
	await capture("res://preview/success_from_working_apex.png")
	records.working_apex=snapshot()
	records.keyposes=keyposes;records.frame_rate=30;records.frames=192;records.preview_seconds=6.4
	records.success_start_seconds=.5;records.animation_seconds=1.3;records.canvas=[1536,2304]
	FileAccess.open("res://data/success_v2_capture.json",FileAccess.WRITE).store_string(JSON.stringify(records,"\t"))
	print("SUCCESS_V2_GPU_COMPLETE");quit()
