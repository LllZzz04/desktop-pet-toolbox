extends SceneTree
var pet: Node2D
var failures: Array[String]=[]
var metrics: Dictionary={}
var meshes: Array=[]
var anchors: Dictionary={}
var minimum_mesh_ratio: float=1.0
var maximum_mesh_ratio: float=1.0
var flipped_triangles: int=0
var leg_min_ratio: float=1.0
var leg_max_ratio: float=1.0
const TARGETS := {"head":Vector2(600,650),"chest":Vector2(772,1070),"legs":Vector2(700,1650)}
func _initialize() -> void:call_deferred("run")
func check(ok: bool,message: String) -> void:
	if not ok and not failures.has(message):failures.append(message);push_error(message)
func create_pet() -> Node2D:
	var result: Node2D=load("res://LunaPet.tscn").instantiate()
	result.automatic_processing=false;result.random_events_enabled=false;root.add_child(result)
	result.get_node("InteractionController").mouse_input_enabled=false
	return result
func six_clicks(region: String) -> void:
	for i in range(6):pet.notify_click(pet.rig.to_global(TARGETS[region]));pet.step(.10)
func check_meshes() -> void:
	var inverse: Transform2D=pet.rig.global_transform.affine_inverse()
	for mesh in meshes:
		var vertices: Array[Vector2]=[]
		for i in range(mesh.vertices_world.size()):
			var p:=Vector2(mesh.vertices_world[i][0],mesh.vertices_world[i][1]);var v:=Vector2.ZERO
			for name in mesh.weights:
				var weight: float=mesh.weights[name][i]
				if weight>0:v+=(inverse*pet.rig.bones[name].global_transform*(p-anchors[name]))*weight
			vertices.append(v)
		for face in mesh.triangles:
			var a:=Vector2(mesh.vertices_world[face[0]][0],mesh.vertices_world[face[0]][1])
			var b:=Vector2(mesh.vertices_world[face[1]][0],mesh.vertices_world[face[1]][1])
			var c:=Vector2(mesh.vertices_world[face[2]][0],mesh.vertices_world[face[2]][1])
			var ratio: float=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[2]]-vertices[face[0]])/(b-a).cross(c-a)
			minimum_mesh_ratio=minf(minimum_mesh_ratio,ratio);maximum_mesh_ratio=maxf(maximum_mesh_ratio,ratio)
			if String(mesh.get("layer",mesh.get("name",""))).begins_with("leg_"):
				leg_min_ratio=minf(leg_min_ratio,ratio);leg_max_ratio=maxf(leg_max_ratio,ratio)
			if ratio<=0:flipped_triangles+=1
func run() -> void:
	meshes=JSON.parse_string(FileAccess.get_file_as_string("res://data/mesh_manifest.json"))
	for b in JSON.parse_string(FileAccess.get_file_as_string("res://data/bones.json")):anchors[b.name]=Vector2(b.pivot[0],b.pivot[1])
	pet=create_pet();var interaction: Node=pet.get_node("InteractionController")
	# Hit coordinates remain valid after moving and scaling the desktop pet.
	for placement in [Transform2D.IDENTITY,Transform2D(.12,Vector2(.28,.28),0.0,Vector2(390,60))]:
		pet.transform=placement
		for region in TARGETS:check(interaction.region_at(pet.rig.to_global(TARGETS[region]))==region,"transformed hit test "+region)
	check(interaction.region_at(pet.rig.to_global(Vector2(50,50))).is_empty(),"outside character ignored")
	pet.transform=Transform2D.IDENTITY
	for i in range(3):pet.notify_click(pet.rig.to_global(TARGETS.head));pet.step(.08)
	check(pet.motion.clip=="click_annoyed","triple click retained")
	for i in range(3):pet.notify_click(pet.rig.to_global(TARGETS.chest));pet.step(.08)
	check(not pet.motion.clip.begins_with("click_angry"),"mixed regions do not count as six clicks")
	pet.queue_free();await process_frame
	var cases: Dictionary={}
	for region in ["head","chest","legs"]:
		pet=create_pet();interaction=pet.get_node("InteractionController")
		var cover: Node2D=pet.get_node("ClickCoverController")
		var feet: Array[Vector2]=[pet.rig.bones.foot_L.global_position,pet.rig.bones.foot_R.global_position]
		six_clicks(region)
		check(pet.motion.clip=="click_angry_"+region,"correct region clip "+region)
		var clip: Animation=pet.motion.player.get_animation("click_angry_"+region)
		for index in range(clip.get_track_count()):
			check(clip.bezier_track_interpolate(index,0.0)==0.0 and clip.bezier_track_interpolate(index,2.0)==0.0,"one-shot returns every overlay channel to zero "+region)
		var first_clock: float=pet.motion.clock
		for i in range(9):pet.notify_click(pet.rig.to_global(TARGETS[region]))
		check(pet.motion.clock==first_clock,"cooldown prevents animation restart "+region)
		var drift: float=0.0;var chain_error: float=0.0;var min_area: float=1.0
		var largest_step: float=0.0;var peak: float=0.0;var last: Dictionary={}
		var closed_seen: bool=false;var open_seen: bool=false
		for i in range(180):
			if i==20:pet.rig.blink_once()
			pet.step(1.0/60.0);peak=maxf(peak,cover.amount)
			drift=maxf(drift,feet[0].distance_to(pet.rig.bones.foot_L.global_position));drift=maxf(drift,feet[1].distance_to(pet.rig.bones.foot_R.global_position))
			check(pet.rig.eye_states_valid(),"exclusive eyes "+region)
			if i>=20 and i<40:closed_seen=closed_seen or pet.rig.eyes_closed;open_seen=open_seen or (i>25 and not pet.rig.eyes_closed)
			if i%4==0:check_meshes()
			for side in cover.arm_pose.controls:
				var controls: Dictionary=cover.arm_pose.controls[side];var rest: Dictionary=cover.arm_pose.REST[side]
				chain_error=maxf(chain_error,(controls.upper*(rest.E-rest.S)).distance_to(controls.E))
				chain_error=maxf(chain_error,(controls.fore*(rest.W-rest.E)).distance_to(controls.W))
				min_area=minf(min_area,minf(controls.upper.determinant(),controls.fore.determinant()))
				if last.has(side):largest_step=maxf(largest_step,controls.W.distance_to(last[side]))
				last[side]=controls.W
			if i==40:
				check(cover.amount>.99,"full cover pose "+region)
				check(pet.expressions.additions.mouth_pout.visible==(region=="head"),"pout exclusive to head")
				check(pet.expressions.additions.blush.visible==(region!="head"),"blush for chest and legs")
		check(drift==0.0,"exact foot lock "+region)
		check(min_area>0.0 and chain_error<.001,"connected positive sleeve meshes "+region)
		check(largest_step<65.0,"no wrist path discontinuity "+region)
		check(closed_seen and open_seen,"blink remains independent "+region)
		check(pet.states.current_name=="idle" and cover.amount==0.0 and cover.arm_pose.controls.is_empty(),"automatic recovery "+region)
		for side in ["L","R"]:
			check(pet.rig.layers["hand_"+side].visible and not cover.arm_pose.hands[side].visible,"original hands restored "+region)
		for poly in cover.arm_pose.meshes:check(not poly.visible,"temporary sleeves removed "+region)
		check(not pet.expressions.additions.mouth_pout.visible and not pet.expressions.additions.blush.visible,"expressions clear after reaction "+region)
		cases[region]={"foot_drift_px":drift,"chain_error_px":chain_error,"minimum_sleeve_area_ratio":min_area,"maximum_wrist_frame_step_px":largest_step,"peak_cover":peak,"blink_closed_and_reopened":closed_seen and open_seen}
		pet.queue_free();await process_frame
	# Rapid input can be interrupted by higher priorities; no frozen raised hand remains.
	var handovers: Dictionary={}
	for target in ["working","success","drag"]:
		pet=create_pet();six_clicks("head")
		for i in range(24):pet.step(1.0/60.0)
		match target:
			"working":pet.set_working(true)
			"success":pet.notify_success()
			"drag":pet.start_drag(Vector2(768,1100))
		var before: String=pet.states.current_name
		for i in range(6):pet.notify_click(pet.rig.to_global(TARGETS.chest))
		check(pet.states.current_name==before,"higher priority rejects clicks "+target)
		for i in range(48):pet.step(1.0/60.0)
		check(pet.get_node("ClickCoverController").amount==0.0,"higher priority clears cover "+target)
		handovers[target]=true
		if target=="drag":
			pet.end_drag()
			for i in range(90):pet.step(1.0/60.0)
			check(pet.foot_lock.locked and pet.foot_lock.maximum_drift()==0.0,"drag release restores foot lock")
		pet.rest_pose();check(pet.get_node("ClickCoverController").arm_pose.controls.is_empty(),"rest removes cover")
		pet.queue_free();await process_frame
	# Slow isolated clicks cannot accidentally trigger angry reactions.
	pet=create_pet()
	for i in range(6):
		pet.notify_click(TARGETS.head)
		for j in range(84):pet.step(1.0/60.0)
		check(not pet.motion.clip.begins_with("click_angry"),"click window expires")
	check(flipped_triangles==0,"existing meshes never invert")
	# The leg reaction now includes a shallow crouch; the previous 5% idle-only
	# compression bound does not describe this intended pose. Shoes remain rigid.
	check(leg_min_ratio>.72 and leg_max_ratio<1.05,"shallow crouch retains safe leg area")
	metrics={"regions":cases,"mesh_flips":flipped_triangles,"mesh_min_area_ratio":minimum_mesh_ratio,"mesh_max_area_ratio":maximum_mesh_ratio,"leg_min_area_ratio":leg_min_ratio,"leg_max_area_ratio":leg_max_ratio,"higher_priority_takeovers":handovers}
	var report: Dictionary={"pass":failures.is_empty(),"failures":failures,"metrics":metrics}
	FileAccess.open("res://data/click_cover_acceptance.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("CLICK_COVER_ACCEPTANCE ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
