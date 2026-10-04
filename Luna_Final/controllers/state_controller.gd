extends Node
const PRIORITY: Dictionary={"idle":0,"idle_variant":10,"attention":20,"click":40,"working":60,"feedback":80,"drag_start":100,"drag_hold":100,"land":100}
var registry: Dictionary={}
var active: RefCounted
var current_name: String="idle"
var variant_remaining: float=20.0
var last_variant: String=""
var working_requested: bool=false
var variant_history: Array[String]=[]
var transition_history: Array[Dictionary]=[]
@onready var pet: Node2D=get_parent()
func configure() -> void:
	registry=JSON.parse_string(FileAccess.get_file_as_string("res://data/stage_registry.json"))
	request("idle",{},true);schedule_variant()
func schedule_variant() -> void:variant_remaining=pet.rng.randf_range(12.0,30.0)
func request(name: String,payload: Dictionary={},force: bool=false) -> bool:
	if not registry.has(name):return false
	if not force and int(PRIORITY[name])<int(PRIORITY[current_name]):return false
	if name==current_name and not force:return false
	if name in ["feedback","drag_start"]:working_requested=false
	var previous: String=current_name
	if active!=null:active.exit()
	active=load(registry[name]).new();active.setup(pet,name);current_name=name
	active.enter(payload)
	transition_history.append({"time":pet.clock,"from":previous,"to":name})
	pet.state_changed.emit(previous,name)
	if name=="idle":schedule_variant()
	return true
func update(delta: float) -> void:
	if active!=null:active.update(delta)
	if current_name=="idle" and pet.random_events_enabled:
		variant_remaining-=delta
		if variant_remaining<=0.0:pet.play_idle_variant()
func set_working(enabled: bool) -> void:
	if enabled and int(PRIORITY[current_name])>60:return
	working_requested=enabled
	if enabled:
		if current_name=="working" and active.exiting:request("working",{},true)
		else:request("working")
	elif current_name=="working" and not active.exiting:request("working",{"exit":true},true)
func return_to_idle() -> void:
	if working_requested:request("working",{},true)
	else:request("idle",{},true)
func choose_variant(requested: String="") -> String:
	var next: String=requested
	if next.is_empty():
		if last_variant.is_empty():next="idle_look_around" if pet.rng.randi_range(0,1)==0 else "idle_yawn"
		else:next="idle_yawn" if last_variant=="idle_look_around" else "idle_look_around"
	return next
