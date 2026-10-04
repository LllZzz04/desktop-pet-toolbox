extends "res://controllers/working_arm_pose.gd"
## Reuse only the sleeve splitter and positive affine projection helper.
## The Working pose/configuration/animation never calls this subclass.
var region: String="head"
var click_point: Vector2=Vector2(600,650)
var hands: Dictionary={}
var standing_hands: Dictionary={}
var pose_hands: Dictionary={}
var hand_assets: Dictionary={}
var hand_pose_weight: float=0.0
const POSES := {
	"head":{
		"R":{"E":Vector2(535,740),"W":Vector2(625,525),"angle":155.0},
		"L":{"E":Vector2(1005,750),"W":Vector2(925,515),"angle":-155.0}},
	"chest":{
		"R":{"E":Vector2(500,1110),"W":Vector2(670,1090),"angle":-70.0},
		"L":{"E":Vector2(1045,1140),"W":Vector2(880,1135),"angle":70.0}},
	"legs":{
		"R":{"E":Vector2(640,1210),"W":Vector2(645,1500),"angle":-15.0},
		"L":{"E":Vector2(905,1210),"W":Vector2(910,1500),"angle":15.0}}
}
const FRONT_POSE := {
	"R":{"E":Vector2(550,1060),"W":Vector2(665,985)},
	"L":{"E":Vector2(990,1060),"W":Vector2(875,985)}
}
func _ready() -> void:
	super._ready()
	hand_assets=JSON.parse_string(FileAccess.get_file_as_string("res://data/click_hand_assets.json")).families
	for side in ["L","R"]:
		for i in range(3):
			var poly: Polygon2D=chains[side].polygons[i]
			poly.z_index=(17 if side=="L" else 16) if i==0 else 36
		var holder:=Node2D.new();holder.name="CoverHand_"+side
		chains[side].wrist.add_child(holder);holder.visible=false;hands[side]=holder
		var hand:=Sprite2D.new();hand.name="StandingHandTransition_"+side
		hand.texture=rig.layers["hand_"+side].texture;hand.centered=false
		hand.position=-Vector2(47,38) if side=="L" else -Vector2(128,38)
		hand.z_as_relative=false;hand.z_index=38
		holder.add_child(hand);standing_hands[side]=hand
		pose_hands[side]={}
		for family in ["head","chest","legs"]:
			var data: Dictionary=hand_assets[family].sides[side]
			var sprite:=Sprite2D.new();sprite.name=family+"_hand_"+side
			sprite.texture=load(hand_assets[family].texture);sprite.centered=false
			sprite.region_enabled=true
			sprite.region_rect=Rect2(data.region[0],data.region[1],data.region[2],data.region[3])
			sprite.region_filter_clip_enabled=true
			sprite.scale=Vector2.ONE*float(data.pixel_scale)
			sprite.position=-Vector2(data.wrist_pixel[0],data.wrist_pixel[1])*float(data.pixel_scale)
			sprite.z_as_relative=false;sprite.z_index=39 if side=="R" else 38
			sprite.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
			# The rotation happens around the authored wrist, not the atlas corner.
			var pivot:=Node2D.new();pivot.name=family+"_wrist_"+side
			holder.add_child(pivot);pivot.add_child(sprite);pivot.visible=false
			pose_hands[side][family]={"pivot":pivot,"sprite":sprite}
func hide_pose() -> void:
	controls.clear()
	for poly in meshes:poly.visible=false
	for hand in hands.values():hand.visible=false
	hand_pose_weight=0.0
func interpolate_vector(from: Vector2,to: Vector2,t: float,turn: int=0) -> Vector2:
	# Cartesian interpolation through a 180-degree fold collapses a sleeve.
	# Interpolate direction and length separately, keeping every triangle positive.
	var change: float=wrapf(to.angle()-from.angle(),-PI,PI)
	# Head guards pass close to an antipodal elbow angle. Pick a consistent
	# side of the arc so head shaking cannot reverse the interpolation path.
	if turn>0 and change<0.0:change+=TAU
	if turn<0 and change>0.0:change-=TAU
	var angle: float=from.angle()+change*t
	return Vector2.from_angle(angle)*lerpf(from.length(),to.length(),t)
func destination(side: String) -> Dictionary:
	var pose: Dictionary=POSES[region][side].duplicate()
	var offset: float=clampf((click_point.x-772.0)*0.20,-35.0,35.0)
	if region=="head":
		# Palms guard the upper hair/crown. The eyes and cheeks remain uncovered.
		var chosen: bool=(side=="R" and click_point.x<772.0) or (side=="L" and click_point.x>=772.0)
		if chosen:
			pose.W.y=clampf(500.0+(click_point.y-520.0)*0.06,490.0,550.0)
			pose.E.y=740.0+(pose.W.y-510.0)*0.12
		pose.W.x+=offset
	elif region=="chest":
		pose.W.x+=offset;pose.W.y+=clampf((click_point.y-1080.0)*0.12,-16.0,22.0)
	else:
		# Protective hands at the upper legs; never stretch the arms to the ankles.
		pose.W.x+=offset
	return pose
func apply(strength: float,_values: Dictionary,_panel) -> void:
	global_transform=rig.global_transform;controls.clear()
	if strength<=0.000001:hide_pose();return
	hand_pose_weight=smoothstep(0.08,0.32,strength)
	for side in ["L","R"]:
		for poly in chains[side].polygons:
			poly.visible=true;poly.material.set_shader_parameter("overlap",52.0*strength)
		var hand: Bone2D=rig.bones["hand_"+side]
		var old: Transform2D=rig.global_transform.affine_inverse()*hand.global_transform
		var shoulder: Vector2=rig.to_local(rig.bones["shoulder_"+side].global_position)
		var elbow: Vector2=rig.to_local(rig.bones["forearm_"+side].global_position)
		var wrist: Vector2=rig.to_local(hand.global_position)
		var pose: Dictionary=destination(side)
		var goal_e: Vector2=target_point(pose.E)
		var goal_w: Vector2=target_point(pose.W)
		if region=="legs":
			# Follow the upper legs rather than the chest while the torso crouches.
			var hip: Bone2D=rig.bones["hip_"+side]
			var hip_anchor:=Vector2(920,1465) if side=="L" else Vector2(640,1465)
			goal_w=rig.to_local(hip.to_global(pose.W-hip_anchor))
			goal_w.y-=90.0*clampf(_values.get("leg_crouch",0.0),0.0,1.0)
			var a: float=(REST[side].E-REST[side].S).length()
			var b: float=(REST[side].W-REST[side].E).length()
			var reach: Vector2=goal_w-shoulder
			# Keep both sleeve segments close to their original lengths.
			reach=reach.limit_length((a+b)*1.09)
			goal_w=shoulder+reach
			var normal:=Vector2(-reach.y,reach.x).normalized()
			goal_e=shoulder+reach*(a/(a+b))+normal*(18.0 if side=="R" else -18.0)
		if region=="head":goal_w=rig.to_local(rig.bones.head.to_global(pose.W-Vector2(772,842)))
		var upper_vector: Vector2
		var fore_vector: Vector2
		if region=="head":
			var front_e: Vector2=target_point(FRONT_POSE[side].E)
			var front_w: Vector2=target_point(FRONT_POSE[side].W)
			if strength<=0.40:
				var gather: float=smoothstep(0.0,0.40,strength)
				upper_vector=interpolate_vector(elbow-shoulder,front_e-shoulder,gather)
				# Turn toward the body front, rather than sweeping outside the head.
				fore_vector=interpolate_vector(wrist-elbow,front_w-front_e,gather,-1 if side=="R" else 1)
				elbow=shoulder+upper_vector;wrist=elbow+fore_vector
			else:
				var raise: float=smoothstep(0.40,1.0,strength)
				# Projected upper arms shorten while lifting forward, toward camera.
				elbow=front_e.lerp(goal_e,raise);wrist=front_w.lerp(goal_w,raise)
				upper_vector=elbow-shoulder;fore_vector=wrist-elbow
		else:
			upper_vector=interpolate_vector(elbow-shoulder,goal_e-shoulder,strength)
			fore_vector=interpolate_vector(wrist-elbow,goal_w-goal_e,strength)
			elbow=shoulder+upper_vector;wrist=elbow+fore_vector
		var upper_width: float=lerpf(1.0,0.88,strength) if region=="head" else 1.0
		var fore_width: float=lerpf(1.0,0.84,strength) if region=="head" else 1.0
		var upper_matrix: Transform2D=projection(REST[side].E-REST[side].S,upper_vector,upper_width,shoulder)
		var fore_matrix: Transform2D=projection(REST[side].W-REST[side].E,fore_vector,fore_width,elbow)
		chains[side].upper.transform=upper_matrix
		chains[side].fore.global_transform=rig.global_transform*fore_matrix
		var hand_angle: float=lerpf(old.get_rotation(),deg_to_rad(pose.angle),strength)
		var hand_matrix:=Transform2D(hand_angle,old.get_scale(),old.get_skew(),wrist)
		chains[side].wrist.global_transform=rig.global_transform*hand_matrix
		hand.global_transform=chains[side].wrist.global_transform
		hands[side].visible=true
		standing_hands[side].visible=hand_pose_weight<0.999999
		standing_hands[side].modulate.a=1.0-hand_pose_weight
		for family in pose_hands[side]:
			var asset: Dictionary=pose_hands[side][family]
			asset.pivot.visible=family==region and hand_pose_weight>0.000001
			asset.pivot.modulate.a=hand_pose_weight
			if family==region:
				var data: Dictionary=hand_assets[region].sides[side]
				var forward: float=deg_to_rad(float(data.forward_degrees))
				var aligned_goal: float=(goal_w-goal_e).angle()-forward
				var bend: float=wrapf(deg_to_rad(float(data.neutral_world_degrees))-aligned_goal,-PI,PI)
				# Follow the visible forearm while raising/lowering. The final bend
				# cups a crown from above or lays a chest hand across clothes.
				var art_angle: float=fore_vector.angle()-forward+bend*strength
				asset.pivot.rotation=art_angle-hand_matrix.get_rotation()
		# New curled hands replace the standing fan-shaped hand only in this state.
		rig.layers["hand_"+side].visible=false
		rig.layers["arm_"+side].visible=false;rig.layers["arm_"+side+"_deform"].visible=false
		controls[side]={"S":shoulder,"E":elbow,"W":wrist,"upper":upper_matrix,"fore":fore_matrix,"hand":hand_matrix}
