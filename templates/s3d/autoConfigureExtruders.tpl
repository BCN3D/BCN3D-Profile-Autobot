<autoConfigureExtruders name="{{name}}"  allowedToolheads="{{extruders|length()}}">
    <startingGcode>
M140 S[bed0_temperature]
{% if profile.left_extruder.is_active %}M104 S[extruder0_temperature] T0{% endif %}

{% if profile.right_extruder.is_active %}M104 S[extruder1_temperature] T1{% endif %}

M190 S[bed0_temperature]
{% if profile.left_extruder.is_active %}M109 S[extruder0_temperature] T0{% endif %}

{% if profile.right_extruder.is_active %}M109 S[extruder1_temperature] T1{% endif %}

G21         ;metric values
G90         ;absolute positioning
{% if extruders|length()==1%}M82         ;set extruder to absolute mode{% endif %}
M107        ;start with the fan off
G28 X0 Y0   ;move X/Y to min endstops
G28 Z0      ;move Z to min endstops

{% with draft_preset=profile.get_quality_preset(extruders, "Draft") %}
{% if extruders|length()==2 %}
T1          ;switch to the 2nd extruder
G92 E0      ;zero the extruded length
G1 F{{draft_preset.purge_speed(profile.right_extruder)|round(2) * 60}} E{{profile.right_extruder.start_purge_length}}   ;extrude {{profile.right_extruder.start_purge_length}}mm of feed stock
G92 E0      ;zero the extruded length again
G1 F200 E-9

T0          ;change to active toolhead
G92 E0      ;zero the extruded length
G1 F{{draft_preset.purge_speed(profile.left_extruder)|round(2) * 60}} E{{profile.left_extruder.start_purge_length}}   ;extrude {{profile.left_extruder.start_purge_length}}mm of feed stock
G92 E0      ;zero the extruded length again
{% else %}
T{{extruders[0].toolhead_number}}          ;change to active toolhead
G92 E0      ;zero the extruded length
G1 Z5 F200  ;Safety Z axis movement
G1 F{{draft_preset.purge_speed(extruders[0])|round(2) * 60}} E{{extruders[0].start_purge_length}}   ;extrude {{extruders[0].start_purge_length}}mm of feed stock
G92 E0      ;zero the extruded length again
{% endif %}
{% endwith %}
    </startingGcode>
    <layerChangeGcode>
        {% if extruders|length==1 %}M104 S0 T{% if extruders[0] == profile.left_extruder %}1{% else %}0{% endif %}{% endif %}
    </layerChangeGcode>
</autoConfigureExtruders>
