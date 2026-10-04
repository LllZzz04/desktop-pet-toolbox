extends SceneTree
var pet: Node2D
var reference: Node2D
var failures: Array[String]=[]
var meshes: Array=[]
var anchors: Dictionary={}
var minimum_area: float=1.0
var maximum_area: float=1.0
var flips: int=0
var shoe_error: float=0.0
func _initialize() -> void:call_deferred("run")
func check(ok: bool,message: String) -> void:
	if not ok and not failures.has(message):failures.append(message);push_error(message)
func make_pet() -> Node2D:
	var result: Node2D=load("res://LunaPet.tscn").instantiate();result.automatic_processing=false;result.random_events_enabled=false;root.add_child(result)
	result.get_node("InteractionController").mouse_input_enabled=false
	return result
func inspect_legs() -> void:
	for mesh in meshes:
		var layer: String=String(mesh.get("layer_name",mesh.get("layer",mesh.get("name",""))))
		if not layer.begins_with("leg_"):continue
		var vertices: Array[Vector2]=[]
		for i in range(mesh.vertices_world.size()):
			var p:=Vector2(mesh.vertices_world[i][0],mesh.vertices_world[i][1]);var v:=Vector2.ZERO
			for bone in mesh.weights:
				var weight: float=mesh.weights[bone][i]
				if weight>0.0:v+=(pet.rig.bones[bone].global_transform*(p-anchors[bone]))*weight
			vertices.append(v)
			var foot: String="foot_"+layer.right(1)
			if mesh.weights[foot][i]==1.0:
				shoe_error=maxf(shoe_error,v.distance_to(pet.rig.bones[foot].global_transform*(p-anchors[foot])))
		for face in mesh.triangles:
			var a:=Vector2(mesh.vertices_world[face[0]][0],mesh.vertices_world[face[0]][1]);var b:=Vector2(mesh.vertices_world[face[1]][0],mesh.vertices_world[face[1]][1]);var c:=Vector2(mesh.vertices_world[face[2]][0],mesh.vertices_world[face[2]][1])
			var ratio: float=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[2]]-vertices[face[0]])/(b-a).cross(c-a)
			minimum_area=minf(minimum_area,ratio);maximum_area=maxf(maximum_area,ratio)
			if ratio<=0.0:flips+=1
func run() -> void:
	meshes=JSON.parse_string(FileAccess.get_file_as_string("res://data/mesh_manifest.json"))
	pet=make_pet();pet.rest_pose()
	for bone in pet.rig.bones:anchors[bone]=pet.rig.bones[bone].global_position
	pet.queue_free();await process_frame
	reference=make_pet()
	var cases: Array=[]
	for phase in [0.0,1.6,3.2,4.8]:
		for target in [Vector2(610,1520),Vector2(930,1900)]:
			pet=make_pet();pet.base_time=phase;pet.composer.apply(pet.motion.output,phase);pet.foot_lock.restore()
			var ground: Array[Vector2]=[pet.rig.bones.foot_L.global_position,pet.rig.bones.foot_R.global_position]
			for i in range(6):pet.notify_click(pet.rig.to_global(target));pet.step(.08)
			check(pet.motion.clip=="click_angry_legs","six clicks choose leg reaction")
			var clip: Animation=pet.motion.player.get_animation("click_angry_legs")
			for track in range(clip.get_track_count()):check(clip.bezier_track_interpolate(track,0.0)==0 and clip.bezier_track_interpolate(track,2.0)==0,"one-shot offset endpoints")
			var drop: float=0.0;var drift: float=0.0;var reach: float=0.0;var chain_error: float=0.0
			var closed: bool=false;var reopened: bool=false
			for i in range(150):
				if i==25:pet.rig.blink_once()
				pet.step(1.0/60.0)
				reference.composer.apply(reference.motion.channels.DEFAULTS,pet.base_time)
				drop=maxf(drop,pet.rig.bones.pelvis.global_position.y-reference.rig.bones.pelvis.global_position.y)
				for side in ["L","R"]:
					var index: int=0 if side=="L" else 1
					drift=maxf(drift,ground[index].distance_to(pet.rig.bones["foot_"+side].global_position))
				var pose: Node2D=pet.get_node("ClickCoverController").arm_pose
				for side in pose.controls:
					var c: Dictionary=pose.controls[side];var rest: Dictionary=pose.REST[side]
					reach=maxf(reach,maxf(c.S.distance_to(c.E)/rest.S.distance_to(rest.E),c.E.distance_to(c.W)/rest.E.distance_to(rest.W)))
					chain_error=maxf(chain_error,(c.upper*(rest.E-rest.S)).distance_to(c.E));chain_error=maxf(chain_error,(c.fore*(rest.W-rest.E)).distance_to(c.W))
					check(c.upper.determinant()>0.0 and c.fore.determinant()>0.0,"positive sleeve projection")
				check(pet.foot_lock.locked,"crouch never releases foot lock")
				check(pet.rig.eye_states_valid(),"exclusive eyes")
				if i>=25 and i<38:closed=closed or pet.rig.eyes_closed
				if i>=38:reopened=reopened or not pet.rig.eyes_closed
				if i%3==0:inspect_legs()
			check(drop>=44.99 and drop<=45.01,"45px shallow crouch")
			check(drift==0.0 and pet.foot_lock.maximum_drift()==0.0,"feet fixed throughout")
			check(reach<1.12 and chain_error<.001,"connected sleeves avoid elongated arms")
			check(closed and reopened,"independent blink during crouch")
			check(pet.states.current_name=="idle" and pet.motion.output.leg_crouch==0.0,"recover to unchanged idle")
			cases.append({"idle_phase":phase,"target":[target.x,target.y],"pelvis_drop_px":drop,"foot_drift_px":drift,"maximum_sleeve_length_ratio":reach,"chain_error_px":chain_error,"blink_closed_and_reopened":closed and reopened})
			pet.queue_free();await process_frame
	var takeovers: Dictionary={}
	for action in ["working","success","drag"]:
		pet=make_pet()
		for i in range(6):pet.notify_click(pet.rig.to_global(Vector2(700,1650)));pet.step(.08)
		for i in range(24):pet.step(1.0/60.0)
		match action:
			"working":pet.set_working(true)
			"success":pet.notify_success()
			"drag":pet.start_drag(Vector2(768,1100))
		for i in range(60):pet.step(1.0/60.0)
		check(pet.motion.output.leg_crouch==0.0 and pet.get_node("ClickCoverController").amount==0.0,"higher priority clears crouch "+action)
		if action=="drag":pet.end_drag()
		elif action=="working":pet.set_working(false)
		for i in range(90):pet.step(1.0/60.0)
		check(pet.states.current_name=="idle" and pet.foot_lock.locked and pet.foot_lock.maximum_drift()==0.0,"takeover restores standing feet "+action)
		takeovers[action]=true
		pet.queue_free();await process_frame
	check(flips==0 and minimum_area>.72 and maximum_area<1.05,"safe shallow leg deformation")
	check(shoe_error==0.0,"shoe vertices remain rigid")
	var report: Dictionary={"pass":failures.is_empty(),"failures":failures,"cases":cases,"leg_mesh_flips":flips,"leg_min_area_ratio":minimum_area,"leg_max_area_ratio":maximum_area,"shoe_rigid_error_px":shoe_error,"higher_priority_takeovers":takeovers}
	FileAccess.open("res://data/leg_guard_crouch_acceptance.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("LEG_GUARD_CROUCH_ACCEPTANCE ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
