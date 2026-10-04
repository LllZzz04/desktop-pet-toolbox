extends SceneTree
var pet: Node2D
var baseline: Node2D
var failures: Array[String]=[]
var metrics: Dictionary={}
var meshes: Array=[]
var anchors: Dictionary={}
var mesh_flips: int=0
var mesh_min_ratio: float=1.0
var mesh_max_ratio: float=1.0
func _initialize() -> void:call_deferred("run")
func check(condition: bool,message: String) -> void:
	if not condition:failures.append(message);push_error(message)
func advance(seconds: float,safety: bool=true) -> void:
	var count: int=int(ceil(seconds*60.0))
	for i in range(count):
		pet.step(seconds/count)
		check(pet.rig.eye_states_valid(),"eye exclusivity")
		if safety and i%4==0:check_meshes()
func feet() -> Array[Vector2]:return [pet.rig.bones.foot_L.global_position,pet.rig.bones.foot_R.global_position]
func pose(rig: Node2D) -> Dictionary:
	var result: Dictionary={}
	for name in rig.bones:result[name]=rig.bones[name].transform
	return result
func check_meshes() -> void:
	var inverse: Transform2D=pet.rig.global_transform.affine_inverse()
	for mesh in meshes:
		var vertices: Array[Vector2]=[]
		for i in range(mesh.vertices_world.size()):
			var p:=Vector2(mesh.vertices_world[i][0],mesh.vertices_world[i][1])
			var v:=Vector2.ZERO
			for name in mesh.weights:
				var w: float=mesh.weights[name][i]
				if w==0.0:continue
				v+=(inverse*pet.rig.bones[name].global_transform*(p-anchors[name]))*w
			vertices.append(v)
		for face in mesh.triangles:
			var a:=Vector2(mesh.vertices_world[face[0]][0],mesh.vertices_world[face[0]][1])
			var b:=Vector2(mesh.vertices_world[face[1]][0],mesh.vertices_world[face[1]][1])
			var c:=Vector2(mesh.vertices_world[face[2]][0],mesh.vertices_world[face[2]][1])
			var ratio: float=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[2]]-vertices[face[0]])/(b-a).cross(c-a)
			mesh_min_ratio=minf(mesh_min_ratio,ratio);mesh_max_ratio=maxf(mesh_max_ratio,ratio)
			if ratio<=0.0:mesh_flips+=1
func run() -> void:
	var stage: String="A"
	var args: PackedStringArray=OS.get_cmdline_user_args()
	if not args.is_empty():stage=args[0]
	pet=load("res://LunaPet.tscn").instantiate();pet.automatic_processing=false;pet.random_events_enabled=false
	root.add_child(pet)
	baseline=load("res://LunaRig.tscn").instantiate();baseline.autoplay_enabled=false;baseline.random_blink_enabled=false
	root.add_child(baseline)
	meshes=JSON.parse_string(FileAccess.get_file_as_string("res://data/mesh_manifest.json"))
	for b in JSON.parse_string(FileAccess.get_file_as_string("res://data/bones.json")):anchors[b.name]=Vector2(b.pivot[0],b.pivot[1])
	pet.rest_pose();baseline.rest_pose()
	check(pose(pet.rig)==pose(baseline),"unchanged rest bone transforms")
	pet.motion.reset()
	var normal_exact: bool=true
	for i in range(65):
		pet.base_time=i/10.0;pet.composer.apply(pet.motion.output,pet.base_time)
		baseline.sample_idle(i/10.0)
		normal_exact=normal_exact and pose(pet.rig)==pose(baseline)
	check(normal_exact,"normal_idle exact baseline transforms")
	metrics.normal_idle_exact=normal_exact
	var test: RefCounted=load("res://tests/stages/"+stage+".gd").new()
	test.run(self)
	check(mesh_flips==0,"no flipped mesh triangles")
	metrics.mesh_flips=mesh_flips;metrics.mesh_min_ratio=mesh_min_ratio;metrics.mesh_max_ratio=mesh_max_ratio
	var report: Dictionary={"stage":stage,"pass":failures.is_empty(),"failures":failures,"metrics":metrics}
	FileAccess.open("res://data/phase4"+stage+"_acceptance.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("PHASE4",stage,"_ACCEPTANCE ",JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)
