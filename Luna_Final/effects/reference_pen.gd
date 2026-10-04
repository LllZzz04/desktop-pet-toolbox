extends Node2D
## A slender black/red/silver pen held by the screen-left fist, pointing into the board.
func _draw() -> void:
	draw_line(Vector2(-35,10),Vector2(-35,161),Color("211e25"),7.0,true)
	draw_line(Vector2(-37,12),Vector2(-37,158),Color("bfb3c0"),1.4,true)
	draw_line(Vector2(-34,19),Vector2(-34,39),Color("8b2c42"),2.0,true)
	draw_line(Vector2(-39,49),Vector2(-31,49),Color("8d808c"),1.3,true)
	draw_colored_polygon(PackedVector2Array([Vector2(-38,162),Vector2(-32,162),Vector2(-35,175)]),Color("bcb1bf"))
	draw_line(Vector2(-35,171),Vector2(-35,175),Color("d0b9be"),1.6,true)
