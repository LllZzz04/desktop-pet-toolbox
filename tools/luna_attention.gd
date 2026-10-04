extends "res://states/base.gd"
## Maid-style desktop greeting. Bone L is screen-right, R is screen-left.
## Copied into the isolated export project; Luna_Final remains the source rig.

var angle: float = 0.0

func enter(payload: Dictionary) -> void:
	super.enter(payload)
	pet.motion.play("", 0.2)

func update(delta: float) -> void:
	super.update(delta)
	var native: Vector2 = pet.to_local(pet.get_node("InteractionController").mouse_position)
	var target: float = clampf((native.x - 772.0) / 450.0, -1.0, 1.0) * 3.0
	angle = lerpf(angle, target, 1.0 - exp(-delta * 7.0))
	var greeting: float = smoothstep(0.0, 1.0, minf(elapsed / 0.7, 1.0))
	pet.motion.overrides = {
		"head_angle": angle,
		"chest_angle": angle / 6.0,
		"ahoge": angle * 0.16,
		"ahoge_tip": angle * 0.24,
		# Fold both forearms toward the lower abdomen; the authored layer
		# order lets the hands overlap naturally, with relaxed wrists.
		"shoulder_L": 27.0 * greeting,
		"forearm_L": 48.0 * greeting,
		"hand_L": -14.0 * greeting,
		"shoulder_R": -27.0 * greeting,
		"forearm_R": -48.0 * greeting,
		"hand_R": 14.0 * greeting,
		"breathing_strength": -0.15 * greeting,
	}
