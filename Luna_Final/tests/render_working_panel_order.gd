extends SceneTree
var viewport: SubViewport
var pet: Node2D
var writing: Node2D
var panel: Sprite2D
var samples: Array=[]
func _initialize() -> void:call_deferred("run")
func capture(path: String) -> void:
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	assert(viewport.get_texture().get_image().save_png(path)==OK)
func isolate() -> void:
	for layer in pet.rig.layers.values():layer.visible=false
	for sprite in pet.get_node("EffectLayer").sprites.values():sprite.visible=false
	for sprite in pet.expressions.additions.values():sprite.visible=false
	for node in [writing.pen,writing.nib,writing.ink,writing.grip_mesh,writing.fingertips,writing.support_grip,writing.support_front]:node.visible=false
	for poly in writing.arm_pose.meshes:poly.visible=false
func run() -> void:
	if DisplayServer.get_name()=="headless":quit(1);return
	viewport=SubViewport.new();viewport.size=Vector2i(1536,2304);viewport.transparent_bg=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	pet=load("res://LunaPet.tscn").instantiate();pet.automatic_processing=false;pet.random_events_enabled=false;viewport.add_child(pet)
	pet.get_node("InteractionController").mouse_input_enabled=false
	writing=pet.get_node("WritingController");panel=pet.get_node("EffectLayer").sprites.panel
	DirAccess.make_dir_recursive_absolute("res://preview/raw_reference_readability")
	pet.rest_pose();await capture("res://preview/rest_pose_gpu.png")
	for i in [0,48,96,144,192]:
		pet.motion.reset();pet.composer.apply(pet.motion.output,i/30.0)
		await capture("res://preview/normal_%03d_gpu.png"%i)
	pet.set_working(true)
	for i in range(30):pet.step(1.0/60.0)
	for i in range(9):
		for layer in pet.rig.layers.values():layer.visible=true
		pet.motion.play("working_loop",0);pet.motion.blend_clock=1.0;pet.motion.advance(maxf(i*.4,0.00001));pet.composer.apply(pet.motion.output,i*.4)
		var label: String="%02d"%i
		var record: Dictionary={"time":i*.4,"label":label,"chain":{}}
		for side in ["L","R"]:
			var c: Dictionary=writing.arm_pose.controls[side];var data: Dictionary={}
			for name in ["S","E","W"]:data[name]=[c[name].x,c[name].y]
			record.chain[side]=data
		var corners: Array=[]
		for p in panel.call("world_corners"):corners.append([p.x,p.y])
		record.panel=corners;record.tip=[writing.tip_world.x,writing.tip_world.y];samples.append(record)
		var grip: Vector2=writing.pen.to_global(writing.GRIP);record.grip=[grip.x,grip.y]
		var cap: Vector2=writing.pen.to_global(writing.CAP);record.pen_cap=[cap.x,cap.y]
		await capture("res://preview/raw_reference_readability/"+label+"_composite.png")
		isolate();panel.visible=true;await capture("res://preview/raw_reference_readability/"+label+"_panel.png")
		# Actual panel-only vs panel plus both behind-panel hands / embedded pen.
		writing.fingertips.visible=true;writing.support_front.visible=true
		await capture("res://preview/raw_reference_readability/"+label+"_panel_with_hands.png")
		for poly in writing.arm_pose.meshes:poly.visible=true
		writing.grip_mesh.visible=true
		# Arms and both hands are below the opaque board.
		await capture("res://preview/raw_reference_readability/"+label+"_panel_with_rear_arms.png")
		for side in ["L","R"]:
			for index in range(3):
				isolate();writing.arm_pose.chains[side].polygons[index].visible=true
				await capture("res://preview/raw_reference_readability/"+label+"_"+["upper_","fore_","cuff_"][index]+side+".png")
			isolate()
			if side==writing.WRITING_SIDE:
				writing.grip_mesh.visible=true;writing.fingertips.visible=true
			else:writing.support_grip.visible=true
			await capture("res://preview/raw_reference_readability/"+label+"_hand_"+side+".png")
		isolate();writing.fingertips.visible=true;await capture("res://preview/raw_reference_readability/"+label+"_grip_front.png")
		isolate();writing.support_front.visible=true;await capture("res://preview/raw_reference_readability/"+label+"_support_front.png")
		isolate();writing.pen.visible=true;await capture("res://preview/raw_reference_readability/"+label+"_pen_front.png")
	for layer in pet.rig.layers.values():layer.visible=true
	pet.motion.play("working_loop",0);pet.motion.blend_clock=1.0;pet.motion.advance(1.3);pet.composer.apply(pet.motion.output,1.3)
	await capture("res://preview/working_panel_front_native.png")
	FileAccess.open("res://data/working_panel_order_samples.json",FileAccess.WRITE).store_string(JSON.stringify(samples,"\t"))
	print("PANEL_ORDER_GPU_COMPLETE");quit()
