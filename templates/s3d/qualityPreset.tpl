<autoConfigureQuality name="{{quality_preset.name}}">
    <globalExtrusionMultiplier>1</globalExtrusionMultiplier>
    <fanSpeed>
        <setpoint layer="1" speed="0" />
        <setpoint layer="2" speed="{{quality_preset.fan_speed_primary}}" />
    </fanSpeed>
    <filamentDiameter>{{quality_preset.primary_extruder.filament.diameter}}</filamentDiameter>
    <filamentPricePerKg>{{quality_preset.primary_extruder.filament.price_per_kg}}</filamentPricePerKg>
    <filamentDensity>{{quality_preset.primary_extruder.filament.density}}</filamentDensity>

    {% for extruder in profile.active_extruders %}
    {% with retraction_lift=(quality_preset.layer_height/2) %}
    {% include "s3d/extruder.xml" %}
    {% endwith %}

    {% endfor %}

    <primaryExtruder>{{quality_preset.primary_extruder.toolhead_number}}</primaryExtruder>
    <raftExtruder>{{quality_preset.raft_extruder.toolhead_number}}</raftExtruder>
    <skirtExtruder>{{quality_preset.skirt_extruder.toolhead_number}}</skirtExtruder>
    <infillExtruder>{{quality_preset.infill_extruder.toolhead_number}}</infillExtruder>
    <supportExtruder>{{quality_preset.support_extruder.toolhead_number}}</supportExtruder>
    <generateSupport>{{quality_preset.generate_support|int}}</generateSupport>
    <layerHeight>{{quality_preset.layer_height}}</layerHeight>
    <firstLayerHeightPercentage>{{quality_preset.first_layer_height_percentage}}</firstLayerHeightPercentage>
    <topSolidLayers>{{quality_preset.top_solid_layers}}</topSolidLayers>
    <bottomSolidLayers>{{quality_preset.bottom_solid_layers}}</bottomSolidLayers>
    <perimeterOutlines>{{quality_preset.perimeter_outlines}}</perimeterOutlines>
    <infillPercentage>{{quality_preset.infill_percentage}}</infillPercentage>
    <infillLayerInterval>1</infillLayerInterval>
    <defaultSpeed>{{quality_preset.default_speed * 60}}</defaultSpeed>
    <firstLayerUnderspeed>{{quality_preset.first_layer_underspeed|round(2)}}</firstLayerUnderspeed>
    <outlineUnderspeed>{{quality_preset.outline_underspeed|round(2)}}</outlineUnderspeed>
    <supportUnderspeed>{{quality_preset.support_underspeed|round(2)}}</supportUnderspeed>
    <supportInfillPercentage>25</supportInfillPercentage>
    <denseSupportInfillPercentage>75</denseSupportInfillPercentage>
    <avoidCrossingOutline>{{quality_preset.avoid_crossing_outline|int}}</avoidCrossingOutline>
    <overlapInfillAngles>1</overlapInfillAngles>
    <supportHorizontalPartOffset>{{quality_preset.support_horizontal_part_offset}}</supportHorizontalPartOffset>
    <supportUpperSeparationLayers>{{quality_preset.support_upper_separation_layers}}</supportUpperSeparationLayers>
    <supportLowerSeparationLayers>{{quality_preset.support_lower_separation_layers}}</supportLowerSeparationLayers>
    <supportAngles>90</supportAngles>
    <onlyRetractWhenCrossingOutline>{{quality_preset.only_retract_when_crossing_outline|int}}</onlyRetractWhenCrossingOutline>
    <retractBetweenLayers>0</retractBetweenLayers>
    <useRetractionMinTravel>1</useRetractionMinTravel>
    <retractWhileWiping>1</retractWhileWiping>
    <onlyWipeOutlines>1</onlyWipeOutlines>
    <minBridgingArea>10</minBridgingArea>
    <bridgingExtraInflation>0</bridgingExtraInflation>
    <bridgingExtrusionMultiplier>{{quality_preset.bridging_extrusion_multiplier}}</bridgingExtrusionMultiplier>
    <bridgingSpeedMultiplier>1.5</bridgingSpeedMultiplier>

    {% for extruder in profile.active_extruders %}
    {% with name=extruder.name, temperature=quality_preset.print_temperature(extruder), temperature_number=extruder.toolhead_number, is_heated_bed=False %}
    {% include "s3d/temperatureController.tpl" %}

    {% endwith %}
    {% endfor %}

    {% with name="Heated Bed", temperature=profile.bed_temperature, is_heated_bed=True %}
    {% include "s3d/temperatureController.tpl" %}

    {% endwith %}

    <toolChangeGcode>{% include "s3d/toolchange.gcode.tpl" %}</toolChangeGcode>
    <postProcessing>{% include "s3d/postprocessing.gcode.tpl" %}</postProcessing>
</autoConfigureQuality>
