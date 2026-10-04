shader_type canvas_item;

// A smooth opacity falloff in the nose area, with the cheeks left at full strength.
uniform float nose_alpha : hint_range(0.0, 1.0) = 0.12;

void fragment() {
	float distance_px = abs(UV.x - 0.5) * 390.0;
	float outside_nose = smoothstep(30.0, 65.0, distance_px);
	COLOR.a *= mix(nose_alpha, 1.0, outside_nose);
}
