extends Node2D
signal state_changed(previous_state: String,current_state: String)
signal animation_started(animation_name: String)
signal animation_finished(animation_name: String)
@export var automatic_processing: bool=true
@export var random_events_enabled: bool=true
var clock: float=0.0
var base_time: float=0.0
var rng:=RandomNumberGenerator.new()
@onready var rig: Node2D=$Rig
@onready var states: Node=$StateController
@onready var motion: Node=$MotionController
@onready var expressions: Node=$ExpressionController
@onready var composer: Node=$PoseComposer
@onready var foot_lock: Node=$FootLockController
@onready var blink_player: AnimationPlayer=$Rig/BlinkPlayer
func _ready() -> void:
	process_priority=100
	# Keep blink separate, but compose forced expressions after its independent tick.
	blink_player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	blink_player.animation_started.connect(_on_blink_started)
	blink_player.animation_finished.connect(_on_blink_finished)
	rng.randomize();states.configure()
	if random_events_enabled:rig._schedule_blink()
	composer.apply(motion.output,0.0)
func _process(delta: float) -> void:
	if automatic_processing:step(minf(delta,0.05))
func _on_blink_started(animation: String) -> void:animation_started.emit(animation)
func _on_blink_finished(animation: String) -> void:animation_finished.emit(animation)
func step(delta: float) -> void:
	clock+=delta;base_time+=delta
	states.update(delta);motion.advance(delta)
	if blink_player.is_playing():blink_player.advance(delta)
	composer.apply(motion.output,base_time)
	foot_lock.finish_frame()
func play_idle_variant(requested: String="") -> bool:
	if states.current_name!="idle":return false
	var animation: String=states.choose_variant(requested)
	if animation not in ["idle_look_around","idle_yawn"]:return false
	if not states.request("idle_variant",{"animation":animation}):return false
	states.last_variant=animation;states.variant_history.append(animation)
	return true
func set_attention(enabled: bool,mouse_position: Vector2) -> void:
	if has_node("InteractionController"):get_node("InteractionController").set_attention(enabled,mouse_position)
func notify_click(mouse_position: Vector2) -> void:
	if has_node("InteractionController"):get_node("InteractionController").notify_click(mouse_position)
func start_drag(mouse_position: Vector2) -> void:
	if has_node("DragController"):get_node("DragController").start_drag(mouse_position)
func update_drag(mouse_position: Vector2) -> void:
	if has_node("DragController"):get_node("DragController").update_drag(mouse_position)
func end_drag() -> void:
	if has_node("DragController"):get_node("DragController").end_drag()
func set_working(enabled: bool) -> void:
	states.set_working(enabled)
func notify_success() -> void:states.request("feedback",{"animation":"feedback_success"})
func notify_error() -> void:states.request("feedback",{"animation":"feedback_error"})
func request_idle() -> void:
	states.working_requested=false
	match states.current_name:
		"drag_start","drag_hold":end_drag()
		"land","feedback":pass
		"working":set_working(false)
		_:states.request("idle",{"transition":0.3},true)
func rest_pose() -> void:
	motion.reset();rig.rest_pose();rig.transform=Transform2D.IDENTITY
	expressions.apply(motion.output)
	if has_node("EffectLayer"):get_node("EffectLayer").apply(motion.output)
	for side in ["L","R"]:
		rig.layers["arm_"+side].visible=true;rig.layers["arm_"+side+"_deform"].visible=false
	if has_node("WritingController"):get_node("WritingController").apply(motion.output,0.0)
	if has_node("ClickCoverController"):get_node("ClickCoverController").reset()
