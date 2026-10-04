extends RefCounted
## Authored grip anchors are shared by the sprite, rig and contact tests.
static func read() -> Dictionary:
	return JSON.parse_string(FileAccess.get_file_as_string("res://data/working_hand_asset.json"))
static func point(config: Dictionary,key: String) -> Vector2:
	var xy: Array=config[key]
	return Vector2(float(xy[0]),float(xy[1]))
static func local(config: Dictionary,key: String) -> Vector2:
	return (point(config,key)-point(config,"wrist_pixel"))*float(config.pixel_scale)
