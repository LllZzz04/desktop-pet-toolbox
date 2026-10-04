extends Node2D
## Two AnimationPlayers keep breathing and random blinks independent.
@export var autoplay_enabled: bool = true
@export var random_blink_enabled: bool = true
@export var eyes_closed: bool = false:
	set(value):
		eyes_closed = value
		_apply_eye_state()

var bones: Dictionary = {}
var layers: Dictionary = {}
var random_generator := RandomNumberGenerator.new()
var blink_intervals: Array[float] = []
@onready var idle_player: AnimationPlayer = $AnimationPlayer
@onready var blink_player: AnimationPlayer = $BlinkPlayer
@onready var blink_timer: Timer = $BlinkTimer

func _ready() -> void:
	_collect_nodes(self)
	random_generator.randomize()
	blink_timer.timeout.connect(_on_blink_timeout)
	_apply_eye_state()
	if autoplay_enabled:
		idle_player.play("idle_loop")
	if autoplay_enabled and random_blink_enabled:
		_schedule_blink()

func _collect_nodes(node: Node) -> void:
	if node is Bone2D:
		bones[String(node.name)] = node
	if node is Sprite2D or node is Polygon2D:
		layers[String(node.name)] = node
	for child in node.get_children():
		_collect_nodes(child)

func _apply_eye_state() -> void:
	# Both eye states are changed in the same call, before the next render.
	for side in ["L", "R"]:
		var open_eye := get_node_or_null("%eye_" + side + "_open")
		var closed_eye := get_node_or_null("%eye_" + side + "_closed")
		if open_eye != null and closed_eye != null:
			open_eye.visible = not eyes_closed
			closed_eye.visible = eyes_closed

func _schedule_blink() -> void:
	var delay := random_generator.randf_range(2.5, 6.5)
	blink_intervals.append(delay)
	if blink_intervals.size() > 64:
		blink_intervals.pop_front()
	blink_timer.start(delay)

func _on_blink_timeout() -> void:
	blink_once()
	# Schedule from this blink's start, so start-to-start stays 2.5–6.5 seconds.
	if random_blink_enabled:
		_schedule_blink()

func blink_once() -> void:
	blink_player.play("blink_once")

func rest_pose() -> void:
	idle_player.stop()
	blink_player.stop()
	blink_timer.stop()
	for bone in bones.values():
		bone.transform = bone.rest
	eyes_closed = false

func sample_idle(time: float) -> void:
	idle_player.play("idle_loop")
	idle_player.seek(time, true)
	idle_player.pause()

func eye_states_valid() -> bool:
	for side in ["L", "R"]:
		if layers["eye_" + side + "_open"].visible == layers["eye_" + side + "_closed"].visible:
			return false
	return true

