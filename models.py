from __future__ import division
import math
import time

from utils import (
    round_to_base,
    parse_none,
)

from data import (
    qualities
)


SIDE_NAMES = {
    0: 'left',
    1: 'right',
}

# Extruder roles
PRIMARY = 'primary'
INFILL = 'infill'
SUPPORT = 'support'

# Heating parameters
HEATING_PARAMS = {
    'hotend': [80, 310, 25],
    'bed': {
        'low_temperature': [51, 61, 19, 0],
        'high_temperature': [1000, 90, 47, 10],
    }
}


class Filament(object):
    def __init__(self, data):
        # Clean any 'None' values in the raw dat
        data = {key: parse_none(value) for key, value in data.items()}

        self.id = data['id']
        self.diameter = data['filamentDiameter']
        self.price_per_kg = data['filamentPricePerKg']
        self.density = data['filamentDensity']
        self.is_support_material = data['isSupportMaterial']
        self.is_flexible_material = data['isFlexibleMaterial']
        self.bed_temperature = data['bedTemperature']
        self.print_temperature_range = data['printTemperature']
        self.default_print_speed = data['defaultPrintSpeed']
        self.advised_max_print_speed = data['advisedMaxPrintSpeed']
        self.max_flow = data['maxFlow']
        self.max_flow_for_high_flow_hotend = data['maxFlowForHighFlowHotend']
        self.retraction_distance = data['retractionDistance']
        self.retraction_speed = data['retractionSpeed']
        self.fan_percentage_range = data['fanPercentage']
        self.extrusion_multiplier = data['extrusionMultiplier']
        self.purge_length = data['purgeLength']


class Extruder(object):
    min_purge_length = 20
    base_start_purge_length = 7
    base_toolchange_purge_length = 1.5
    yeld_curve = 1000

    def __init__(self, toolhead_number, filament_data, hotend_data):
        self.toolhead_number = toolhead_number
        self.filament = Filament(filament_data)

        self.hotend_id = hotend_data['id']
        self.nozzle_size = hotend_data['nozzleSize']
        self.material = hotend_data['material']
        self.hot_block = hotend_data['hotBlock']

        self.side_name = SIDE_NAMES[self.toolhead_number].capitalize()
        self.is_active = self.filament.id and self.hotend_id

        self.coasting_distance = (self.nozzle_size / 0.4)**2 * self.filament.purge_length

        self.purge_parameters = {
            'S': math.pi * ((self.filament.diameter / 2)**2 - (self.nozzle_size / 2)**2) * self.yeld_curve / self.nozzle_size,
            'E': self.max_purge_length * self.filament.purge_length,
            'P': (self.min_purge_length * self.filament.purge_length * (self.nozzle_size / 2)**2) / (self.filament.diameter / 2)**2
        }
        self.start_purge_length = max(
            10,
            (self.nozzle_size / 0.4)**2 * self.base_start_purge_length * self.filament.purge_length / self.base_toolchange_purge_length
        )
        self.toolchange_purge_length = (self.nozzle_size / 0.4)**2 * self.filament.purge_length

    @property
    def name(self):
        if not self.nozzle_size:
            return ''
        return '{} Extruder {}'.format(
            self.side_name,
            self.nozzle_size
        )

    @property
    def speed_multiplier(self):
        if self.filament.is_flexible_material:
            return self.filament.default_print_speed / 24 * self.nozzle_size
        else:
            return self.filament.default_print_speed / 60

    @property
    def max_purge_length(self):
        """Maximum purge length for different nozzle sizes."""
        if self.nozzle_size >= 0.8:
            return 8 + 18  # llargada max highFlow
        return 8 + 14  # llargada max standard


class Profile(object):
    def __init__(self, hotend_left_data=None, hotend_right_data=None, filament_left_data=None, filament_right_data=None):
        self.left_extruder = Extruder(
            toolhead_number=0,
            filament_data=filament_left_data,
            hotend_data=hotend_left_data,
        )
        self.right_extruder = Extruder(
            toolhead_number=1,
            filament_data=filament_right_data,
            hotend_data=hotend_right_data,
        )

        self.version = time.strftime("%Y-%m-%d %H:%M:%S")

        self.active_extruders = [e for e in [self.left_extruder, self.right_extruder] if e.is_active]
        self.primary_extruder = self.get_primary_extruder()
        self.bed_temperature = max([e.filament.bed_temperature for e in self.active_extruders])

        self.quality_presets = self.get_quality_presets()

    @property
    def name(self):
        if len(self.active_extruders) == 1:
            extruder_label = '{side} Extruder {size} Only ({filament})'.format(
                self.primary_extruder.side_name,
                self.primary_extruder.nozzle_size,
                self.primary_extruder.filament.id
            )
        else:
            extruder_label = ', '.join([
                '{} {} ({})'.format(e.nozzle_size, e.side_name, e.filament.id)
                for e in self.active_extruders
            ])

        return "BCN3D Sigma - {}".format(
            extruder_label
        )

    def get_quality_preset(self, extruders, quality_id):
        for preset in self.quality_presets:
            if preset.extruders == extruders and preset.quality_id == quality_id:
                return preset

    @property
    def extruder_combinations(self):
        """Return combinations of extruders used for quality presets."""
        extruder_combinations = [[e] for e in self.active_extruders]
        if len(extruder_combinations) == 2:
            extruder_combinations.append([self.left_extruder, self.right_extruder])
        return extruder_combinations

    def get_quality_presets(self):
        presets = []
        for extruder_combination in self.extruder_combinations:
            for quality_data in sorted(qualities.values(), key=lambda x: x['index']):
                presets.append(QualityPreset(extruders=extruder_combination, quality_data=quality_data))
        return presets

    def get_primary_extruder(self):
        """Default primary extruder."""
        if len(self.active_extruders) == 1:
            return self.active_extruders[0]
        if self.active_extruders[0].filament.is_support_material != self.active_extruders[1].filament.is_support_material:
            return self.active_extruders[0] if self.active_extruders[1].filament.is_support_material else self.active_extruders[1]
        if self.active_extruders[0].nozzle_size > self.active_extruders[1].nozzle_size:
            return self.active_extruders[1]
        return self.active_extruders[0]

    def hotend_heating_time(temperature):
        """Return needed time (sec) to reach Temperature (C) for a hotend."""
        param1, param2, param3 = HEATING_PARAMS['hotend']
        return param1 * math.log(-(param2 - param3) / (temperature - param2))

    def bed_heating_time(temperature):
        """Return needed time (sec) to reach Temperature (C) for a heated bed."""
        if temperature <= 60:
            param1, param2, param3 = HEATING_PARAMS['bed']['low_temperature']
            time = param1 * math.log(-(param2 - param3) / (temperature - param2))
        else:
            param1, param2, param3, param4 = HEATING_PARAMS['bed']['high_temperature']
            time = param1 * math.log(-param2 / (temperature - param2 - param3)) + param4

        return max(0, time)


class QualityPreset(object):
    bridging_speed_multiplier = 1.5

    def __init__(self, extruders, quality_data):
        self.quality_id = quality_data['id']
        self.layer_height_multiplier = quality_data['layerHeightMultiplier']
        self.base_default_speed = quality_data['defaultSpeed']
        self.base_first_layer_underspeed = quality_data['firstLayerUnderspeed']
        self.base_outline_underspeed = quality_data['outlineUnderspeed']
        self.top_bottom_width = quality_data['topBottomWidth']
        self.wall_width = quality_data['wallWidth']
        self.infill_percentage = quality_data['infillPercentage']

        self.extruders = extruders
        self.quality_data = quality_data
        self.primary_extruder = self.get_primary_extruder()
        self.raft_extruder = self.primary_extruder
        self.skirt_extruder = self.primary_extruder
        self.infill_extruder = self.secondary_extruder if self.secondary_extruder_role() == INFILL else self.primary_extruder
        self.support_extruder = self.secondary_extruder if self.secondary_extruder_role() == SUPPORT else self.primary_extruder

        self.only_retract_when_crossing_outline = self.primary_extruder.filament.is_flexible_material
        # Always avoid crossing outlines, except for combined infill
        self.avoid_crossing_outline = self.secondary_extruder_role != INFILL

        self.bridging_extrusion_multiplier = self.primary_extruder.filament.extrusion_multiplier / self.bridging_speed_multiplier
        self.max_allowed_underspeed = self.max_flow_value() / (self.layer_height * self.primary_extruder.nozzle_size * self.base_default_speed)
        self.first_layer_height = self.layer_height * self.first_layer_height_percentage / 100

        self.top_solid_layers = max(4, int(round(self.top_bottom_width / self.layer_height)))
        self.bottom_solid_layers = max(4, int(round(self.top_bottom_width / self.layer_height)))
        self.perimeter_outlines = max(2, int(round(self.wall_width / self.primary_extruder.nozzle_size)))

        self.support_horizontal_part_offset = 0.1 if self.secondary_extruder_role == SUPPORT else 0.7
        self.support_upper_separation_layers = 0 if self.secondary_extruder_role == SUPPORT else 1
        self.support_lower_separation_layers = 0 if self.secondary_extruder_role == SUPPORT else 1

    @property
    def name(self):
        combination_name = self.extruder_combination_name
        quality_name = self.quality_id
        if combination_name == 'Both Extruders':
            secondary_extruder = self.secondary_extruder
            secondary_role = self.secondary_extruder_role()
            return '{} ({} Ext. for {}) - {}'.format(
                combination_name,
                secondary_extruder.side_name,
                secondary_role,
                quality_name
            )
        else:
            return '{} - {}'.format(combination_name, quality_name)

    @property
    def extruder_combination_name(self):
        if len(self.extruders) == 2:
            return "Both Extruders"
        return "{} Extruder".format(self.extruders[0].side_name)

    def get_primary_extruder(self):
        if len(self.extruders) == 1:
            return self.extruders[0]
        if self.extruders[0].filament.is_support_material != self.extruders[1].filament.is_support_material:
            return self.extruders[0] if self.extruders[1].filament.is_support_material else self.extruders[1]
        if self.extruders[0].nozzle_size > self.extruders[1].nozzle_size:
            return self.extruders[1]
        return self.extruders[0]

    @property
    def primary_speed(self):
        return min(
            *filter(lambda x: x, [
                self.base_default_speed * self.primary_extruder.speed_multiplier,
                self.max_flow_value() / (self.primary_extruder.nozzle_size * self.layer_height),
                self.primary_extruder.filament.advised_max_print_speed
            ])
        )

    @property
    def secondary_speed(self):
        if not self.secondary_extruder:
            raise Exception("No secondary extruder selected!")

        return min(
            *filter(lambda x: x, [
                self.base_default_speed * self.secondary_extruder.speed_multiplier,
                self.max_flow_value() / (self.secondary_extruder.nozzle_size * self.layer_height),
                self.secondary_extruder.filament.advised_max_print_speed
            ])
        )

    @property
    def default_speed(self):
        """Find the default speed for this quality preset.

        The default speed is the minimum of the default speed of the active extruders.
        """
        quality_default_speed = self.primary_speed
        if self.secondary_extruder:
            quality_default_speed = min(quality_default_speed, self.secondary_speed)

        return int(round(quality_default_speed))

    def extruder_speed(self, extruder):
        if extruder != self.primary_extruder and extruder == self.support_extruder:
            return self.default_speed * self.support_underspeed
        return self.default_speed

    @property
    def secondary_extruder(self):
        if len(self.extruders) < 2:
            return

        primary_index = self.extruders.index(self.primary_extruder)
        return self.extruders[primary_index - 1]

    def secondary_extruder_role(self):
        """ Find the role for the secondary extruder (infill or support)

        If one extruder uses support material and the other doesn't, the secondary's job is always support.
        If none of both of the extruders use support material, the secondary will be used for infill.
        """
        secondary = self.secondary_extruder
        if not secondary:
            return

        primary = self.primary_extruder

        if primary.filament.is_support_material != secondary.filament.is_support_material:
            return SUPPORT
        return INFILL

    def generate_support(self):
        return self.secondary_extruder_role() == SUPPORT

    @property
    def layer_height(self):
        """Generate quality's Layer height setting.

        Generally, a quality's layer height the primary extruder's layer height.
        However, if two extruders are used the layer height can't be more than 0.5 * secondary nozzle size.
        """
        layer_height = self.primary_extruder.nozzle_size * self.layer_height_multiplier

        if self.secondary_extruder:
            layer_height = min(layer_height, self.secondary_extruder.nozzle_size * 0.5)

        return layer_height

    def max_flow_value(self, extruder=None):
        """Return the extruder's maximum allowed flow in mm/s."""
        extruder = extruder or self.primary_extruder
        filament = extruder.filament

        if extruder.nozzle_size > 0.6 and filament.max_flow_for_high_flow_hotend:
            return filament.max_flow_for_high_flow_hotend
        if filament.max_flow:
            return filament.max_flow

        return extruder.nozzle_size * self.layer_height * filament.advised_max_print_speed

    @property
    def first_layer_underspeed(self):
        if self.primary_extruder.filament.is_flexible_material:
            return 1.0

        base_speed = self.base_default_speed * self.primary_extruder.speed_multiplier
        return min(
            self.max_allowed_underspeed,
            base_speed * self.base_first_layer_underspeed / self.default_speed
        )

    @property
    def outline_underspeed(self):
        if self.primary_extruder.filament.is_flexible_material:
            return 1.0

        base_speed = self.base_default_speed * self.primary_extruder.speed_multiplier
        return min(
            self.max_allowed_underspeed,
            base_speed * self.base_outline_underspeed / self.default_speed
        )

    @property
    def support_underspeed(self):
        support_extruder = self.support_extruder

        if support_extruder == self.primary_extruder:
            underspeed = self.default_speed * 0.9 / self.primary_speed
        else:
            underspeed = (
                self.max_flow_value() /
                self.primary_extruder.nozzle_size *
                self.layer_height_multiplier *
                self.secondary_extruder.nozzle_size *
                self.default_speed
            )

        return min(
            self.max_allowed_underspeed,
            underspeed
        )

    @property
    def first_layer_height_percentage(self):
        extruder = self.primary_extruder

        return int(min(
            125,
            (extruder.nozzle_size / 2) / self.layer_height * 100,
            self.max_flow_value() * 100 / (
                extruder.nozzle_size * self.layer_height * (self.base_default_speed) * float(self.first_layer_underspeed)
            )
        ))

    def print_temperature(self, extruder, base=5):
        # adaptative temperature according to flow values. Rounded to base
        speed = self.extruder_speed(extruder)

        # This is taken from the original script, it calculates a temporary layer height for the chosen extruder.
        # This layer height doesn't always get used though, as only the minimum layer height of all extruders gets used.
        # So, this seems like it might return some wrong results and should just be self.layer_height instead.
        temp_layer_height = extruder.nozzle_size * self.layer_height_multiplier
        flow = extruder.nozzle_size * temp_layer_height * speed

        # Warning if something is not working properly
        if flow > self.max_flow_value(extruder):
            print("Warning! You're trying to print at higher flow than allowed: {}: {} > {}".format(
                extruder.filament.id,
                flow,
                self.max_flow_value(extruder))
            )

        min_temperature = extruder.filament.print_temperature_range[0]
        max_temperature = extruder.filament.print_temperature_range[1]
        temperature = min_temperature + flow / self.max_flow_value(
            extruder
        ) * (max_temperature - min_temperature)
        return round_to_base(temperature, base=base)

    def max_print_speed(self, extruder):
        return (
            max(
                1,
                self.print_temperature(
                    extruder,
                ) - extruder.filament.print_temperature_range[0]
            ) / max(
                1,
                extruder.filament.print_temperature_range[1] - extruder.filament.print_temperature_range[0]
            )
        ) * self.max_flow_value(extruder) / (
            extruder.nozzle_size * self.layer_height
        )

    def purge_speed(self, extruder):
        # speed adapted to improve surplus material storage (maximum purge speed for the hotend's temperature)
        return self.max_print_speed(extruder) * extruder.nozzle_size * self.layer_height / (math.pi * (extruder.filament.diameter / 2)**2)

    def fan_speed(self, extruder, base=5):
        """Adaptative fan speed according to temperature values. Rounded to base."""
        min_percentage = extruder.filament.fan_percentage_range[0]
        temperature = self.print_temperature(extruder)
        temperature_range = extruder.filament.print_temperature_range[1] - extruder.filament.print_temperature_range[0]

        if not temperature_range or extruder.filament.fan_percentage_range[1] == 0:
            return extruder.filament.fan_percentage_range[0]

        degrees_above_min = temperature - extruder.filament.print_temperature_range[0]

        fan_percentage_range = extruder.filament.fan_percentage_range[1] - extruder.filament.fan_percentage_range[0]
        fan_speed_for_temperature = min_percentage + (degrees_above_min / temperature_range) * fan_percentage_range

        layer_height_at_max_fan_speed = 0.025
        layer_height_at_min_fan_speed = 0.2
        layer_height_range = layer_height_at_min_fan_speed - layer_height_at_max_fan_speed

        layer_height_above_min = self.layer_height - layer_height_at_max_fan_speed

        fan_speed_for_layer_height = min_percentage + (layer_height_above_min / layer_height_range) * fan_percentage_range
        result = max(fan_speed_for_temperature, fan_speed_for_layer_height)
        return round_to_base(min(result, 100), base=base)

    @property
    def fan_speed_primary(self):
        return self.fan_speed(self.primary_extruder)

    def perimeter_acceleration(self, base=5, multiplier=30000, default_acceleration=2000):
        outline_speed = self.extruder_speed(self.primary_extruder) * self.outline_underspeed
        acceleration = min(
            default_acceleration,
            self.primary_extruder.nozzle_size * self.layer_height * multiplier * 1 / (outline_speed**(0.5))
        )
        return round_to_base(acceleration, base=base)
