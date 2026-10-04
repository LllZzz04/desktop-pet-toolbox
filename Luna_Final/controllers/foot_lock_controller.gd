extends Node
## Phase3.7's static foot branches do the actual lock. This records its lifecycle.
var locked: bool=true
var restore_pending: bool=false
var anchors: Array[Vector2]=[]
@onready var rig: Node2D=$"../Rig"
func _ready() -> void:restore()
func release() -> void:locked=false;restore_pending=false
func request_restore() -> void:restore_pending=true
func finish_frame() -> void:
	if restore_pending:restore_pending=false;restore()
func restore() -> void:
	locked=true;anchors=[rig.bones.foot_L.global_position,rig.bones.foot_R.global_position]
func maximum_drift() -> float:
	if not locked:return 0.0
	return maxf(rig.bones.foot_L.global_position.distance_to(anchors[0]),rig.bones.foot_R.global_position.distance_to(anchors[1]))
