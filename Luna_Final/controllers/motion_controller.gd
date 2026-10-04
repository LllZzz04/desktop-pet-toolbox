extends Node
var clip: String=""
var clock: float=0.0
var blend_clock: float=0.0
var blend_duration: float=0.0
var overrides: Dictionary={}
var output: Dictionary={}
var blend_from: Dictionary={}
var catalog: Dictionary={}
@onready var pet: Node2D=get_parent()
@onready var channels: Node=$"../Motion"
@onready var player: AnimationPlayer=$"../AnimationPlayer"
func _ready() -> void:
	output=channels.DEFAULTS.duplicate();blend_from=output.duplicate()
	catalog=JSON.parse_string(FileAccess.get_file_as_string("res://data/animation_catalog.json"))
	if not player.has_animation_library(""):
		var library:=AnimationLibrary.new()
		for name in catalog:library.add_animation(name,load(catalog[name].resource))
		player.add_animation_library("",library)
	# New region reactions are registered without rewriting the protected library.
	var library: AnimationLibrary=player.get_animation_library("")
	for name in catalog:
		if not library.has_animation(name):library.add_animation(name,load(catalog[name].resource))
func play(name: String,transition: float=0.2) -> void:
	clip=name;clock=0.0;blend_clock=0.0;blend_duration=transition
	blend_from=output.duplicate();overrides.clear()
	pet.animation_started.emit("idle_normal" if name.is_empty() else name)
func length() -> float:
	return 0.0 if clip.is_empty() else float(catalog[clip].length)
func advance(delta: float) -> void:
	clock+=delta;blend_clock+=delta
	channels.reset()
	if not clip.is_empty():
		var duration: float=length()
		var time: float=fposmod(clock,duration) if catalog[clip].loop else minf(clock,duration)
		player.play(clip);player.seek(time,true);player.pause()
	var raw: Dictionary=channels.values()
	# Exit starts from the currently sampled handwriting pose, including wrist phase.
	if clip=="working_exit":
		var recovery: float=smoothstep(0.0,1.0,clampf(clock/length(),0.0,1.0))
		for key in raw:raw[key]=lerpf(blend_from.get(key,raw[key]),channels.DEFAULTS[key],recovery)
	for name in overrides:raw[name]=float(raw.get(name,0.0))+float(overrides[name])
	var weight: float=1.0 if blend_duration<=0.0 else smoothstep(0.0,1.0,minf(blend_clock/blend_duration,1.0))
	for name in raw:
		var channel_weight: float=weight
		if name.begins_with("shoulder_") or name.begins_with("forearm_") or name.begins_with("hand_") or name in ["working_fold","write_x","write_y"]:
			var arm_duration: float=maxf(blend_duration,0.30)
			if clip.begins_with("drag_"):arm_duration=maxf(blend_duration,0.18)
			if float(blend_from.get("working_fold",0.0))>0.01 and clip!="working_exit":
				arm_duration=maxf(arm_duration,0.54)
			if clip=="feedback_success":
				arm_duration=maxf(blend_duration,0.44 if float(blend_from.get("working_fold",0.0))>0.01 else 0.10)
			channel_weight=smoothstep(0.0,1.0,minf(blend_clock/arm_duration,1.0))
		output[name]=lerpf(float(blend_from.get(name,raw[name])),float(raw[name]),channel_weight)
func reset() -> void:
	clip="";clock=0;blend_clock=0;blend_duration=0;overrides.clear()
	channels.reset();output=channels.values();blend_from=output.duplicate()
