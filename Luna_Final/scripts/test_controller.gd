extends Node2D
@export var automatic_demo: bool=false
var demo_time: float=0.0
var event_index: int=0
var drag_test_time: float=-1.0
var drag_origin: Vector2
var drag_grab: Vector2
var attention_test_until: float=0.0
var attention_phase: float=0.0
var status: Label
var hint: Label
var auto_button: CheckButton
var event_log: Array[String]=[]
var demo_events: Array=[]
@onready var pet: Node2D=$LunaPet
const ACTIONS: Array[String]=["普通待机","左右看看","困倦哈欠","注意鼠标","单击疑问","连续点击","拖拽 / 落地","持板工作","成功庆祝","错误反馈"]
func _ready() -> void:
	demo_events=JSON.parse_string(FileAccess.get_file_as_string("res://data/showcase_timeline.json"))
	pet.state_changed.connect(_state_changed)
	pet.animation_started.connect(_animation_started)
	build_ui()
	if automatic_demo:start_demo()
func build_ui() -> void:
	var canvas:=CanvasLayer.new();add_child(canvas)
	var panel:=PanelContainer.new();panel.position=Vector2(18,18);panel.size=Vector2(300,736);canvas.add_child(panel)
	var style:=StyleBoxFlat.new();style.bg_color=Color(0.16,0.15,0.18,0.95)
	style.border_color=Color(0.5,0.2,0.3);style.set_border_width_all(1);style.set_corner_radius_all(14)
	style.content_margin_left=16;style.content_margin_right=16;style.content_margin_top=14;style.content_margin_bottom=14
	panel.add_theme_stylebox_override("panel",style)
	var box:=VBoxContainer.new();box.add_theme_constant_override("separation",6);panel.add_child(box)
	var font:=SystemFont.new();font.font_names=PackedStringArray(["Microsoft YaHei UI","Microsoft YaHei"])
	box.add_theme_font_override("font",font)
	var title:=Label.new();title.text="Luna · 最终版";title.add_theme_font_size_override("font_size",26);box.add_child(title)
	var subtitle:=Label.new();subtitle.text="已确认动画 · 统一预览";box.add_child(subtitle)
	for i in range(10):
		var button:=Button.new();var key: int=(i+1)%10
		button.text=str(key)+"  ·  "+ACTIONS[i];button.custom_minimum_size=Vector2(265,32)
		button.pressed.connect(trigger.bind(key));box.add_child(button)
	var covers:=HBoxContainer.new();box.add_child(covers)
	for entry in [["Q · 头", "head"],["W · 胸", "chest"],["E · 腿", "legs"]]:
		var button:=Button.new();button.text=entry[0];button.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		button.pressed.connect(trigger_cover.bind(entry[1]));covers.add_child(button)
	auto_button=CheckButton.new();auto_button.text="Space · 自动循环演示";auto_button.button_pressed=automatic_demo
	auto_button.toggled.connect(_auto_toggled);box.add_child(auto_button)
	var debug:=Button.new();debug.text="D · 骨架 / 脚底固定检查";debug.pressed.connect(func():pet.get_node("DebugLayer").toggle());box.add_child(debug)
	status=Label.new();status.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;status.custom_minimum_size=Vector2(265,70);box.add_child(status)
	hint=Label.new();hint.text="同一部位 2 秒内六击：用手遮挡\n头 → 嘟嘴；胸／腿 → 脸红\nQ / W / E：三种遮挡动作测试\n按住并移动：提起，松开：落地";hint.add_theme_font_size_override("font_size",13);box.add_child(hint)
	queue_redraw()
func _draw() -> void:
	var ground: float=60.0+2170.0*0.28
	draw_line(Vector2(340,ground),Vector2(930,ground),Color(0.33,0.31,0.35),1)
	draw_circle(Vector2(870,55),9,Color(0.6,0.19,0.28))
func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:return
	if event.keycode>=KEY_0 and event.keycode<=KEY_9:
		stop_demo();trigger(int(event.keycode-KEY_0));get_viewport().set_input_as_handled()
	elif event.keycode in [KEY_Q,KEY_W,KEY_E]:
		trigger_cover({KEY_Q:"head",KEY_W:"chest",KEY_E:"legs"}[event.keycode]);get_viewport().set_input_as_handled()
	elif event.keycode==KEY_SPACE:auto_button.button_pressed=not auto_button.button_pressed;get_viewport().set_input_as_handled()
	elif event.keycode==KEY_D:pet.get_node("DebugLayer").toggle();get_viewport().set_input_as_handled()
func trigger(key: int) -> void:
	stop_demo()
	match key:
		1:pet.request_idle();pet.set_attention(false,Vector2.ZERO)
		2:pet.play_idle_variant("idle_look_around")
		3:pet.play_idle_variant("idle_yawn")
		4:attention_test_until=pet.clock+3.2;attention_phase=0.0
		5:pet.notify_click(pet.to_global(Vector2(1250,650)))
		6:
			for i in range(6):pet.notify_click(pet.to_global(Vector2(1250,650)))
		7:start_drag_test()
		8:pet.set_working(pet.states.current_name!="working")
		9:pet.notify_success()
		0:pet.notify_error()
func trigger_cover(region: String) -> void:
	stop_demo()
	if int(pet.states.PRIORITY[pet.states.current_name])>40:return
	pet.request_idle()
	var interaction: Node=pet.get_node("InteractionController")
	# Only these preview buttons reset cooldown; real mouse input never bypasses it.
	interaction.click_times.clear();interaction.click_region="";interaction.angry_cooldown_until=0.0
	var points: Dictionary={"head":Vector2(600,650),"chest":Vector2(772,1070),"legs":Vector2(700,1650)}
	for i in range(6):pet.notify_click(pet.rig.to_global(points[region]))
func _auto_toggled(enabled: bool) -> void:
	automatic_demo=enabled
	if enabled:start_demo()
	else:stop_demo()
func start_demo() -> void:
	automatic_demo=true;demo_time=-1.5;event_index=0
	pet.random_events_enabled=false
	pet.set_attention(false,Vector2.ZERO);pet.request_idle()
	if is_instance_valid(auto_button):auto_button.set_pressed_no_signal(true)
func stop_demo() -> void:
	automatic_demo=false;pet.random_events_enabled=true
	if is_instance_valid(auto_button):auto_button.set_pressed_no_signal(false)
func start_drag_test() -> void:
	drag_origin=pet.global_position;drag_grab=pet.to_global(Vector2(768,950))
	drag_test_time=0.0;pet.start_drag(drag_grab)
func update_drag_test(delta: float) -> void:
	if drag_test_time<0:return
	drag_test_time+=delta
	var time: float=minf(drag_test_time,3.2)
	# Smooth round trip, then hold the original horizontal location before release.
	var movement: Vector2=Vector2(55*sin(TAU*time/2.5),-65*sin(PI*minf(time/2.5,1.0))) if time<2.5 else Vector2.ZERO
	pet.update_drag(drag_grab+movement)
	if drag_test_time>=3.2:pet.end_drag();drag_test_time=-1.0
func dispatch(event: Dictionary) -> void:
	match String(event.type):
		"variant":pet.play_idle_variant(event.name)
		"attention":
			attention_test_until=pet.clock+float(event.get("duration",0.0));attention_phase=0.0
		"click":
			var region: String=event.get("region","head")
			var points: Dictionary={"head":Vector2(600,650),"chest":Vector2(772,1070),"legs":Vector2(700,1650)}
			for i in range(int(event.get("count",1))):pet.notify_click(pet.rig.to_global(points[region]))
		"drag":start_drag_test()
		"working":pet.set_working(event.enabled)
		"success":pet.notify_success()
		"error":pet.notify_error()
		"idle":pet.request_idle()
func _process(delta: float) -> void:
	var interaction: Node=pet.get_node("InteractionController")
	interaction.mouse_input_enabled=not automatic_demo and drag_test_time<0 and pet.clock>=attention_test_until
	update_drag_test(delta)
	if pet.clock<attention_test_until:
		attention_phase+=delta
		pet.set_attention(true,pet.to_global(Vector2(772+500*sin(attention_phase*2.4-1.1),650)))
	elif interaction.attention_enabled and not interaction.mouse_input_enabled:pet.set_attention(false,Vector2.ZERO)
	if automatic_demo:
		demo_time+=delta
		while event_index<demo_events.size() and demo_time>=float(demo_events[event_index].time):dispatch(demo_events[event_index]);event_index+=1
		if demo_time>=44.4:demo_time-=44.4;event_index=0
	if is_instance_valid(status):
		status.text="State: "+pet.states.current_name+"\nClip: "+("idle_normal" if pet.motion.clip.is_empty() else pet.motion.clip)+"\nFoot Lock: "+("%.3f px"%pet.foot_lock.maximum_drift() if pet.foot_lock.locked else "悬空")
func _state_changed(previous: String,current: String) -> void:
	event_log.append(previous+" → "+current)
	if event_log.size()>40:event_log.pop_front()
func _animation_started(animation: String) -> void:pass
