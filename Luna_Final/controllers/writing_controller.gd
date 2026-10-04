extends Node2D
## Working-only authored grip: the fingers and pen share one texture and transform.
## The board occludes both hands and the pen wherever their silhouettes overlap.
const INK_ENABLED: bool=false
const WRITING_SIDE: String="R"
const SUPPORT_SIDE: String="L"
const Asset=preload("res://controllers/working_hand_asset.gd")
var config: Dictionary
var GRIP: Vector2
var TIP: Vector2
var CAP: Vector2
var pen: Node2D
var nib: Node2D
var fingertips: Sprite2D
var support_grip: Polygon2D
var support_front: Polygon2D
var arm_pose: Node2D
var ink: Node2D
var grip_mesh: Sprite2D
var strokes: Array[PackedVector2Array]=[]
var pen_down: bool=false
var previous_page: int=-1
var page: int=0
var tip_panel: Vector2=Vector2.ZERO
var tip_world: Vector2=Vector2.ZERO
var contact_valid: bool=true
@onready var pet: Node2D=get_parent()
@onready var rig: Node2D=$"../Rig"
func _ready() -> void:
	config=Asset.read();GRIP=Asset.local(config,"grip_pixel");TIP=Asset.local(config,"tip_pixel");CAP=Asset.local(config,"cap_pixel")
	# A coordinate marker, not a second drawn pen. The actual pen is in the sprite.
	pen=Node2D.new();pen.name="AuthoredGripCoordinates";add_child(pen)
	nib=Node2D.new();nib.name="VisibleStylusNib";nib.z_index=39;nib.z_as_relative=false
	nib.set_script(load("res://effects/stylus_nib.gd"));add_child(nib);nib.visible=false
	ink=Node2D.new();ink.name="HandwritingInk";ink.z_index=39;ink.z_as_relative=false
	ink.set_script(load("res://effects/handwriting_ink.gd"));add_child(ink)
	grip_mesh=make_grip_sprite(false);grip_mesh.name="WorkingWritingWristRear";grip_mesh.z_index=39
	rig.bones["hand_"+WRITING_SIDE].add_child(grip_mesh);grip_mesh.visible=false;pen.visible=false;ink.visible=false
	var uv:=PackedVector2Array();var faces: Array[PackedInt32Array]=[]
	for y in range(20):
		for x in range(17):
			var pixel:=Vector2(174.0*x/16.0,199.0*y/19.0)
			uv.append(pixel)
	for y in range(19):
		for x in range(16):
			var a: int=y*17+x;faces.append(PackedInt32Array([a,a+1,a+17]));faces.append(PackedInt32Array([a+1,a+18,a+17]))
	support_grip=Polygon2D.new();support_grip.name="SupportingHand";support_grip.z_index=39;support_grip.z_as_relative=false
	support_grip.texture=rig.layers["hand_"+SUPPORT_SIDE].texture;support_grip.uv=uv;support_grip.polygons=faces
	rig.bones["hand_"+SUPPORT_SIDE].add_child(support_grip);support_grip.visible=false
	support_front=Polygon2D.new();support_front.name="ReferenceBoardSupportingPalm";support_front.z_index=39;support_front.z_as_relative=false
	support_front.texture=support_grip.texture;support_front.uv=uv;support_front.polygons=faces
	var support_shader:=Shader.new();support_shader.code="shader_type canvas_item; void fragment(){ }"
	var support_material:=ShaderMaterial.new();support_material.shader=support_shader;support_front.material=support_material
	rig.bones["hand_"+SUPPORT_SIDE].add_child(support_front);support_front.visible=false
	arm_pose=Node2D.new();arm_pose.name="WorkingArmPose";arm_pose.set_script(load("res://controllers/working_arm_pose.gd"));add_child(arm_pose)
	fingertips=make_grip_sprite(true);fingertips.name="WorkingAuthoredWritingGrip";fingertips.z_index=39
	rig.bones["hand_"+WRITING_SIDE].add_child(fingertips);fingertips.visible=false
func make_grip_sprite(front: bool) -> Sprite2D:
	var sprite:=Sprite2D.new();sprite.centered=false;sprite.z_as_relative=false
	sprite.texture=load(config.texture);sprite.scale=Vector2.ONE*float(config.pixel_scale)
	sprite.position=-Asset.point(config,"wrist_pixel")*float(config.pixel_scale)
	sprite.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	# Preserve the authored sprite alpha. Its draw order is behind the board.
	var shader:=Shader.new()
	shader.code="shader_type canvas_item; uniform bool front; uniform vec2 cut; void fragment(){vec2 p=UV/TEXTURE_PIXEL_SIZE; bool rear=p.x<cut.x&&p.y>cut.y; if((front&&rear)||(!front&&!rear)){COLOR.a=0.;}}"
	var material:=ShaderMaterial.new();material.shader=shader
	material.set_shader_parameter("front",front)
	material.set_shader_parameter("cut",Vector2(config.rear_cut_x_pixel,config.rear_cut_y_pixel))
	sprite.material=material;return sprite
func apply(values: Dictionary,clock: float) -> void:
	var amount: float=clampf(maxf(values.writing,values.working_fold),0.0,1.0)
	var visibility: float=clampf(values.writing,0.0,1.0)
	var prop_visibility: float=visibility*smoothstep(0.88,1.0,clampf(values.working_fold,0.0,1.0))
	pen.visible=prop_visibility>0.001;ink.visible=pen.visible and INK_ENABLED;nib.visible=false
	pen.modulate.a=prop_visibility;ink.modulate.a=prop_visibility;nib.modulate.a=prop_visibility
	var grip_visibility: float=smoothstep(0.70,1.0,amount)
	fingertips.visible=grip_visibility>0.001;fingertips.modulate.a=grip_visibility
	grip_mesh.visible=false;grip_mesh.modulate.a=grip_visibility
	support_front.visible=amount>0.001;support_front.modulate.a=amount
	# The old hand returns unchanged in every non-Working state.
	rig.layers["hand_"+WRITING_SIDE].visible=grip_visibility<0.999
	rig.layers["hand_"+WRITING_SIDE].modulate.a=1.0-grip_visibility
	rig.layers["hand_"+SUPPORT_SIDE].visible=amount<0.001;support_grip.visible=false
	var left:=PackedVector2Array()
	for uv in support_grip.uv:
		var p: Vector2=uv-Vector2(47,38)
		var w: float=smoothstep(55.0,110.0,p.y)*amount
		left.append(Vector2(40+(p.x-40)*(1-w*0.12),lerpf(p.y,55+maxf(p.y-55,0)*0.73,amount) if p.y>55 else p.y))
	support_grip.polygon=left
	support_front.polygon=left
	var panel=pet.get_node("EffectLayer").sprites.panel
	arm_pose.apply(clampf(values.working_fold,0.0,1.0),values,panel)
	if not pen.visible:
		strokes.clear();previous_page=-1;pen_down=false;ink.strokes=strokes;ink.queue_redraw();return
	var hand: Bone2D=rig.bones["hand_"+WRITING_SIDE]
	pen.global_transform=hand.global_transform;nib.global_transform=pen.global_transform
	ink.global_transform=panel.global_transform
	ink.surface=panel
	tip_world=pen.to_global(TIP);tip_panel=panel.world_to_surface(tip_world)
	page=int(floor(clock/3.2))
	ink.modulate.a=amount*(1.0-smoothstep(2.72,3.18,fposmod(clock,3.2)))
	if page!=previous_page:
		previous_page=page;strokes.clear();pen_down=false
	var touching: bool=amount>0.97 and values.pen_contact>0.75 and pet.motion.clip=="working_loop"
	var inside: bool=Rect2(-123,-100,253,178).has_point(tip_panel)
	if touching:
		contact_valid=contact_valid and inside
		if inside and INK_ENABLED:
			if not pen_down:strokes.append(PackedVector2Array())
			var path: PackedVector2Array=strokes[-1]
			if path.is_empty() or path[-1].distance_to(tip_panel)>0.35:path.append(tip_panel)
			strokes[-1]=path
	pen_down=touching and inside
	ink.contact_point=tip_panel;ink.contact=pen_down and INK_ENABLED
	ink.strokes=strokes;ink.queue_redraw()
