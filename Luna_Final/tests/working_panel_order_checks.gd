extends SceneTree
var pet: Node2D
var reference: Node2D
var accepted: Node2D
var failures: Array[String]=[]
var metrics: Dictionary={}
var trajectory: Array=[]
func _initialize() -> void:call_deferred("run")
func check(ok: bool,message: String) -> void:
	if not ok:failures.append(message);push_error(message)
func run() -> void:
	pet=load("res://LunaPet.tscn").instantiate();pet.automatic_processing=false;pet.random_events_enabled=false
	root.add_child(pet);pet.get_node("InteractionController").mouse_input_enabled=false
	accepted=load("res://LunaPet.tscn").instantiate();accepted.automatic_processing=false;accepted.random_events_enabled=false
	accepted.get_node("WritingController").set_script(load("res://baselines/phase4_7_writing_controller.gd"));root.add_child(accepted)
	accepted.get_node("InteractionController").mouse_input_enabled=false
	reference=load("res://baselines/LunaRig_Phase4.tscn").instantiate();reference.autoplay_enabled=false;reference.random_blink_enabled=false;root.add_child(reference)
	var normal_error: float=0.0
	for i in range(385):
		var time: float=i/60.0;pet.motion.reset();pet.composer.apply(pet.motion.output,time);reference.sample_idle(time)
		for name in reference.bones:
			var a: Transform2D=pet.rig.bones[name].global_transform;var b: Transform2D=reference.bones[name].global_transform
			normal_error=maxf(normal_error,a.origin.distance_to(b.origin))
			check(absf(a.get_rotation()-b.get_rotation())<0.000001,"unchanged normal rotation "+name)
		check(pet.rig.layers.arm_L.visible and pet.rig.layers.arm_R.visible,"normal uses original arm sprites")
	check(normal_error<0.001,"normal bone world positions match protected Phase4")
	metrics.normal_world_error_px=normal_error
	for side in ["L","R"]:
		check(pet.rig.bones["hand_"+side].get_parent()==pet.rig.bones["forearm_"+side],"wrist child of forearm "+side)
	pet.base_time=0.0;pet.composer.apply(pet.motion.output,0.0);pet.foot_lock.restore()
	var feet: Array[Vector2]=[pet.rig.bones.foot_L.global_position,pet.rig.bones.foot_R.global_position]
	accepted.motion.reset();accepted.base_time=0.0;accepted.composer.apply(accepted.motion.output,0.0);accepted.foot_lock.restore()
	pet.set_working(true);accepted.set_working(true)
	var tip_min:=Vector2(INF,INF);var tip_max:=Vector2(-INF,-INF)
	var all_tips_inside: bool=true
	var chain_error: float=0.0;var min_projection_area: float=1.0
	var left_min:=Vector2(INF,INF);var left_max:=Vector2(-INF,-INF)
	var contact_frames: int=0;var lifted_frames: int=0;var ink_points: int=0;var grip_min: float=1.0;var support_min: float=1.0
	var controller: Node2D=pet.get_node("WritingController")
	var authored_transform: Transform2D=controller.fingertips.transform
	var authored_texture=controller.fingertips.texture
	var surface=pet.get_node("EffectLayer").sprites.panel
	var top: float=surface.CORNERS[0].distance_to(surface.CORNERS[1]);var bottom: float=surface.CORNERS[3].distance_to(surface.CORNERS[2])
	check(top/bottom>1.05 and top/bottom<1.20,"reference upper-wide lower-narrow perspective")
	var roundtrip: float=0.0;var panel_area: float=1.0
	for q in [Vector2(-180,-115),Vector2(180,-115),Vector2(180,115),Vector2(-180,115),Vector2.ZERO,Vector2(43,12),Vector2(145,72)]:
		roundtrip=maxf(roundtrip,q.distance_to(surface.local_to_surface(surface.surface_to_local(q))))
	for face in surface.surface_mesh.polygons:
		var v: PackedVector2Array=surface.surface_mesh.polygon;var uv: PackedVector2Array=surface.surface_mesh.uv
		panel_area=minf(panel_area,(v[face[1]]-v[face[0]]).cross(v[face[2]]-v[face[0]])/(uv[face[1]]-uv[face[0]]).cross(uv[face[2]]-uv[face[0]]))
	check(roundtrip<0.001 and panel_area>0.0,"projective surface inverse and mesh orientation")
	metrics.panel_top_bottom_ratio=top/bottom;metrics.surface_roundtrip_error_px=roundtrip;metrics.minimum_panel_triangle_ratio=panel_area
	var panel_z: int=pet.get_node("EffectLayer").sprites.panel.z_index
	for poly in controller.arm_pose.meshes:check(poly.z_index<panel_z,"every working arm and cuff behind panel")
	check(controller.support_grip.z_index<panel_z and controller.grip_mesh.z_index<panel_z,"proximal wrist and sleeves behind board")
	check(controller.fingertips is Sprite2D and controller.fingertips.texture.resource_path=="res://assets/working/working_hand_pen_R_v2.png","authored grip sprite replaces compressed open palm")
	check(controller.fingertips.z_index<panel_z and controller.support_front.z_index<panel_z and controller.nib.z_index<panel_z,"panel in front of both hands and actual embedded pen")
	var max_foot: float=0.0;var largest_elbow: float=0.0;var pose_difference: float=0.0
	for i in range(800):
		pet.step(1.0/60.0);accepted.step(1.0/60.0)
		for name in pet.rig.bones:
			var current_pose: Transform2D=pet.rig.bones[name].global_transform;var accepted_pose: Transform2D=accepted.rig.bones[name].global_transform
			pose_difference=maxf(pose_difference,maxf(current_pose.origin.distance_to(accepted_pose.origin),maxf(current_pose.x.distance_to(accepted_pose.x),current_pose.y.distance_to(accepted_pose.y))))
		for name in pet.motion.output:check(pet.motion.output[name]==accepted.motion.output[name],"accepted animation channel identical: "+name)
		check(not controller.ink.visible and not controller.ink.contact and controller.strokes.is_empty(),"no emitted handwriting strokes or contact dot")
		max_foot=maxf(max_foot,pet.rig.bones.foot_L.global_position.distance_to(feet[0]));max_foot=maxf(max_foot,pet.rig.bones.foot_R.global_position.distance_to(feet[1]))
		largest_elbow=maxf(largest_elbow,absf(rad_to_deg(pet.rig.bones.forearm_R.rotation)))
		check(pet.rig.eye_states_valid(),"working exclusive eyes")
		if i==90:pet.rig.blink_once();accepted.rig.blink_once()
		# Include the enter blend: a folded sleeve must never pass through a reflected pose.
		for side in controller.arm_pose.controls:
			var entering: Dictionary=controller.arm_pose.controls[side]
			min_projection_area=minf(min_projection_area,minf(entering.upper.determinant(),entering.fore.determinant()))
		if i>60:
			check(controller.fingertips.visible and controller.support_front.visible and not controller.grip_mesh.visible and not controller.support_grip.visible,"authored writing hand and supporting hand each drawn once")
			check(controller.pen.to_global(controller.GRIP).distance_to(pet.rig.bones["hand_"+controller.WRITING_SIDE].to_global(controller.GRIP))<0.001,"pen is rigidly held at actual reference writing hand grip")
			check(controller.fingertips.transform==authored_transform and controller.fingertips.texture==authored_texture,"writing never warps or substitutes authored curled fingers")
			check(controller.tip_world==accepted.get_node("WritingController").tip_world,"actual pen path exactly preserved")
			check(surface.surface_to_world(controller.tip_panel).distance_to(controller.tip_world)<0.001,"projected ink and actual pen tip share the same surface point")
			for side in ["L","R"]:
				var controls: Dictionary=controller.arm_pose.controls[side]
				var rest: Dictionary=controller.arm_pose.REST[side]
				chain_error=maxf(chain_error,(controls.upper*(rest.E-rest.S)).distance_to(controls.E))
				chain_error=maxf(chain_error,(controls.fore*(rest.W-rest.E)).distance_to(controls.W))
				chain_error=maxf(chain_error,controller.arm_pose.chains[side].wrist.global_position.distance_to(pet.rig.bones["hand_"+side].global_position))
				min_projection_area=minf(min_projection_area,minf(controls.upper.determinant(),controls.fore.determinant()))
			tip_min=tip_min.min(controller.tip_panel);tip_max=tip_max.max(controller.tip_panel)
			all_tips_inside=all_tips_inside and Rect2(-123,-100,253,178).has_point(controller.tip_panel)
			if i<253:trajectory.append({"clock":pet.motion.clock,"panel":[controller.tip_panel.x,controller.tip_panel.y],"world":[controller.tip_world.x,controller.tip_world.y],"contact":controller.pen_down})
			var panel: Sprite2D=pet.get_node("EffectLayer").sprites.panel
			var left: Vector2=panel.to_local(pet.rig.bones["hand_"+controller.SUPPORT_SIDE].global_position)
			left_min=left_min.min(left);left_max=left_max.max(left)
			if controller.pen_down:contact_frames+=1
			else:lifted_frames+=1
			for stroke in controller.strokes:ink_points=maxi(ink_points,stroke.size())
		grip_min=minf(grip_min,controller.fingertips.global_transform.determinant())
		for face in controller.support_grip.polygons:
			var source_left: PackedVector2Array=controller.support_grip.uv
			var now_left: PackedVector2Array=controller.support_grip.polygon
			var area_left: float=(source_left[face[1]]-source_left[face[0]]).cross(source_left[face[2]]-source_left[face[0]])
			support_min=minf(support_min,(now_left[face[1]]-now_left[face[0]]).cross(now_left[face[2]]-now_left[face[0]])/area_left)
	check(chain_error<0.001,"shoulder-elbow-wrist-hand chain has no positional disconnection")
	check(min_projection_area>0.0,"all working sleeve projection triangles retain orientation")
	check(max_foot==0.0,"working feet fixed at exactly zero drift")
	check(all_tips_inside,"pen stays over the surface during both strokes and pauses")
	check(tip_max.distance_to(tip_min)<30.0,"writing remains in a short surface range")
	check(left_max.distance_to(left_min)<6.0,"supporting left wrist stays stable relative to tablet")
	check(controller.contact_valid,"every pen contact inside writing surface")
	check(contact_frames>100 and lifted_frames>100,"actual writing and lifted pen phases")
	check(tip_max.distance_to(tip_min)>10.0 and ink_points==0,"writing motion preserved without ink")
	check(pose_difference==0.0,"all bone world transforms match accepted Phase4.7 over 800 frames")
	metrics.accepted_pose_maximum_difference=pose_difference;metrics.handwriting_disabled=true
	check(grip_min>0.0,"authored writing sprite transform never mirrors or collapses")
	check(support_min>0.15,"supporting hand mesh has no triangle inversion")
	check(largest_elbow<=52.001,"elbow safety bound")
	# Looped scalar channels have matching endpoints, including writing contact.
	var clip: Animation=pet.motion.player.get_animation("working_loop")
	for track in range(clip.get_track_count()):
		check(is_equal_approx(clip.bezier_track_interpolate(track,0.0),clip.bezier_track_interpolate(track,3.2)),"writing loop endpoints")
	var loop_pose: Dictionary={};var loop_tip:=Vector2.ZERO;var loop_error: float=0.0
	for sample_time in [0.0,6.4]:
		pet.motion.play("working_loop",0.0);pet.motion.blend_clock=1.0;pet.motion.advance(sample_time)
		pet.composer.apply(pet.motion.output,sample_time);pet.foot_lock.finish_frame()
		if sample_time==0.0:
			for name in pet.rig.bones:loop_pose[name]=pet.rig.bones[name].global_transform
			loop_tip=controller.tip_world
		else:
			for name in loop_pose:
				var old: Transform2D=loop_pose[name];var current: Transform2D=pet.rig.bones[name].global_transform
				loop_error=maxf(loop_error,maxf(old.origin.distance_to(current.origin),maxf(old.x.distance_to(current.x),old.y.distance_to(current.y))))
			check(controller.tip_world==loop_tip,"actual nib endpoint identical at 0 and 6.4 seconds")
	check(loop_error==0.0,"all actual bone transforms identical at 0 and 6.4 seconds")
	metrics.complete_working_loop_maximum_transform_difference=loop_error
	# Recover from arbitrary pen phase; no reset to a fixed wrist pose.
	var before: Dictionary=pet.motion.output.duplicate()
	pet.set_working(false);pet.step(0.000001)
	var exit_jump: float=absf(pet.motion.output.forearm_R-before.forearm_R)
	check(exit_jump<0.0001,"working exit starts at current pose")
	for i in range(40):pet.step(1.0/60.0)
	check(pet.states.current_name=="idle" and not controller.pen.visible and not controller.grip_mesh.visible and not controller.fingertips.visible and pet.rig.layers.hand_R.visible and pet.rig.layers.hand_R.modulate.a==1.0,"writing recovery hides props and restores hand")
	check(not controller.support_grip.visible and not controller.support_front.visible and controller.arm_pose.controls.is_empty(),"working-only support pose fully restored")
	for poly in controller.arm_pose.meshes:check(not poly.visible,"working sleeves hidden after recovery")
	check(pet.foot_lock.maximum_drift()==0.0,"exit foot lock")
	var handover_steps: Dictionary={}
	for target in ["success","error","drag"]:
		pet.request_idle()
		for i in range(120):pet.step(1.0/60.0)
		pet.set_working(true)
		for i in range(100):pet.step(1.0/60.0)
		var last: Dictionary={}
		for name in ["shoulder_L","shoulder_R","forearm_L","forearm_R","hand_L","hand_R"]:last[name]=pet.rig.bones[name].rotation_degrees
		match target:
			"success":pet.notify_success()
			"error":pet.notify_error()
			"drag":pet.start_drag(Vector2(768,1100))
		var max_step: float=0.0
		for i in range(90):
			pet.step(1.0/60.0)
			for name in last:
				var now: float=pet.rig.bones[name].rotation_degrees
				max_step=maxf(max_step,absf(now-last[name]));last[name]=now
		check(max_step<8.0,"smooth arm takeover from working to "+target)
		handover_steps[target]=max_step
		if target=="drag":
			pet.end_drag()
			for i in range(75):pet.step(1.0/60.0)
			check(pet.foot_lock.locked and pet.foot_lock.maximum_drift()==0.0,"arm drag retains restored foot lock")
	metrics.chain_connection_error_px=chain_error;metrics.minimum_working_projection_area_ratio=min_projection_area
	metrics.minimum_support_hand_triangle_ratio=support_min
	metrics.arm_handover_max_step_degrees=handover_steps
	metrics.all_tips_inside=all_tips_inside;metrics.left_support_travel_panel_px=left_max.distance_to(left_min)
	metrics.merge({"working_foot_drift_px":max_foot,"pen_travel_px":tip_max.distance_to(tip_min),"tip_min":[tip_min.x,tip_min.y],"tip_max":[tip_max.x,tip_max.y],"pen_contact_frames":contact_frames,"pen_lift_frames":lifted_frames,"maximum_stroke_points":ink_points,"minimum_authored_grip_transform_determinant":grip_min,"maximum_elbow_degrees":largest_elbow,"exit_jump_degrees":exit_jump})
	var report: Dictionary={"pass":failures.is_empty(),"failures":failures,"metrics":metrics}
	FileAccess.open("res://data/working_panel_order_acceptance.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	FileAccess.open("res://data/panel_order_path_samples.json",FileAccess.WRITE).store_string(JSON.stringify(trajectory,"\t"))
	print("WORKING_PANEL_ORDER ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
