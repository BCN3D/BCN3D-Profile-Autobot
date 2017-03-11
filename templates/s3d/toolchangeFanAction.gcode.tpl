{% if quality_preset.secondary_extruder_role == 'support' %}
{% if extruder == profile.primary_extruder %}
{IF NEWTOOL={{extruder.toolhead_number}} } M107\t\t;disable fan for support material
{% else %}
{IF NEWTOOL={{extruder.toolhead_number}} } M106 S{ {{quality_preset.fan_speed_primary}} }\t\t;enable fan for part material
{% endif %}
{% endif %}
