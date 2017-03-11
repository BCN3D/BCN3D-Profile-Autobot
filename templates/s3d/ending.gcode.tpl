M104 S0 T0
M104 S0 T1
M140 S0		;heated bed heater off
G91		;relative positioning
G1 Z+0.5 E-5 Y+10 F[travel_speed]	;move Z up a bit and retract filament even more
G28 X0 Y0		;move X/Y to min endstops so the head is out of the way
M84		;steppers off
G90		;absolute positioning,
