extends SceneTree
var pet: Node2D
var failures: Array[String]=[]
var meshes: Array=[]
var anchors: Dictionary={}
var minimum_area: float=1.0
var maximum_area: float=1.0
var leg_minimum: float=1.0
var leg_maximum: float=1.0
var flipped: int=0
var maximum_shoe_error: float=0.0
var samples: Array=[]
func _initialize() -> void:call_deferred("run")
func check(ok: bool,message: String) -> void:
	if not ok and not failures.has(message):failures.append(message);push_error(message)
func make_pet() -> Node2D:
	var result: Node2D=load("res://LunaPet.tscn").instantiate()
	result.automatic_processing=false;result.random_events_enabled=false;root.add_child(result)
	result.get_node("InteractionController").mouse_input_enabled=false
	return result
func feet() -> Array[Vector2]:return [pet.rig.bones.foot_L.global_position,pet.rig.bones.foot_R.global_position]
func inspect_meshes() -> void:
	var inverse: Transform2D=pet.rig.global_transform.affine_inverse()
	for mesh in meshes:
		var layer: String=String(mesh.get("layer_name",mesh.get("layer",mesh.get("name",""))))
		if pet.rig.layers.has(layer) and not pet.rig.layers[layer].visible:continue
		var vertices: Array[Vector2]=[]
		for i in range(mesh.vertices_world.size()):
			var p:=Vector2(mesh.vertices_world[i][0],mesh.vertices_world[i][1]);var v:=Vector2.ZERO
			for bone in mesh.weights:
				var weight: float=mesh.weights[bone][i]
				if weight>0.0:v+=(inverse*pet.rig.bones[bone].global_transform*(p-anchors[bone]))*weight
			vertices.append(v)
			if layer.begins_with("leg_"):
				var foot: String="foot_"+layer.right(1)
				if float(mesh.weights[foot][i])==1.0:
					var expected: Vector2=inverse*pet.rig.bones[foot].global_transform*(p-anchors[foot])
					maximum_shoe_error=maxf(maximum_shoe_error,v.distance_to(expected))
		for face in mesh.triangles:
			var a:=Vector2(mesh.vertices_world[face[0]][0],mesh.vertices_world[face[0]][1])
			var b:=Vector2(mesh.vertices_world[face[1]][0],mesh.vertices_world[face[1]][1])
			var c:=Vector2(mesh.vertices_world[face[2]][0],mesh.vertices_world[face[2]][1])
			var ratio: float=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[2]]-vertices[face[0]])/(b-a).cross(c-a)
			minimum_area=minf(minimum_area,ratio);maximum_area=maxf(maximum_area,ratio)
			if ratio<=0.0:flipped+=1
			if layer.begins_with("leg_"):leg_minimum=minf(leg_minimum,ratio);leg_maximum=maxf(leg_maximum,ratio)
	for control in pet.get_node("WritingController").arm_pose.controls.values():
		check(control.upper.determinant()>0 and control.fore.determinant()>0,"Working handover sleeves stay positive")
func run() -> void:
	meshes=JSON.parse_string(FileAccess.get_file_as_string("res://data/mesh_manifest.json"))
	meshes.append_array(JSON.parse_string(FileAccess.get_file_as_string("res://data/arm_mesh_manifest.json")))
	pet=make_pet();pet.rest_pose()
	for bone in pet.rig.bones:anchors[bone]=pet.rig.bones[bone].global_position
	var clip: Animation=pet.motion.player.get_animation("feedback_success")
	check(is_equal_approx(clip.length,1.3) and clip.loop_mode==Animation.LOOP_NONE,"1.3 second one-shot")
	for track in range(clip.get_track_count()):
		var channel: String=String(clip.track_get_path(track)).get_slice(":",1)
		check(clip.track_get_type(track)==Animation.TYPE_BEZIER,"smooth curves "+channel)
		check(is_equal_approx(clip.bezier_track_interpolate(track,1.3),pet.motion.channels.DEFAULTS[channel]),"channel restores default "+channel)
	pet.queue_free();await process_frame
	for origin in ["idle","working"]:
		for phase in [0.0,1.6,3.2,4.8]:
			pet=make_pet();pet.base_time=phase;pet.composer.apply(pet.motion.output,phase);pet.foot_lock.restore()
			if origin=="working":
				pet.set_working(true)
				for j in range(84):pet.step(1.0/60.0)
			var ground: Array[Vector2]=feet();pet.notify_success()
			var lift: float=0.0;var x_drift: float=0.0;var grounded_drift: float=0.0
			var last_hands: Dictionary={"L":pet.rig.bones.hand_L.global_rotation,"R":pet.rig.bones.hand_R.global_rotation}
			var hand_step: float=0.0;var open_peak: float=0.0;var closed_seen: bool=false;var reopened_seen: bool=false
			for i in range(102):
				if i==27:pet.rig.blink_once()
				pet.step(1.0/60.0)
				var now: Array[Vector2]=feet();var time: float=(i+1)/60.0
				for side in range(2):
					lift=maxf(lift,ground[side].y-now[side].y);x_drift=maxf(x_drift,absf(ground[side].x-now[side].x))
					if time<=.15 or time>=.65:grounded_drift=maxf(grounded_drift,ground[side].distance_to(now[side]))
				for side in ["L","R"]:
					var angle: float=pet.rig.bones["hand_"+side].global_rotation
					hand_step=maxf(hand_step,absf(rad_to_deg(angle-last_hands[side])));last_hands[side]=angle
				check(pet.rig.eye_states_valid(),"eye exclusivity")
				if i>=27 and i<39:closed_seen=closed_seen or pet.rig.eyes_closed
				if i>=39:reopened_seen=reopened_seen or not pet.rig.eyes_closed
				if time>=.4 and time<=.5:
					open_peak=maxf(open_peak,absf(pet.motion.output.shoulder_L))
					check(pet.expressions.additions.mouth_success.visible,"apex happy mouth")
					check(pet.get_node("EffectLayer").sprites.check.visible,"apex right-side checkmark")
				if pet.motion.clip=="feedback_success":
					for name in ["hair_side_L","hair_side_R","hair_tip_L","hair_tip_R"]:check(absf(pet.rig.bones[name].rotation_degrees)<=2.001,"hair bounds")
					for name in ["cape_L_root","cape_R_root","cape_L_mid","cape_R_mid"]:check(absf(pet.rig.bones[name].rotation_degrees)<=4.701,"cape bounds")
					check(absf(pet.rig.bones.ahoge_tip.rotation_degrees)<=6.001,"ahoge tip bounds")
				if i%3==0:inspect_meshes()
			check(lift>=21.99 and lift<=22.01,"22px lift "+origin)
			check(x_drift==0.0 and grounded_drift==0.0,"no foot slide / exact contact "+origin)
			check(open_peak>=8.5,"arms open clearly "+origin)
			check(closed_seen and reopened_seen,"independent blink "+origin)
			check(pet.states.current_name=="idle" and pet.foot_lock.locked and pet.foot_lock.maximum_drift()==0.0,"return to locked Idle "+origin)
			check(not pet.expressions.additions.mouth_success.visible,"original mouth restored")
			for name in ["check","success_star_1","success_star_2","success_star_3"]:check(not pet.get_node("EffectLayer").sprites[name].visible,"effect clears "+name)
			samples.append({"origin":origin,"idle_phase":phase,"lift_px":lift,"foot_x_drift_px":x_drift,"grounded_foot_drift_px":grounded_drift,"maximum_hand_step_degrees":hand_step,"shoulder_peak_degrees":open_peak,"blink_closed_and_reopened":closed_seen and reopened_seen})
			pet.queue_free();await process_frame
	check(flipped==0,"no inverted triangles")
	check(leg_minimum>.90 and leg_maximum<1.10,"small leg area change")
	check(maximum_shoe_error==0.0,"shoes entirely rigid under foot controls")
	var report: Dictionary={"pass":failures.is_empty(),"failures":failures,"cases":samples,"mesh_flips":flipped,"mesh_min_area_ratio":minimum_area,"mesh_max_area_ratio":maximum_area,"leg_min_area_ratio":leg_minimum,"leg_max_area_ratio":leg_maximum,"shoe_rigid_error_px":maximum_shoe_error}
	FileAccess.open("res://data/success_v2_acceptance.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("SUCCESS_V2_ACCEPTANCE ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
