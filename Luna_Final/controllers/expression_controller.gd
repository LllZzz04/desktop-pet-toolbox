extends Node
var additions: Dictionary={}
var eye_transforms: Dictionary={}
@onready var rig: Node2D=$"../Rig"
func _ready() -> void:
	for side in ["L","R"]:
		for mode in ["open","closed"]:
			var name: String="eye_"+side+"_"+mode
			eye_transforms[name]=rig.layers[name].transform
	for name in ["mouth_yawn","mouth_annoyed","mouth_pout","mouth_success","blush","glasses"]:
		var folder: String="accessories" if name=="glasses" else "expressions"
		var path: String="res://assets/"+folder+"/"+name+".svg"
		if not ResourceLoader.exists(path):continue
		var sprite:=Sprite2D.new();sprite.name=name;sprite.texture=load(path)
		sprite.z_as_relative=false;sprite.z_index=25 if name=="glasses" else 21
		sprite.position=Vector2(3,-157) if name=="glasses" else (Vector2(2,-97) if name=="blush" else Vector2(2.5,-73))
		sprite.visible=false;rig.bones.head.add_child(sprite);additions[name]=sprite
		if name=="blush":sprite.material=load("res://assets/expressions/nose_blush_soft.tres")
func apply(values: Dictionary) -> void:
	var closure: float=clampf(values.eye_closure,0.0,1.0)
	var closed: bool=rig.eyes_closed or closure>=0.82
	for side in ["L","R"]:
		for mode in ["open","closed"]:
			var name: String="eye_"+side+"_"+mode
			rig.layers[name].transform=eye_transforms[name]
		rig.layers["eye_"+side+"_open"].visible=not closed
		rig.layers["eye_"+side+"_closed"].visible=closed
		if not closed and closure>0.0:rig.layers["eye_"+side+"_open"].scale.y=maxf(0.12,1.0-closure*0.88)
	var yawn: float=clampf(values.yawn,0.0,1.0)
	var annoyed: float=clampf(values.annoyed,0.0,1.0)
	var pout: float=clampf(values.get("pout",0.0),0.0,1.0)
	var success: float=clampf(values.get("success_smile",0.0),0.0,1.0)
	rig.layers.mouth.modulate.a=1.0-maxf(success,maxf(pout,maxf(yawn,annoyed)))
	rig.layers.mouth.visible=rig.layers.mouth.modulate.a>0.001
	for name in additions:
		var amount: float=values.glasses if name=="glasses" else (yawn if name=="mouth_yawn" else (pout if name=="mouth_pout" else (values.get("blush",0.0) if name=="blush" else annoyed)))
		if name=="mouth_success":amount=success
		additions[name].visible=amount>0.001;additions[name].modulate.a=amount
