extends Node2D
var show_bones: bool=false
@onready var pet: Node2D=get_parent()
func _process(_delta: float) -> void:
	if show_bones:queue_redraw()
func toggle() -> void:show_bones=not show_bones;queue_redraw()
func _draw() -> void:
	if not show_bones:return
	for name in pet.rig.bones:
		var bone: Bone2D=pet.rig.bones[name]
		var point: Vector2=to_local(bone.global_position)
		var color:=Color(0.4,0.8,1.0,0.7)
		if String(name).begins_with("foot"):color=Color(0.4,1.0,0.6,0.9)
		if bone.get_parent() is Bone2D:draw_line(to_local(bone.get_parent().global_position),point,color,5.0)
		draw_circle(point,8,color)
