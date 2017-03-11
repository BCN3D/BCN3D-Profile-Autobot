{IF NEWTOOL=0} T0			;Start tool switch 0
{IF NEWTOOL=0} G1 F2400 E0
{% with extruder=profile.left_extruder, purge_speed=quality_preset.purge_speed(profile.left_extruder) * 60 %}
;{IF NEWTOOL=0} M800 F{{purge_speed|round(2)}} E{{extruder.purge_parameters['E']|round(2)}} S{{extruder.purge_parameters['S']|round(2)}} P{{extruder.purge_parameters['P']|round(4)}} 	;SmartPurge
{IF NEWTOOL=0} G1 F{{purge_speed|round(2)}} E{{extruder.toolchange_purge_length|round(2)}}		;Default purge value
{% endwith %}

{IF NEWTOOL=1} T1			;Start tool switch 1
{IF NEWTOOL=1} G1 F2400 E0
{% with extruder=profile.right_extruder, purge_speed=quality_preset.purge_speed(profile.right_extruder) * 60 %}
;{IF NEWTOOL=1} M800 F{{purge_speed|round(2)}} E{{extruder.purge_parameters['E']|round(2)}} S{{extruder.purge_parameters['S']|round(2)}} P{{extruder.purge_parameters['P']|round(4)}} 	;SmartPurge
{IF NEWTOOL=1} G1 F{{purge_speed|round(2)}} E{{extruder.toolchange_purge_length|round(2)}}		;Default purge
{% endwith %}

G4 P2000					;Stabilize Hotend's pressure
G92 E0						;Zero extruder
G1 F3000 E-4.5				;Retract
G1 F[travel_speed]			;End tool switch
G91
G1 F[travel_speed] Z2
G90
