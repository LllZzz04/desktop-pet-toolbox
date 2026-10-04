extends SceneTree
var viewport: SubViewport
var pet: Node2D
var records: Array=[]
const TARGETS := {"head":Vector2(600,650),"chest":Vector2(772,1070),"legs":Vector2(700,1650)}
func _initialize() -> void:call_deferred("run")
func capture(path: String) -> void:
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	assert(viewport.get_texture().get_image().save_png(path)==OK)
func run() -> void:
	if DisplayServer.get_name()=="headless":quit(1);return
	viewport=SubViewport.new();viewport.size=Vector2i(1536,2304);viewport.transparent_bg=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	pet=load("res://LunaPet.tscn").instantiate();pet.automatic_processing=false;pet.random_events_enabled=false;viewport.add_child(pet)
	pet.get_node("InteractionController").mouse_input_enabled=false
	DirAccess.make_dir_recursive_absolute("res://preview/raw_click_cover")
	pet.rest_pose();await capture("res://preview/click_cover_rest.png")
	var regions: Array=["head","chest","legs"]
	if not OS.get_cmdline_user_args().is_empty():regions=[String(OS.get_cmdline_user_args()[0])]
	for region in regions:
		pet.request_idle();pet.clock+=3.0;pet.rig.eyes_closed=false
		for j in range(40):pet.step(.05)
		for i in range(76):
			if i in [10,12,14,16,18,20]:pet.notify_click(pet.rig.to_global(TARGETS[region]))
			if i==30:pet.rig.blink_once()
			pet.step(.05)
			await capture("res://preview/raw_click_cover/%s_%03d.png"%[region,i])
			if i==34:
				await capture("res://preview/angry_cover_%s.png"%region)
				var record: Dictionary={"region":region,"clicked":[TARGETS[region].x,TARGETS[region].y],"amount":pet.get_node("ClickCoverController").amount,"chain":{}}
				for side in ["L","R"]:
					var data: Dictionary=pet.get_node("ClickCoverController").arm_pose.controls[side];var points: Dictionary={}
					for name in ["S","E","W"]:points[name]=[data[name].x,data[name].y]
					record.chain[side]=points
				records.append(record)
	if regions.size()==1:
		var old: Array=JSON.parse_string(FileAccess.get_file_as_string("res://data/click_cover_render_samples.json"))
		for record in old:
			if record.region!=regions[0]:records.append(record)
	FileAccess.open("res://data/click_cover_render_samples.json",FileAccess.WRITE).store_string(JSON.stringify(records,"\t"))
	print("CLICK_COVER_GPU_COMPLETE");quit()
