extends SceneTree
func _initialize() -> void:call_deferred("run")
func run() -> void:
	var results: Dictionary={}
	var success: bool=true
	for name in ["idle","look","attention","single","annoyed","angry","drag","working","success","error","yawn"]:
		var pet: Node2D=load("res://LunaPet.tscn").instantiate()
		pet.automatic_processing=false;pet.random_events_enabled=false;root.add_child(pet)
		match name:
			"look":pet.play_idle_variant("idle_look_around")
			"attention":pet.set_attention(true,Vector2(1200,650))
			"single":pet.notify_click(Vector2(1200,650))
			"annoyed":
				for i in range(3):pet.notify_click(Vector2(1200,650))
			"angry":
				for i in range(6):pet.notify_click(Vector2(1200,650))
			"drag":pet.start_drag(Vector2(768,1000))
			"working":pet.set_working(true)
			"success":pet.notify_success()
			"error":pet.notify_error()
			"yawn":pet.play_idle_variant("idle_yawn")
		for i in range(72 if name=="yawn" else 18):pet.step(1.0/60.0)
		pet.rig.blink_once();pet.step(.05)
		var closed: bool=pet.rig.eyes_closed and pet.rig.layers.eye_L_closed.visible and pet.rig.layers.eye_R_closed.visible and pet.rig.eye_states_valid()
		pet.step(.14)
		var reopened: bool=not pet.rig.eyes_closed and pet.rig.eye_states_valid()
		if name=="yawn":reopened=reopened and pet.rig.layers.eye_L_closed.visible and pet.rig.layers.eye_R_closed.visible
		else:reopened=reopened and pet.rig.layers.eye_L_open.visible and pet.rig.layers.eye_R_open.visible
		results[name]={"closed_exclusively":closed,"reopened_or_forced_closed_correctly":reopened,"pass":closed and reopened}
		success=success and closed and reopened
		pet.queue_free();await process_frame
	var report: Dictionary={"pass":success,"cases":results}
	FileAccess.open("res://data/blink_compatibility_results.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("BLINK_COMPATIBILITY ",JSON.stringify(report));quit(0 if success else 1)
