extends SceneTree
## Deterministic production export. All visual layers and pose curves come from
## the frozen LunaPet scene; only host time, input and viewport are controlled.

const FPS := 30
const OUTPUT_SIZE := Vector2i(384, 576)
const CLIPS := [
	{"name":"idle_normal", "duration":6.4, "loop":true},
	# Keep the authored return-to-idle blend, not only the action itself.
	{"name":"idle_look_around", "duration":4.75, "loop":false},
	{"name":"idle_yawn", "duration":4.2, "loop":false},
	{"name":"click_question", "duration":1.25, "loop":false},
	{"name":"click_annoyed", "duration":1.65, "loop":false},
	{"name":"click_angry_head", "duration":2.35, "loop":false},
	{"name":"click_angry_chest", "duration":2.35, "loop":false},
	{"name":"click_angry_legs", "duration":2.35, "loop":false},
	{"name":"working_enter", "duration":0.6, "loop":false},
	{"name":"working_loop", "duration":6.4, "loop":true},
	{"name":"working_exit", "duration":0.75, "loop":false},
	{"name":"working_success", "duration":1.65, "loop":false},
	{"name":"working_error", "duration":1.75, "loop":false},
	{"name":"feedback_success", "duration":1.65, "loop":false},
	{"name":"feedback_error", "duration":1.75, "loop":false},
	{"name":"drag_start", "duration":0.6, "loop":false},
	{"name":"drag_hold", "duration":2.4, "loop":true},
	{"name":"land", "duration":1.2, "loop":false},
]

var viewport: SubViewport
var destination: String

func _initialize() -> void:
	root.position = Vector2i(-32000, -32000)
	root.hide()
	call_deferred("_export_all")

func _export_all() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.is_empty():
		push_error("Expected output directory after --")
		quit(1)
		return
	destination = arguments[0].replace("\\", "/")
	viewport = SubViewport.new()
	viewport.size = OUTPUT_SIZE
	viewport.transparent_bg = true
	viewport.disable_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	root.add_child(viewport)
	var only_attention: bool = arguments.size() > 1 and arguments[1] == "attention"
	var manifest := {"version":2, "size":[384,576], "source_size":[1536,2304], "clips":{}, "directional":{}}
	if only_attention:
		var previous = JSON.parse_string(FileAccess.get_file_as_string(destination.path_join("manifest.json")))
		if not previous is Dictionary or previous.get("version") != 2:
			push_error("A complete v2 manifest is required for a partial greeting export")
			quit(1)
			return
		manifest = previous
	var specifications: Array = [] if only_attention else CLIPS.duplicate(true)
	# Nine close poses are interpolated by the host for continuous gaze. The
	# entrance includes the original 0.7 s greeting, and can be reversed on exit.
	for family in ["attention_enter", "attention_loop"]:
		var names: Array[String] = []
		for direction in range(9):
			var clip: String = family if direction == 4 else "%s_%d" % [family, direction]
			names.append(clip)
			specifications.append({"name":clip, "duration":0.7 if family == "attention_enter" else 6.4,
				"loop":family == "attention_loop", "direction":float(direction) / 4.0 - 1.0})
		manifest.directional[family] = names
	for specification in specifications:
		var result: Dictionary = await _export_clip(specification)
		if result.is_empty():
			quit(1)
			return
		manifest.clips[specification.name] = result
	var file := FileAccess.open(destination.path_join("manifest.json"), FileAccess.WRITE)
	if file == null:
		push_error("Cannot write Luna manifest")
		quit(1)
		return
	file.store_string(JSON.stringify(manifest, "\t") + "\n")
	file.close()
	print("LUNA_EXPORT_COMPLETE clips=", specifications.size())
	quit(0)

func _advance(pet: Node2D, seconds: float) -> void:
	var count := int(round(seconds * FPS))
	for _index in range(count):
		pet.step(1.0 / FPS)

func _prepare_pose(pet: Node2D, specification: Dictionary) -> void:
	var clip: String = specification.name
	if clip.begins_with("attention_"):
		var direction: float = specification.direction
		var x := 772.0 + direction * 450.0
		pet.set_attention(true, pet.to_global(Vector2(x, 600)))
		# Input easing happens in the host. Each sample needs a fixed target;
		# the skeleton's normal entrance blend still applies to that target.
		pet.states.active.angle = direction * 3.0
		if specification.loop: _advance(pet, 6.4)
	elif clip.begins_with("working_"):
		pet.set_working(true)
		if clip != "working_enter": _advance(pet, 6.4)
		if clip == "working_exit": pet.set_working(false)
		if clip == "working_success": pet.notify_success()
		if clip == "working_error": pet.notify_error()
	elif clip in ["drag_start", "drag_hold", "land"]:
		pet.start_drag(pet.to_global(Vector2(768, 1000)))
		if clip != "drag_start":
			_advance(pet, 6.4)
			if clip == "land": pet.end_drag()
	elif clip.begins_with("idle_") and clip != "idle_normal":
		pet.play_idle_variant(clip)
	elif clip.begins_with("click_"):
		var y := 600.0
		if clip.ends_with("chest"): y = 1100.0
		if clip.ends_with("legs"): y = 1700.0
		var clicks := 1
		if clip == "click_annoyed": clicks = 3
		if clip.begins_with("click_angry_"): clicks = 6
		for _index in range(clicks): pet.notify_click(pet.rig.to_global(Vector2(768, y)))
	elif clip == "feedback_success":
		pet.notify_success()
	elif clip == "feedback_error":
		pet.notify_error()
	pet.step(0.0)

func _export_clip(specification: Dictionary) -> Dictionary:
	var clip: String = specification.name
	var folder := destination.path_join(clip)
	if DirAccess.make_dir_recursive_absolute(folder) != OK:
		push_error("Cannot create clip output " + folder)
		return {}
	var pet = load("res://LunaPet.tscn").instantiate()
	pet.automatic_processing = false
	pet.random_events_enabled = false
	pet.get_node("Rig").autoplay_enabled = false
	pet.get_node("Rig").random_blink_enabled = false
	pet.get_node("InteractionController").mouse_input_enabled = false
	pet.scale = Vector2(0.25, 0.25)
	viewport.add_child(pet)
	pet.rig.blink_timer.stop()
	_prepare_pose(pet, specification)
	var phase_offset: float = fposmod(pet.base_time, 6.4)
	var duration: float = specification.duration
	var count := int(ceil(duration * FPS)) + (0 if specification.loop else 1)
	var previous_time := 0.0
	var frames: Array[String] = []
	for index in range(count):
		var frame_time: float = minf(float(index) / FPS, duration)
		if index > 0: pet.step(frame_time - previous_time)
		previous_time = frame_time
		if specification.loop and clip != "drag_hold" and index in [63, 141]:
			pet.rig.blink_once()
			pet.step(0.0)
		await RenderingServer.frame_post_draw
		var image := viewport.get_texture().get_image()
		if image.is_empty():
			push_error("Offscreen renderer returned an empty image for " + clip)
			pet.free()
			return {}
		var relative := "%s/%04d.png" % [clip, index]
		var error := image.save_png(destination.path_join(relative))
		if error != OK:
			push_error("PNG export failed for " + relative)
			pet.free()
			return {}
		frames.append(relative)
	pet.free()
	print("LUNA_CLIP ", clip, " frames=", count, " size=384x576 RGBA")
	return {"fps":FPS, "duration":duration, "phase_offset":phase_offset, "loop":specification.loop, "frames":frames}
