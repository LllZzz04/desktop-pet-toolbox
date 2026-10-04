extends Node2D
## Only the short end of the stylus is visible in front of the tablet.
## Shared rigid hand transform with the occluded shaft; never an independent pen.
func _draw() -> void:
	draw_line(Vector2(-28,64),Vector2(-28,124),Color("25242b"),8.0,true)
	draw_line(Vector2(-30,65),Vector2(-30,123),Color("d8d3d4"),2.3,true)
	draw_line(Vector2(-33,124),Vector2(-23,124),Color("a62b43"),2.0,true)
	draw_colored_polygon(PackedVector2Array([Vector2(-32,125),Vector2(-24,125),Vector2(-28,140)]),Color("d9d4d5"))
	draw_line(Vector2(-28,136),Vector2(-28,140),Color("82253d"),2.0,true)
