extends Node2D
var strokes: Array[PackedVector2Array]=[]
var surface: Node
var contact_point:=Vector2.ZERO
var contact: bool=false
func _draw() -> void:
	if surface==null:return
	if contact:draw_circle(surface.surface_to_local(contact_point),2.5,Color(0.1,0.08,0.12,0.22))
	for stroke in strokes:
		if stroke.size()>1:
			var projected:=PackedVector2Array()
			for p in stroke:projected.append(surface.surface_to_local(p))
			draw_polyline(projected,Color("cbb9c4"),2.1,true)
