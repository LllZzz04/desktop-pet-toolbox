extends Node
## Interaction clips contain offsets, never a second complete rig pose.
const DEFAULTS := {
	"head_angle":0.0,"head_y":0.0,"chest_angle":0.0,"chest_y":0.0,
	"pelvis_x":0.0,"pelvis_y":0.0,"rig_angle":0.0,"root_y":0.0,
	"shoulder_L":0.0,"shoulder_R":0.0,"hand_L":0.0,"hand_R":0.0,
	"forearm_L":0.0,"forearm_R":0.0,"writing":0.0,"pen_contact":0.0,
	"working_fold":0.0,"write_x":0.0,"write_y":0.0,
	"hand_L_x":0.0,"hand_R_x":0.0,"hip_L":0.0,"hip_R":0.0,
	"knee_L":0.0,"knee_R":0.0,"foot_L":0.0,"foot_R":0.0,
	"hair_side_L":0.0,"hair_side_R":0.0,"hair_tip_L":0.0,"hair_tip_R":0.0,
	"ahoge":0.0,"ahoge_tip":0.0,"cape_upper_L":0.0,"cape_upper_R":0.0,
	"cape_tail_L":0.0,"cape_tail_R":0.0,"eye_closure":0.0,
	"yawn":0.0,"annoyed":0.0,"question":0.0,"anger":0.0,
	"sweat":0.0,"check":0.0,"exclamation":0.0,"glasses":0.0,"panel":0.0,
	"panel_y":0.0,"breathing_strength":1.0,
	"cover_head":0.0,"cover_chest":0.0,"cover_legs":0.0,"leg_crouch":0.0,"pout":0.0,"blush":0.0,
	"success_smile":0.0,"check_scale":1.0,"check_rotation":0.0,
	"success_star_1":0.0,"success_star_2":0.0,"success_star_3":0.0
}
@export var head_angle: float=0.0
@export var head_y: float=0.0
@export var chest_angle: float=0.0
@export var chest_y: float=0.0
@export var pelvis_x: float=0.0
@export var pelvis_y: float=0.0
@export var rig_angle: float=0.0
@export var root_y: float=0.0
@export var shoulder_L: float=0.0
@export var shoulder_R: float=0.0
@export var forearm_L: float=0.0
@export var forearm_R: float=0.0
@export var writing: float=0.0
@export var pen_contact: float=0.0
@export var working_fold: float=0.0
@export var write_x: float=0.0
@export var write_y: float=0.0
@export var hand_L: float=0.0
@export var hand_R: float=0.0
@export var hand_L_x: float=0.0
@export var hand_R_x: float=0.0
@export var hip_L: float=0.0
@export var hip_R: float=0.0
@export var knee_L: float=0.0
@export var knee_R: float=0.0
@export var foot_L: float=0.0
@export var foot_R: float=0.0
@export var hair_side_L: float=0.0
@export var hair_side_R: float=0.0
@export var hair_tip_L: float=0.0
@export var hair_tip_R: float=0.0
@export var ahoge: float=0.0
@export var ahoge_tip: float=0.0
@export var cape_upper_L: float=0.0
@export var cape_upper_R: float=0.0
@export var cape_tail_L: float=0.0
@export var cape_tail_R: float=0.0
@export var eye_closure: float=0.0
@export var yawn: float=0.0
@export var annoyed: float=0.0
@export var question: float=0.0
@export var anger: float=0.0
@export var sweat: float=0.0
@export var check: float=0.0
@export var exclamation: float=0.0
@export var glasses: float=0.0
@export var panel: float=0.0
@export var panel_y: float=0.0
@export var breathing_strength: float=1.0
func reset() -> void:
	for key in DEFAULTS:set(key,DEFAULTS[key])
func values() -> Dictionary:
	var result: Dictionary={}
	for key in DEFAULTS:result[key]=get(key)
	return result

@export var cover_head: float=0.0
@export var cover_chest: float=0.0
@export var cover_legs: float=0.0
@export var leg_crouch: float=0.0
@export var pout: float=0.0
@export var blush: float=0.0
@export var success_smile: float=0.0
@export var check_scale: float=1.0
@export var check_rotation: float=0.0
@export var success_star_1: float=0.0
@export var success_star_2: float=0.0
@export var success_star_3: float=0.0
