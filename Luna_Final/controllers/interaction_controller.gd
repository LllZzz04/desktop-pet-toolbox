extends Node
@export var mouse_input_enabled: bool=true
var attention_enabled: bool=false
var mouse_position: Vector2=Vector2.ZERO
var click_times: Array[float]=[]
var click_region: String=""
var region_config: Dictionary={}
var angry_cooldown_until: float=0.0
var button_down: bool=false
var press_position: Vector2=Vector2.ZERO
var dragging: bool=false
@onready var pet: Node2D=get_parent()
func _ready() -> void:
	region_config=JSON.parse_string(FileAccess.get_file_as_string("res://data/click_regions.json"))
func region_at(world_point: Vector2) -> String:
	var point: Vector2=pet.rig.to_local(world_point)
	for entry in region_config.regions:
		var rect: Array=entry.rect
		if Rect2(rect[0],rect[1],rect[2],rect[3]).has_point(point):return entry.name
	return ""
func set_attention(enabled: bool,position: Vector2) -> void:
	attention_enabled=enabled;mouse_position=position
	if enabled:pet.states.request("attention")
	elif pet.states.current_name=="attention":pet.states.request("idle",{"transition":0.4},true)
func notify_click(position: Vector2) -> void:
	if int(pet.states.PRIORITY[pet.states.current_name])>40:return
	var region: String=region_at(position)
	if region.is_empty():return
	mouse_position=position
	if region!=click_region:
		click_times.clear();click_region=region
	# Runtime windows use monotonic wall time, even when render frames are delayed.
	var now: float=Time.get_ticks_msec()/1000.0 if pet.automatic_processing else pet.clock
	while not click_times.is_empty() and now-click_times[0]>2.0:click_times.pop_front()
	click_times.append(now)
	if now<angry_cooldown_until:return
	var recent: int=0
	for time in click_times:
		if now-time<=1.0:recent+=1
	var animation: String="click_question"
	if click_times.size()>=int(region_config.angry_count):animation="click_angry_"+region
	elif recent>=3:animation="click_annoyed"
	var ranks: Dictionary={"click_question":1,"click_annoyed":2,"click_angry":3}
	if pet.states.current_name=="click" and int(ranks["click_angry"] if animation.begins_with("click_angry") else ranks[animation])<=int(ranks["click_angry"] if pet.motion.clip.begins_with("click_angry") else ranks.get(pet.motion.clip,0)):return
	if animation.begins_with("click_angry"):angry_cooldown_until=now+float(region_config.cooldown_seconds)
	pet.states.request("click",{"animation":animation,"mouse":position,"region":region},true)
func _process(_delta: float) -> void:
	if not mouse_input_enabled or not pet.automatic_processing:return
	var point: Vector2=pet.get_global_mouse_position()
	if dragging:pet.update_drag(point);return
	var native: Vector2=pet.to_local(point)
	var near: bool=Rect2(170,100,1210,2110).has_point(native)
	if near!=attention_enabled:set_attention(near,point)
	elif near:
		mouse_position=point
		if pet.states.current_name=="idle":pet.states.request("attention")
func _unhandled_input(event: InputEvent) -> void:
	if not mouse_input_enabled:return
	if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
		if event.pressed:
			var point: Vector2=pet.get_global_mouse_position()
			if Rect2(170,100,1210,2110).has_point(pet.to_local(point)):
				button_down=true;press_position=point;dragging=false
		elif button_down:
			button_down=false
			if dragging:pet.end_drag();dragging=false
			else:notify_click(pet.get_global_mouse_position())
	elif event is InputEventMouseMotion and button_down:
		var point: Vector2=pet.get_global_mouse_position()
		if not dragging and point.distance_to(press_position)>5.0 and pet.has_node("DragController"):
			dragging=true;pet.start_drag(press_position)
		if dragging:pet.update_drag(point)
