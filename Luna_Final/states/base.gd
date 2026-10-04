extends RefCounted
var pet: Node2D
var name: String
var elapsed: float=0.0
func setup(owner_pet: Node2D,state_name: String) -> void:pet=owner_pet;name=state_name
func enter(_payload: Dictionary) -> void:elapsed=0.0
func update(delta: float) -> void:elapsed+=delta
func exit() -> void:pass
