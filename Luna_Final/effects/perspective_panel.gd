extends Sprite2D
## True projective board surface. Logical page coordinates remain 360 x 230.
const CORNERS := [Vector2(-226,-82),Vector2(220,-104),Vector2(190,88),Vector2(-210,108)]
var surface_mesh: Polygon2D
var coefficients: PackedFloat64Array
func _ready() -> void:
	var source: Texture2D=texture;texture=null
	var p0: Vector2=CORNERS[0];var p1: Vector2=CORNERS[1];var p2: Vector2=CORNERS[2];var p3: Vector2=CORNERS[3]
	var dx1: float=p1.x-p2.x;var dx2: float=p3.x-p2.x;var dx3: float=p0.x-p1.x+p2.x-p3.x
	var dy1: float=p1.y-p2.y;var dy2: float=p3.y-p2.y;var dy3: float=p0.y-p1.y+p2.y-p3.y
	var den: float=dx1*dy2-dx2*dy1
	var g: float=(dx3*dy2-dx2*dy3)/den;var h: float=(dx1*dy3-dx3*dy1)/den
	coefficients=PackedFloat64Array([p1.x-p0.x+g*p1.x,p3.x-p0.x+h*p3.x,p0.x,p1.y-p0.y+g*p1.y,p3.y-p0.y+h*p3.y,p0.y,g,h])
	surface_mesh=Polygon2D.new();surface_mesh.name="ProjectedBoard";surface_mesh.texture=source
	var points:=PackedVector2Array();var uv:=PackedVector2Array();var faces: Array[PackedInt32Array]=[]
	for y in range(15):
		for x in range(23):
			var q:=Vector2(x/22.0,y/14.0)
			points.append(surface_to_local(q*Vector2(360,230)-Vector2(180,115)));uv.append(q*source.get_size())
	for y in range(14):
		for x in range(22):
			var a: int=y*23+x;faces.append(PackedInt32Array([a,a+1,a+23]));faces.append(PackedInt32Array([a+1,a+24,a+23]))
	surface_mesh.polygon=points;surface_mesh.uv=uv;surface_mesh.polygons=faces;add_child(surface_mesh)
	queue_redraw()
func surface_to_local(p: Vector2) -> Vector2:
	var u: float=(p.x+180.0)/360.0;var v: float=(p.y+115.0)/230.0;var c:=coefficients
	var den: float=c[6]*u+c[7]*v+1.0
	return Vector2((c[0]*u+c[1]*v+c[2])/den,(c[3]*u+c[4]*v+c[5])/den)
func local_to_surface(p: Vector2) -> Vector2:
	var c:=coefficients;var a: float=c[0]-p.x*c[6];var b: float=c[1]-p.x*c[7]
	var d: float=c[3]-p.y*c[6];var e: float=c[4]-p.y*c[7];var x: float=p.x-c[2];var y: float=p.y-c[5]
	var den: float=a*e-b*d
	return Vector2((x*e-b*y)/den*360.0-180.0,(a*y-x*d)/den*230.0-115.0)
func surface_to_world(p: Vector2) -> Vector2:return to_global(surface_to_local(p))
func world_to_surface(p: Vector2) -> Vector2:return local_to_surface(to_local(p))
func world_corners() -> Array:
	var result: Array=[]
	for p in CORNERS:result.append(to_global(p))
	return result
func _draw() -> void:
	# Restrained thickness along the near bottom edge and right side.
	var a: Vector2=CORNERS[3]+Vector2(13,-1);var b: Vector2=CORNERS[2]-Vector2(13,1)
	draw_line(a+Vector2(0,4),b+Vector2(0,4),Color("17171c"),6.0,true)
	draw_line(a+Vector2(0,3),b+Vector2(0,3),Color("625c65"),2.0,true)
	draw_line(CORNERS[1]+Vector2(-1,8),CORNERS[2]+Vector2(0,-8),Color("514a53"),3.0,true)
