extends Node2D
## Working-only projection of the original sleeves onto connected S -> E -> W chains.
## Rigid UV pieces keep positive triangle orientation even at a folded elbow.
const REST := {
	"L":{"S":Vector2(930,870),"E":Vector2(1060,1100),"W":Vector2(1182,1276),"crop":Vector2(869,817)},
	"R":{"S":Vector2(610,870),"E":Vector2(480,1100),"W":Vector2(359,1276),"crop":Vector2(276,817)}
}
const TARGET := {
	"L":{"E":Vector2(1070,1260),"W":Vector2(950,1280),"wrist_bend":0.0},
	"R":{"E":Vector2(465,1230),"W":Vector2(630,1050),"wrist_bend":0.0}
}
const Asset=preload("res://controllers/working_hand_asset.gd")
var hand_config: Dictionary
var chains: Dictionary={}
var controls: Dictionary={}
var meshes: Array[Polygon2D]=[]
@onready var pet: Node2D=get_parent().get_parent()
@onready var rig: Node2D=pet.get_node("Rig")
func _ready() -> void:
	hand_config=Asset.read()
	for side in ["L","R"]:
		var upper:=Node2D.new();upper.name="WorkShoulder_"+side;add_child(upper)
		var fore:=Node2D.new();fore.name="WorkElbow_"+side;upper.add_child(fore)
		var wrist:=Node2D.new();wrist.name="WorkWrist_"+side;fore.add_child(wrist)
		chains[side]={"upper":upper,"fore":fore,"wrist":wrist,"polygons":[]}
		for part in range(3):
			var poly:=Polygon2D.new();poly.name=["UpperSleeve_","ForeSleeve_","CuffRear_"][part]+side
			poly.texture=rig.layers["arm_"+side].texture;poly.z_as_relative=false
			# Every sleeve pixel is behind the opaque panel, including the wrist cuff.
			poly.z_index=(17 if side=="L" else 16) if part==0 else 35
			var anchor: Vector2=REST[side].S if part==0 else REST[side].E
			var uv:=PackedVector2Array([Vector2.ZERO,Vector2(389,0),Vector2(389,560),Vector2(0,560)])
			var vertices:=PackedVector2Array()
			for p in uv:vertices.append(p+REST[side].crop-anchor)
			poly.polygon=vertices;poly.uv=uv
			var shader:=Shader.new()
			shader.code="shader_type canvas_item; uniform vec2 origin; uniform vec2 shoulder; uniform vec2 axis; uniform float split; uniform float overlap=0.; uniform int part; uniform sampler2D hand_texture; uniform vec2 hand_origin; void fragment(){ vec2 p=UV/TEXTURE_PIXEL_SIZE+origin; float s=dot(p-shoulder,axis); float a=1.; if(part==0){a=1.-smoothstep(split+overlap-5.,split+overlap,s);}else{a=smoothstep(split-overlap,split-overlap+5.,s); if(part==1){a*=1.-step(350.,s);}else{a*=step(350.,s);vec2 q=(p-hand_origin)/vec2(174.,199.); if(q.x>=0.&&q.x<=1.&&q.y>=0.&&q.y<=1.){a*=1.-texture(hand_texture,q).a;}}} COLOR.a*=a; }"
			var mat:=ShaderMaterial.new();mat.shader=shader
			var axis: Vector2=(REST[side].W-REST[side].S).normalized()
			mat.set_shader_parameter("origin",REST[side].crop);mat.set_shader_parameter("shoulder",REST[side].S)
			mat.set_shader_parameter("axis",axis);mat.set_shader_parameter("split",(REST[side].E-REST[side].S).dot(axis))
			mat.set_shader_parameter("part",part);poly.material=mat
			mat.set_shader_parameter("hand_texture",rig.layers["hand_"+side].texture)
			mat.set_shader_parameter("hand_origin",Vector2(1135,1238) if side=="L" else Vector2(231,1238))
			(upper if part==0 else fore).add_child(poly);poly.visible=false
			chains[side].polygons.append(poly);meshes.append(poly)
func projection(source: Vector2,target: Vector2,width: float,position: Vector2) -> Transform2D:
	var a: Vector2=source.normalized();var n:=Vector2(-a.y,a.x)
	var b: Vector2=target.normalized();var m:=Vector2(-b.y,b.x)
	var reach: float=target.length()/source.length()
	return Transform2D(b*a.x*reach+m*n.x*width,b*a.y*reach+m*n.y*width,position)
func target_point(p: Vector2) -> Vector2:
	return rig.to_local(rig.bones.chest.to_global(p-Vector2(768,965)))
func apply(amount: float,values: Dictionary,panel) -> void:
	global_transform=rig.global_transform
	controls.clear()
	for side in ["L","R"]:
		for poly in chains[side].polygons:
			poly.visible=amount>0.001
			poly.material.set_shader_parameter("overlap",amount*52.0)
		if amount<=0.001:continue
		var shoulder: Vector2=rig.to_local(rig.bones["shoulder_"+side].global_position)
		var elbow: Vector2=rig.to_local(rig.bones["forearm_"+side].global_position)
		var wrist: Vector2=rig.to_local(rig.bones["hand_"+side].global_position)
		elbow=elbow.lerp(target_point(TARGET[side].E),amount)
		var destination: Vector2=target_point(TARGET[side].W)
		var write_angle: float=deg_to_rad(float(hand_config.neutral_angle_degrees)+clampf(values.write_y/8.0,-1.0,1.0)*float(hand_config.maximum_wrist_adjustment_degrees))
		var writing_basis:=Transform2D(write_angle,Vector2.ZERO)
		if side=="R":
			var contact: Vector2=panel.surface_to_world(Asset.point(hand_config,"surface_anchor")+Vector2(values.write_x*1.5,values.write_y*0.75))
			destination=rig.to_local(contact)-writing_basis.basis_xform(Asset.local(hand_config,"tip_pixel"))
		else:
			destination=rig.to_local(panel.surface_to_world(Vector2(127,117)))
		wrist=wrist.lerp(destination,amount)
		var upper_matrix: Transform2D=projection(REST[side].E-REST[side].S,elbow-shoulder,1.0,shoulder)
		var width: float=0.90
		var fore_matrix: Transform2D=projection(REST[side].W-REST[side].E,wrist-elbow,lerpf(1.0,width,amount),elbow)
		chains[side].upper.transform=upper_matrix
		chains[side].fore.global_transform=rig.global_transform*fore_matrix
		var hand: Bone2D=rig.bones["hand_"+side]
		var old: Transform2D=rig.global_transform.affine_inverse()*hand.global_transform
		# Keep a consistent turn direction. A shortest-arc interpolation could
		# reverse abruptly when a feedback pose crosses the antipodal wrist angle.
		var target_angle: float=deg_to_rad(125.0) if side=="L" else write_angle
		var target_scale: float=0.88 if side=="L" else 1.0
		var hand_matrix:=Transform2D(lerpf(old.get_rotation(),target_angle,amount),old.get_scale().lerp(Vector2.ONE*target_scale,amount),old.get_skew()*(1.0-amount),wrist)
		chains[side].wrist.global_transform=rig.global_transform*hand_matrix
		hand.global_transform=chains[side].wrist.global_transform
		rig.layers["arm_"+side].visible=false;rig.layers["arm_"+side+"_deform"].visible=false
		controls[side]={"S":shoulder,"E":elbow,"W":wrist,"upper":upper_matrix,"fore":fore_matrix,"hand":hand_matrix}
