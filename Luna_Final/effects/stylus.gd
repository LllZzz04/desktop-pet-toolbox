extends Node2D
## Tip is local (-28,140), shared with the writing contact calculation.
func _draw() -> void:
	draw_line(Vector2(-28,-6),Vector2(-28,121),Color("25242b"),9.0,true)
	draw_line(Vector2(-30,-1),Vector2(-30,115),Color("d8d3d4"),2.5,true)
	draw_line(Vector2(-27,7),Vector2(-27,38),Color("a62b43"),3.0,true)
	draw_line(Vector2(-34,46),Vector2(-22,46),Color("ddd7d7"),2.0,true)
	draw_line(Vector2(-34,115),Vector2(-22,115),Color("b9b1b5"),2.0,true)
	draw_colored_polygon(PackedVector2Array([Vector2(-33,122),Vector2(-23,122),Vector2(-28,140)]),Color("d9d4d5"))
	draw_line(Vector2(-28,135),Vector2(-28,140),Color("82253d"),2.0,true)
	draw_arc(Vector2(-27,-12),7,0.45,5.6,20,Color("d9d4d5"),2,true)
