extends Node2D
@export var effect_scale: float=1.0
@export var opacity: float=1.0
@export var offset: Vector2=Vector2.ZERO
var sprites: Dictionary={}
const LOCATIONS: Dictionary={"question":Vector2(1085,290),"anger":Vector2(1055,420),"exclamation":Vector2(470,410),"sweat":Vector2(1100,585),"check":Vector2(1180,395),"panel":Vector2(774,1186),"success_star_1":Vector2(1120,290),"success_star_2":Vector2(1290,360),"success_star_3":Vector2(1230,495)}
@onready var rig: Node2D=$"../Rig"
func _ready() -> void:
	for name in LOCATIONS:
		var file: String="res://assets/accessories/writing_pad.svg" if name=="panel" else "res://effects/"+name+".svg"
		if name.begins_with("success_star_"):file="res://effects/success_sparkle.svg"
		if not ResourceLoader.exists(file):continue
		var sprite:=Sprite2D.new();sprite.name=name;sprite.texture=load(file)
		if name=="panel":sprite.set_script(load("res://effects/perspective_panel.gd"))
		sprite.z_as_relative=false;sprite.z_index=40 if name=="panel" else 60
		sprite.visible=false;add_child(sprite);sprites[name]=sprite
func apply(values: Dictionary) -> void:
	for name in sprites:
		var amount: float=clampf(values[name]*opacity,0.0,1.0)
		var sprite: Sprite2D=sprites[name]
		sprite.visible=amount>0.001;sprite.modulate.a=amount
		var anchor: Bone2D=rig.bones.chest if name=="panel" else rig.bones.head
		var pivot:=Vector2(768,965) if name=="panel" else Vector2(772,842)
		sprite.position=to_local(anchor.to_global(LOCATIONS[name]-pivot))+offset
		if name=="panel":sprite.position.y+=values.panel_y
		sprite.scale=Vector2.ONE*effect_scale*(0.9+amount*0.1)
		if name=="panel":sprite.scale*=1.12
		sprite.rotation=-0.038 if name=="panel" else 0.0
		if name=="check":
			sprite.scale=Vector2.ONE*effect_scale*values.get("check_scale",1.0)
			sprite.rotation=deg_to_rad(values.get("check_rotation",0.0))
		elif name.begins_with("success_star_"):
			sprite.scale=Vector2.ONE*effect_scale*(0.45+amount*0.65)
			sprite.rotation=deg_to_rad((int(name.right(1))-2)*9.0+amount*5.0)
