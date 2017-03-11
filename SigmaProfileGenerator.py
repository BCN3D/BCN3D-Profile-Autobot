#!/usr/bin/python -tt
# coding: utf-8

# Guillem Àvila Padró - October 2016
# Released under GNU LICENSE
# https://opensource.org/licenses/GPL-3.0
# version 1.1.1

# Version Changelog:
# - Start gcodes adjusted for cleaner skirts
# - Improved Layer Fan speeds according to layer height and temperature
# - Code cleaned up
# - S3D: Fixed bug in starting gcode for Dual prints
# - Support material speeds bugfixes

import copy, time, math, os, platform, sys, json, string, shutil, zipfile

from models import Profile
from rendering import render


def createSimplify3DProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, dataLog, createFile):
    profile = Profile(
        filament_left_data=filamentLeft,
        filament_right_data=filamentRight,
        hotend_left_data=hotendLeft,
        hotend_right_data=hotendRight
    )

    template_data = {
        'profile': profile,
    }

    rendered_profile = render('s3d/profile.fff', template_data)

    filename = "{}.test.fff".format(profile.name)
    if createFile == 'createFile':
        with open(filename, "w") as f:
            f.write(rendered_profile)
    if createFile == '--no-file':
        print(rendered_profile)
    if createFile == '--only-filename':
        print(filename)
    return filename


def createCuraProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, dataLog, createFile):

    #  Attention: hotendLeft and hotendRight must be the same, or "None".

    makeSupports = 'None'
    supportType = 'Lines'
    supportDualExtrusion = 'First extruder'
    supportXYDistance = 1

    if hotendLeft['id'] != 'None' and hotendRight['id'] != 'None' and hotendLeft['id'] != hotendRight['id']:
        return
    if hotendLeft['id'] == 'None':
        if hotendRight['id'] == 'None':
            return
        else:
            # MEX Right
            hotend, extruder, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder = hotendRight, "Right Extruder", 1, 1, 1,
            currentLayerHeight = hotend['nozzleSize'] * quality['layerHeightMultiplier']
            supportZdistance = currentLayerHeight
            fileName = "BCN3D Sigma - Right Extruder "+str(hotendRight['nozzleSize'])+" Only ("+filamentRight['id']+") - "+quality['id']
            extruderPrintOptions = ["Right Extruder"]
            filamentLeft = dict([('id', '')])
            currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, currentLayerHeight, 1, quality, 'MEX Right')
            printTemperature1 = 0
            printTemperature2 = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
            bedTemperature = filamentRight['bedTemperature']
            filamentDiameter1 = filamentRight['filamentDiameter']
            filamentDiameter2 = 0
            filamentFlow = filamentRight['extrusionMultiplier']*100
            retractionSpeed = filamentRight['retractionSpeed']
            retractionAmount = filamentRight['retractionDistance']
            currentFirstLayerHeightPercentage = int(min(125, (hotend['nozzleSize']/2)/currentLayerHeight*100, maxFlowValue(hotendRight, filamentRight, currentLayerHeight)*100/(hotend['nozzleSize']*currentLayerHeight*(currentDefaultSpeed/60.)*float(currentFirstLayerUnderspeed))))
            firstLayerHeight = "%.2f" % (currentLayerHeight * currentFirstLayerHeightPercentage/100.)
            if filamentRight['fanPercentage'][1] > 0:
                fanEnabled = 'True'
            else:
                fanEnabled = 'False'
            fanPercentage = fanSpeed(filamentRight, printTemperature2, currentLayerHeight)            
            hotendLeftTemperature, hotendRightTemperature = 0, printTemperature2
            purgeValuesGeneral = purgeValues(hotendRight, filamentRight, currentDefaultSpeed, currentLayerHeight)       
            purgeValuesT0 = purgeValuesGeneral
            purgeValuesT1 = purgeValuesGeneral
    elif hotendRight['id'] == 'None':
        # MEX Left
        hotend, extruder, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder = hotendLeft, "Left Extruder", 0, 0, 0
        currentLayerHeight = hotend['nozzleSize'] * quality['layerHeightMultiplier']
        supportZdistance = currentLayerHeight
        fileName = "BCN3D Sigma - Left Extruder "+str(hotendLeft['nozzleSize'])+" Only ("+filamentLeft['id']+") - "+quality['id']
        extruderPrintOptions = ["Left Extruder"]
        filamentRight = dict([('id', '')])
        currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, currentLayerHeight, 1, quality, 'MEX Left')
        printTemperature1 = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
        printTemperature2 = 0
        bedTemperature = filamentLeft['bedTemperature']
        filamentDiameter1 = filamentLeft['filamentDiameter']
        filamentDiameter2 = 0
        filamentFlow = filamentLeft['extrusionMultiplier']*100
        retractionSpeed = filamentLeft['retractionSpeed']
        retractionAmount = filamentLeft['retractionDistance']
        currentFirstLayerHeightPercentage = int(min(125, (hotend['nozzleSize']/2)/currentLayerHeight*100, maxFlowValue(hotendLeft, filamentLeft, currentLayerHeight)*100/(hotend['nozzleSize']*currentLayerHeight*(currentDefaultSpeed/60.)*float(currentFirstLayerUnderspeed))))
        firstLayerHeight = "%.2f" % (currentLayerHeight * currentFirstLayerHeightPercentage/100.)
        if filamentLeft['fanPercentage'][1] > 0:
            fanEnabled = 'True'
        else:
            fanEnabled = 'False'
        fanPercentage = fanSpeed(filamentLeft, printTemperature1, currentLayerHeight)
        hotendLeftTemperature, hotendRightTemperature = printTemperature1, 0
        purgeValuesGeneral = purgeValues(hotendLeft, filamentLeft, currentDefaultSpeed, currentLayerHeight)       
        purgeValuesT0 = purgeValuesGeneral
        purgeValuesT1 = purgeValuesGeneral
    else:
        # IDEX
        hotend, extruder, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder = hotendLeft, "Both Extruders", 0, 0, 0
        currentLayerHeight = hotend['nozzleSize'] * quality['layerHeightMultiplier']
        supportZdistance = currentLayerHeight
        fileName = "BCN3D Sigma - "+str(hotendLeft['nozzleSize'])+" Left ("+filamentLeft['id']+"), "+str(hotendRight['nozzleSize'])+" Right ("+filamentRight['id']+") - "+quality['id']
        extruderPrintOptions = ["Both Extruders"] 
        if filamentLeft['isSupportMaterial'] != filamentRight['isSupportMaterial']:
            # IDEX, Support Material
            makeSupports = 'Everywhere'
            supportDualExtrusion = 'Second extruder'
            supportXYDistance = 1
            supportZdistance = 0
            supportType = 'Grid'
            if filamentLeft['isSupportMaterial']:
                # IDEX, Support Material in Left Hotend. For Cura it's not a correct combination
                return
            else:
                # IDEX, Support Material in Right Hotend
                currentSupportExtruder = 1
                currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, currentLayerHeight, 1, quality, 'IDEX, Supports with Right')
                printTemperature1 = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
                printTemperature2 = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed*currentSupportUnderspeed)

        else:
            # IDEX, Dual Color / Material
            makeSupports = 'None'
            supportDualExtrusion = 'Both'
            currentDefaultSpeedL, currentFirstLayerUnderspeedL, currentOutlineUnderspeedL, currentSupportUnderspeedL = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, currentLayerHeight, 1, quality, 'MEX Left')
            currentDefaultSpeedR, currentFirstLayerUnderspeedR, currentOutlineUnderspeedR, currentSupportUnderspeedR = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, currentLayerHeight, 1, quality, 'MEX Right')
            currentDefaultSpeed = min(currentDefaultSpeedL, currentDefaultSpeedR)
            currentFirstLayerUnderspeed = min(currentFirstLayerUnderspeedL, currentFirstLayerUnderspeedR)
            currentOutlineUnderspeed = min(currentOutlineUnderspeedL, currentOutlineUnderspeedR)
            currentSupportUnderspeed  = min(currentSupportUnderspeedL, currentSupportUnderspeedR)
            printTemperature1 = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
            printTemperature2 = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
        bedTemperature = max(filamentLeft['bedTemperature'], filamentRight['bedTemperature'])
        filamentDiameter1 = filamentLeft['filamentDiameter']
        filamentDiameter2 = filamentRight['filamentDiameter']
        filamentFlow = max(filamentLeft['extrusionMultiplier'], filamentRight['extrusionMultiplier'])*100
        retractionSpeed = max(filamentLeft['retractionSpeed'], filamentRight['retractionSpeed'])
        retractionAmount = max(filamentLeft['retractionDistance'], filamentRight['retractionDistance'])
        currentFirstLayerHeightPercentage = int(min(125, (hotend['nozzleSize']/2)/currentLayerHeight*100, min(maxFlowValue(hotendLeft, filamentLeft, currentLayerHeight),maxFlowValue(hotendRight, filamentRight, currentLayerHeight))*100/(hotend['nozzleSize']*currentLayerHeight*(currentDefaultSpeed/60)*float(currentFirstLayerUnderspeed))))
        firstLayerHeight = "%.2f" % (currentLayerHeight * currentFirstLayerHeightPercentage/100.)
        if filamentLeft['fanPercentage'][1] == 0 or filamentRight['fanPercentage'][1] == 0:
            fanEnabled = 'False'
        else:
            fanEnabled = 'True'
        fanPercentage = max(fanSpeed(filamentLeft, printTemperature1, currentLayerHeight), fanSpeed(filamentRight, printTemperature2, currentLayerHeight))
        hotendLeftTemperature, hotendRightTemperature = printTemperature1, printTemperature2
        purgeValuesT0 = purgeValues(hotendLeft, filamentLeft, currentDefaultSpeed, currentLayerHeight)
        purgeValuesT1 = purgeValues(hotendRight, filamentRight, currentDefaultSpeed, currentLayerHeight)
    currentPurgeSpeedT0, currentStartPurgeLengthT0, currentToolChangePurgeLengthT0, currentEParameterT0, currentSParameterT0, currentPParameterT0 = purgeValuesT0
    currentPurgeSpeedT1, currentStartPurgeLengthT1, currentToolChangePurgeLengthT1, currentEParameterT1, currentSParameterT1, currentPParameterT1 = purgeValuesT1
    purgeValuesGeneral = min(currentPurgeSpeedT0, currentPurgeSpeedT1), max(currentStartPurgeLengthT0, currentStartPurgeLengthT1), max(currentToolChangePurgeLengthT0, currentToolChangePurgeLengthT1), max(currentEParameterT0, currentEParameterT1), min(currentSParameterT0, currentSParameterT1), max(currentPParameterT0, currentPParameterT1)
    currentPurgeSpeed, currentStartPurgeLength, currentToolChangePurgeLength, currentEParameter, currentSParameter, currentPParameter = purgeValuesGeneral
    perimeters = 0
    while perimeters*hotend['nozzleSize'] < quality['wallWidth']:
        perimeters += 1
    currentWallThickness = perimeters * hotend['nozzleSize']
    bottomLayerSpeed = int(currentFirstLayerUnderspeed * currentDefaultSpeed/60.)
    outerShellSpeed = int(currentOutlineUnderspeed * currentDefaultSpeed/60.)
    innerShellSpeed = int(outerShellSpeed + (currentDefaultSpeed/60.-outerShellSpeed)/2.)

    ini = []
    ini.append('[profile]\n')
    ini.append('layer_height = '+str(currentLayerHeight)+'\n')
    ini.append('wall_thickness = '+str(currentWallThickness)+'\n')
    ini.append('retraction_enable = True\n')
    ini.append('solid_layer_thickness = '+str(quality['topBottomWidth'])+'\n')
    ini.append('fill_density = '+str(quality['infillPercentage'])+'\n')
    ini.append('nozzle_size = '+str(hotend['nozzleSize'])+'\n')
    ini.append('print_speed = '+str(currentDefaultSpeed/60)+'\n')
    ini.append('print_temperature = '+str(printTemperature1)+'\n')
    ini.append('print_temperature2 = '+str(printTemperature2)+'\n')
    ini.append('print_temperature3 = 0\n')
    ini.append('print_temperature4 = 0\n')
    ini.append('print_temperature5 = 0\n')
    ini.append('print_bed_temperature = '+str(bedTemperature)+'\n')
    ini.append('support = '+makeSupports+'\n')
    ini.append('platform_adhesion = None\n')
    ini.append('support_dual_extrusion = '+supportDualExtrusion+'\n')
    ini.append('wipe_tower = False\n')
    ini.append('wipe_tower_volume = 50\n')
    ini.append('ooze_shield = False\n')
    ini.append('filament_diameter = '+str(filamentDiameter1)+'\n')
    ini.append('filament_diameter2 = '+str(filamentDiameter2)+'\n')
    ini.append('filament_diameter3 = 0\n')
    ini.append('filament_diameter4 = 0\n')
    ini.append('filament_diameter5 = 0\n')
    ini.append('filament_flow = '+str(filamentFlow)+'\n')
    ini.append('retraction_speed = '+str(retractionSpeed)+'\n')
    ini.append('retraction_amount = '+str(retractionAmount)+'\n')
    ini.append('retraction_dual_amount = 8\n')
    ini.append('retraction_min_travel = 1.5\n')
    ini.append('retraction_combing = All\n')
    ini.append('retraction_minimal_extrusion = 0\n')
    ini.append('retraction_hop = '+str("%.2f" % (currentLayerHeight/2.))+'\n')
    ini.append('bottom_thickness = '+str(firstLayerHeight)+'\n')
    ini.append('layer0_width_factor = 100\n')
    ini.append('object_sink = 0\n')
    ini.append('overlap_dual = 0.15\n')
    ini.append('travel_speed = 200\n')
    ini.append('bottom_layer_speed = '+str(bottomLayerSpeed)+'\n')
    ini.append('infill_speed = '+str(currentDefaultSpeed/60)+'\n')
    ini.append('solidarea_speed = '+str(bottomLayerSpeed)+'\n')
    ini.append('inset0_speed = '+str(outerShellSpeed)+'\n')
    ini.append('insetx_speed = '+str(innerShellSpeed)+'\n')
    ini.append('cool_min_layer_time = 5\n')
    ini.append('fan_enabled = '+str(fanEnabled)+'\n')
    ini.append('skirt_line_count = 2\n')
    ini.append('skirt_gap = 2\n')
    ini.append('skirt_minimal_length = 150.0\n')
    ini.append('fan_full_height = 0.5\n')
    ini.append('fan_speed = '+str(fanPercentage)+'\n')
    ini.append('fan_speed_max = 100\n')
    ini.append('cool_min_feedrate = 10\n')
    ini.append('cool_head_lift = False\n')
    ini.append('solid_top = True\n')
    ini.append('solid_bottom = True\n')
    ini.append('fill_overlap = 15\n')
    ini.append('perimeter_before_infill = True\n')
    ini.append('support_type = '+str(supportType)+'\n')
    ini.append('support_angle = 60\n')
    ini.append('support_fill_rate = 40\n')
    ini.append('support_xy_distance = '+str(supportXYDistance)+'\n')
    ini.append('support_z_distance = '+str(supportZdistance)+'\n')
    ini.append('spiralize = False\n')
    ini.append('simple_mode = False\n')
    ini.append('brim_line_count = 5\n')
    ini.append('raft_margin = 5.0\n')
    ini.append('raft_line_spacing = 3.0\n')
    ini.append('raft_base_thickness = 0.3\n')
    ini.append('raft_base_linewidth = 1.0\n')
    ini.append('raft_interface_thickness = 0.27\n')
    ini.append('raft_interface_linewidth = 0.4\n')
    ini.append('raft_airgap_all = 0.0\n')
    ini.append('raft_airgap = 0.22\n')
    ini.append('raft_surface_layers = 2\n')
    ini.append('raft_surface_thickness = 0.27\n')
    ini.append('raft_surface_linewidth = 0.4\n')
    ini.append('fix_horrible_union_all_type_a = True\n')
    ini.append('fix_horrible_union_all_type_b = False\n')
    ini.append('fix_horrible_use_open_bits = False\n')
    ini.append('fix_horrible_extensive_stitching = False\n')
    ini.append('plugin_config = (lp1\n')
    ini.append('\t(dp2\n')
    ini.append("\tS'params'\n")
    ini.append('\tp3\n')
    ini.append('\t(dp4\n')
    ini.append("\tsS'filename'\n")
    ini.append('\tp5\n')
    ini.append("\tS'RingingRemover.py'\n")
    ini.append('\tp6\n')
    ini.append('\tsa.\n')
    ini.append('object_center_x = -1\n')
    ini.append('object_center_y = -1\n')
    ini.append('quality_fast = False\n')
    ini.append('quality_standard = False\n')
    ini.append('quality_high = False\n')
    ini.append('quality_strong = False\n')
    ini.append('extruder_left = False\n')
    ini.append('extruder_right = False\n')
    ini.append('material_pla = False\n')
    ini.append('material_abs = False\n')
    ini.append('material_fila = False\n')
    ini.append('quality_fast_dual = False\n')
    ini.append('quality_standard_dual = False\n')
    ini.append('quality_high_dual = False\n')
    ini.append('quality_strong_dual = False\n')
    ini.append('pla_left_dual = False\n')
    ini.append('abs_left_dual = False\n')
    ini.append('fila_left_dual = False\n')
    ini.append('pla_right_dual = False\n')
    ini.append('abs_right_dual = False\n')
    ini.append('fila_right_dual = False\n')
    ini.append('pva_right_dual = False\n')
    ini.append('dual_support = False\n')
    ini.append('\n')
    ini.append('[alterations]\n')
    ini.append('start.gcode = ;Sliced at: {day} {date} {time}\n')
    ini.append('\t;Profile: '+str(fileName)+'\n')
    ini.append('\t;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}\n')
    ini.append('\t;Print time: {print_time}\n')
    ini.append('\t;Filament used: {filament_amount}m {filament_weight}g\n')
    ini.append('\t;Filament cost: {filament_cost}\n')
    if hotendLeft['id'] != 'None':
        ini.append(firstHeatSequence(printTemperature1, 0, bedTemperature, 'Cura'))
    else:
        ini.append(firstHeatSequence(0, printTemperature2, bedTemperature, 'Cura'))
    ini.append('\tG21                               ;metric values\n')
    ini.append('\tG90                               ;absolute positioning\n')
    ini.append('\tM82                               ;set extruder to absolute mode\n')
    ini.append('\tM107                              ;start with the fan off\n')
    ini.append('\tG28 X0 Y0                         ;move X/Y to min endstops\n')
    ini.append('\tG28 Z0                            ;move Z to min endstops\n')
    ini.append('\tT'+str(currentPrimaryExtruder)+'  ;change to active toolhead\n')
    ini.append('\tG92 E0                            ;zero the extruded length\n')
    ini.append('\tG1 Z5 F1200                       ;Safety Z axis movement\n')
    ini.append('\tG1 F'+str(currentPurgeSpeed)+' E'+str(currentStartPurgeLength)+' ;extrude '+str(currentStartPurgeLength)+'mm of feed stock\n')
    ini.append('\tG92 E0                            ;zero the extruded length again\n')
    ini.append('\tG1 F2400 E-4\n')
    ini.append('\tG1 F{travel_speed}\n')
    ini.append('\tG91\n')
    ini.append('\tG1 F{travel_speed} Z2\n')
    ini.append('\tG90\n')
    ini.append('end.gcode = M104 S0\n')
    ini.append('\tM140 S0                           ;heated bed heater off\n')
    ini.append('\tG91                               ;relative positioning\n')
    ini.append('\tG1 Z+0.5 E-5 Y+10 F{travel_speed} ;move Z up a bit and retract filament even more\n')
    ini.append('\tG28 X0 Y0                         ;move X/Y to min endstops, so the head is out of the way\n')
    ini.append('\tM84                               ;steppers off\n')
    ini.append('\tG90                               ;absolute positioning\n')
    ini.append('\t;{profile_string}\n')
    ini.append('start2.gcode = ;Sliced at: {day} {date} {time}\n')
    ini.append('\t;Profile: '+str(fileName)+'\n')
    ini.append('\t;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}\n')
    ini.append('\t;Print time: {print_time}\n')
    ini.append('\t;Filament used: {filament_amount}m {filament_weight}g\n')
    ini.append('\t;Filament cost: {filament_cost}\n')
    ini.append(firstHeatSequence(printTemperature1, printTemperature2, bedTemperature, 'Cura'))
    ini.append('\tG21                               ;metric values\n')
    ini.append('\tG90                               ;absolute positioning\n')
    ini.append('\tM107                              ;start with the fan off\n')
    ini.append('\tG28 X0 Y0                         ;move X/Y to min endstops\n')
    ini.append('\tG28 Z0                            ;move Z to min endstops\n')
    ini.append('\tT1                                ;switch to the 2nd extruder\n')
    ini.append('\tG92 E0                            ;zero the extruded length\n')
    ini.append('\tG1 F'+str(currentPurgeSpeedT1)+' E'+str(currentStartPurgeLengthT1)+' ;extrude '+str(currentStartPurgeLengthT1)+'mm of feed stock\n')
    ini.append('\tG92 E0                            ;zero the extruded length again\n')
    ini.append('\tG1 F2400 E-{retraction_dual_amount}\n')
    ini.append('\tT0                                ;switch to the 1st extruder\n')
    ini.append('\tG92 E0                            ;zero the extruded length\n')
    ini.append('\tG1 F'+str(currentPurgeSpeedT0)+' E'+str(currentStartPurgeLengthT0)+' ;extrude '+str(currentStartPurgeLengthT0)+'mm of feed stock\n')
    ini.append('\tG92 E0                            ;zero the extruded length again\n')
    ini.append('\tG1 F2400 E-4\n')
    ini.append('\tG1 F{travel_speed}\n')
    ini.append('\tG91\n')
    ini.append('\tG1 F{travel_speed} Z2\n')
    ini.append('\tG90\n')
    ini.append('end2.gcode = M104 T0 S0\n')
    ini.append('\tM104 T1 S0                        ;extruder heater off\n')
    ini.append('\tM140 S0                           ;heated bed heater off\n')
    ini.append('\tG91                               ;relative positioning\n')
    ini.append('\tG1 Z+0.5 E-5 Y+10 F{travel_speed} ;move Z up a bit and retract filament even more\n')
    ini.append('\tG28 X0 Y0                         ;move X/Y to min endstops, so the head is out of the way\n')
    ini.append('\tM84                               ;steppers off\n')
    ini.append('\tG90                               ;absolute positioning\n')
    ini.append('\t;{profile_string}\n')
    ini.append('support_start.gcode = \n')
    ini.append('support_end.gcode = \n')
    ini.append('cool_start.gcode = \n')
    ini.append('cool_end.gcode = \n')
    ini.append('replace.csv = \n')
    ini.append('preswitchextruder.gcode =          ;Switch between the current extruder and the next extruder, when printing with multiple extruders.\n')
    ini.append('\t;This code is added before the T(n)\n')
    ini.append('postswitchextruder.gcode =         ;Switch between the current extruder and the next extruder, when printing with multiple extruders.\n')
    ini.append('\t;This code is added after the T(n)\n')
    ini.append('\tG1 F2400 E0\n')
    ini.append('\t;M800 F'+str(currentPurgeSpeed)+' E'+str(currentEParameter)+' S'+str(currentSParameter)+' P'+str(currentPParameter)+' ;SmartPurge\n')
    ini.append('\tG1 F'+str(currentPurgeSpeed)+' E'+str(currentToolChangePurgeLength)+' ;Default purge\n')
    ini.append("\tG4 P2000 ;Stabilize Hotend's pressure\n")
    ini.append('\tG92 E0 ;Zero extruder\n')
    ini.append('\tG1 F2400 E-4 ;Retract\n')
    ini.append('\tG1 F{travel_speed}\n')
    ini.append('\tG91\n')
    ini.append('\tG1 F{travel_speed} Z2\n')
    ini.append('\tG90\n')

    if dataLog != 'noData' :
        # Store flows, speeds, temperatures and other data
        writeData(extruder, currentDefaultSpeed, 1, currentLayerHeight, hotendLeft, hotendRight, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder, filamentLeft, filamentRight, quality, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed, currentFirstLayerHeightPercentage, hotendLeftTemperature, hotendRightTemperature, bedTemperature, dataLog)

    if createFile == 'createFile':
        f = open(fileName+".ini", "w")
        f.writelines(ini)
        f.close()
    if createFile == '--no-file':
        print string.join(ini, '')
    if createFile == '--only-filename':
        print fileName+'.ini'
    return fileName+'.ini'

def createSimplify3DProfilesBundle(dataLog, profilesCreatedCount):    
    y = 'y'
    if getSimplify3DBundleSize()/1024/1024 >= 150: # define Size limit to notice (in MB)
        print '\t\tEstimated space needed during the process: '+str(int(getSimplify3DBundleSize()*1.075/1024/1024))+' MB.'
        print '\t\tEstimated final bundle size: '+str(int(getSimplify3DBundleSize()*0.075/1024/1024))+' MB.'
        print '\t\tDo you want to continue? (Y/n)'
        while y not in ['Y', 'n']:
            y = raw_input('\t\t')
        print
    else:
        y = 'Y'
    if y == 'Y':
        totalSmaProfiles = (len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2
        totalBigProfiles = (len(profilesData['hotend'])-1)**2 * len(profilesData['filament'])**2
        totalProfilesAvailable = totalSmaProfiles + totalBigProfiles
        if ".BCN3D Sigma - Simplify3D Profiles temp" in os.listdir('.'):
            shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
        os.mkdir(".BCN3D Sigma - Simplify3D Profiles temp")
        os.chdir(".BCN3D Sigma - Simplify3D Profiles temp")
        for hotendLeft in sorted(profilesData['hotend'], key=lambda k: k['id']):
            if hotendLeft['id'] != 'None':
                os.mkdir("Left Hotend "+hotendLeft['id'])
                os.chdir("Left Hotend "+hotendLeft['id'])
            else:
                os.mkdir("No Left Hotend")
                os.chdir("No Left Hotend")
            for hotendRight in sorted(profilesData['hotend'], key=lambda k: k['id']):
                if hotendRight['id'] != 'None':
                    os.mkdir("Right Hotend "+hotendRight['id'])
                    os.chdir("Right Hotend "+hotendRight['id'])
                else:                
                    os.mkdir("No Right Hotend")
                    os.chdir("No Right Hotend")
                for filamentLeft in sorted(profilesData['filament'], key=lambda k: k['id']):
                    for filamentRight in sorted(profilesData['filament'], key=lambda k: k['id']):
                        if hotendRight['id'] == 'None' and hotendLeft['id'] == 'None':
                            break
                        profilesCreatedCount += 1
                        createSimplify3DProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, dataLog, 'createFile')
                        sys.stdout.write("\r\t\tProgress: %d%%" % int(float(profilesCreatedCount)/totalProfilesAvailable*100))
                        sys.stdout.flush()
                        if hotendRight['id'] == 'None':
                            break
                    if hotendLeft['id'] == 'None':
                        break
                os.chdir('..')
            os.chdir('..')
        csv = open("BCN3D Sigma - Simplify3D Profiles.csv", "w")
        csv.writelines(dataLog)
        csv.close()
        os.chdir('..')
        sys.stdout.write("\r\t\tProgress: Creating the zip file...")
        sys.stdout.flush()
        shutil.make_archive('BCN3D Sigma - Simplify3D Profiles', 'zip', '.BCN3D Sigma - Simplify3D Profiles temp')
        shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
        print("\r\t\tYour bundle 'BCN3D Sigma - Simplify3D Profiles.zip' is ready. Enjoy!\n")+'\t',
        return profilesCreatedCount
    else:
        return 0

def getSimplify3DBundleSize(oneLineCsvSize = float(10494984)/78480): # experimental value
    if ".BCN3D Sigma - Simplify3D Profiles temp" in os.listdir('.'):
        shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
    os.mkdir(".BCN3D Sigma - Simplify3D Profiles temp")
    os.chdir(".BCN3D Sigma - Simplify3D Profiles temp")
    
    totalSmaProfiles = (len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2
    totalBigProfiles = (len(profilesData['hotend'])-1)**2 * len(profilesData['filament'])**2

    fileNameBig = createSimplify3DProfile(profilesData['hotend'][0], profilesData['hotend'][0], profilesData['filament'][0], profilesData['filament'][0], 'noData', 'createFile')
    fileNameSmall = createSimplify3DProfile(profilesData['hotend'][0], profilesData['hotend'][-1], profilesData['filament'][0], profilesData['filament'][0], 'noData', 'createFile')
    
    csvSize = oneLineCsvSize * (totalSmaProfiles*len(profilesData['quality']) + totalBigProfiles*len(profilesData['quality'])*3)
    bundleSize = totalSmaProfiles*os.path.getsize(fileNameSmall)+totalBigProfiles*os.path.getsize(fileNameBig) + csvSize

    os.chdir('..')
    shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
    return bundleSize*1.05

def createCuraProfilesBundle(dataLog, profilesCreatedCount):  
    y = 'y'
    if getCuraBundleSize()/1024/1024 >= 150: # define Size limit to notice (in MB)
        print '\t\tEstimated space needed during the process: '+str(int(getSimplify3DBundleSize()*1.075/1024/1024))+' MB.'
        print '\t\tEstimated final bundle size: '+str(int(getSimplify3DBundleSize()*0.075/1024/1024))+' MB.'
        print '\t\tDo you want to continue? (Y/n)'
        while y not in ['Y', 'n']:
            y = raw_input('\t\t')
        print
    else:
        y = 'Y'
    if y == 'Y':
        nozzleSizes = []
        for hotend in sorted(profilesData['hotend'], key=lambda k: k['id'])[:-1]:
            nozzleSizes.append(hotend['nozzleSize'])
        curaGroupedSizes = {x:nozzleSizes.count(x) for x in nozzleSizes}
        curaIDEXHotendsCombinations = 0
        for size in curaGroupedSizes:
            curaIDEXHotendsCombinations += curaGroupedSizes[size]**2
        totalProfilesAvailable = ((len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2 + curaIDEXHotendsCombinations * len(profilesData['filament'])**2) * len(profilesData['quality'])
        if ".BCN3D Sigma - Cura Profiles temp" in os.listdir('.'):
            shutil.rmtree(".BCN3D Sigma - Cura Profiles temp")
        os.mkdir(".BCN3D Sigma - Cura Profiles temp")
        os.chdir(".BCN3D Sigma - Cura Profiles temp")

        for hotendLeft in sorted(profilesData['hotend'], key=lambda k: k['id']):
            if hotendLeft['id'] != 'None':
                os.mkdir("Left Hotend "+hotendLeft['id'])
                os.chdir("Left Hotend "+hotendLeft['id'])
            else:
                os.mkdir("No Left Hotend")
                os.chdir("No Left Hotend")
            for hotendRight in sorted(profilesData['hotend'], key=lambda k: k['id']):
                if hotendRight['id'] != 'None':
                    os.mkdir("Right Hotend "+hotendRight['id'])
                    os.chdir("Right Hotend "+hotendRight['id'])
                else:                
                    os.mkdir("No Right Hotend")
                    os.chdir("No Right Hotend")
                for quality in sorted(profilesData['quality'], key=lambda k: k['index']):
                    os.mkdir(quality['id'])
                    os.chdir(quality['id'])
                    for filamentLeft in sorted(profilesData['filament'], key=lambda k: k['id']):
                        for filamentRight in sorted(profilesData['filament'], key=lambda k: k['id']):
                            if hotendRight['id'] == 'None' and hotendLeft['id'] == 'None':
                                break
                            if hotendLeft['id'] != 'None' and hotendRight['id'] != 'None':
                                if hotendLeft['nozzleSize'] != hotendRight['nozzleSize']:
                                    break
                            profilesCreatedCount += 1
                            createCuraProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, dataLog, 'createFile')
                            sys.stdout.write("\r\t\tProgress: %d%%" % int(float(profilesCreatedCount)/totalProfilesAvailable*100))
                            sys.stdout.flush()
                            if hotendRight['id'] == 'None':
                                break
                        if hotendLeft['id'] == 'None':
                            break
                    os.chdir('..')
                os.chdir('..')
            os.chdir('..')
        csv = open("BCN3D Sigma - Cura Profiles.csv", "w")
        csv.writelines(dataLog)
        csv.close()
        os.chdir('..')
        sys.stdout.write("\r\t\tProgress: Creating the zip file...")
        sys.stdout.flush()
        shutil.make_archive('BCN3D Sigma - Cura Profiles', 'zip', '.BCN3D Sigma - Cura Profiles temp')
        shutil.rmtree(".BCN3D Sigma - Cura Profiles temp")
        print("\r\t\tYour bundle 'BCN3D Sigma - Cura Profiles.zip' is ready. Enjoy!\n")+'\t',
        return profilesCreatedCount
    else:
        return 0

def getCuraBundleSize(oneLineCsvSize = float(10494984)/78480): # experimental value
    if ".BCN3D Sigma - Cura Profiles temp" in os.listdir('.'):
        shutil.rmtree(".BCN3D Sigma - Cura Profiles temp")
    os.mkdir(".BCN3D Sigma - Cura Profiles temp")
    os.chdir(".BCN3D Sigma - Cura Profiles temp")

    nozzleSizes = []
    for hotend in sorted(profilesData['hotend'], key=lambda k: k['id'])[:-1]:
        nozzleSizes.append(hotend['nozzleSize'])
    curaGroupedSizes = {x:nozzleSizes.count(x) for x in nozzleSizes}
    curaIDEXHotendsCombinations = 0
    for size in curaGroupedSizes:
        curaIDEXHotendsCombinations += curaGroupedSizes[size]**2

    totalProfiles = ((len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2 + curaIDEXHotendsCombinations * len(profilesData['filament'])**2) * len(profilesData['quality'])

    fileName = createCuraProfile(profilesData['hotend'][0], profilesData['hotend'][0], profilesData['filament'][0], profilesData['filament'][0], profilesData['quality'][0], 'noData', 'createFile')
    
    csvSize = oneLineCsvSize * totalProfiles
    bundleSize = totalProfiles*os.path.getsize(fileName) + csvSize

    os.chdir('..')
    shutil.rmtree(".BCN3D Sigma - Cura Profiles temp")
    return bundleSize*1.05

def speedMultiplier(hotend, filament):
    if filament['isFlexibleMaterial']:
        return float(filament['defaultPrintSpeed'])/24*hotend['nozzleSize']
    else:
        return float(filament['defaultPrintSpeed'])/60

def purgeValues(hotend, filament, speed, layerHeight, minPurgeLenght = 20): # purge at least 20mm so the filament weight is enough to stay inside the purge container
    baseStartLength04 = 7
    baseToolChangeLength04 = 1.5
    
    # speed adapted to printed area
    # purgeSpeed = float("%.2f" % (speed * hotend['nozzleSize'] * layerHeight / (math.pi * (filament['filamentDiameter']/2.)**2)))

    # speed adapted to improve surplus material storage (maximum purge speed for the hotend's temperature)
    maxPrintSpeed = (max(1, temperatureValue(filament, hotend, layerHeight, speed) - filament['printTemperature'][0])/float(max(1, filament['printTemperature'][1]-filament['printTemperature'][0]))) * maxFlowValue(hotend, filament, layerHeight) / (hotend['nozzleSize']*layerHeight/60.)
    purgeSpeed = float("%.2f" % (maxPrintSpeed * hotend['nozzleSize'] * layerHeight / (math.pi * (filament['filamentDiameter']/2.)**2)))

    startPurgeLength = float("%.2f" % max(10, ((hotend['nozzleSize']/0.4)**2*baseStartLength04*filament['purgeLength']/baseToolChangeLength04)))
    toolChangePurgeLength = float("%.2f" % ((hotend['nozzleSize']/0.4)**2*filament['purgeLength']))

    if hotend['nozzleSize'] >= 0.8:
        maxPurgeLength = 8 + 18 # llargada max highFlow
    else:
        maxPurgeLength = 8 + 14 # llargada max standard
    E = float("%.2f" % (maxPurgeLength * filament['purgeLength']))
    yeldCurve = 1000
    S = float("%.2f" % (math.pi * ((filament['filamentDiameter']/2.)**2 - (hotend['nozzleSize']/2.)**2) * yeldCurve/hotend['nozzleSize']))
    P = float("%.4f" %  ((minPurgeLenght*filament['purgeLength']*(hotend['nozzleSize']/2.)**2) / ((filament['filamentDiameter']/2.)**2)))

    return (purgeSpeed, startPurgeLength, toolChangePurgeLength, E, S, P)

def retractValues(filament):
    if filament['isFlexibleMaterial']:
        useCoasting = 0
        useWipe = 0
        onlyRetractWhenCrossingOutline = 1
        retractBetweenLayers = 0
        useRetractionMinTravel = 1
        retractWhileWiping = 1
        onlyWipeOutlines = 1
    else:
        useCoasting = 0
        useWipe = 0
        onlyRetractWhenCrossingOutline = 0
        retractBetweenLayers = 0
        useRetractionMinTravel = 1
        retractWhileWiping = 1
        onlyWipeOutlines = 1
    return useCoasting, useWipe, onlyRetractWhenCrossingOutline, retractBetweenLayers, useRetractionMinTravel, retractWhileWiping, onlyWipeOutlines

def coastValue(hotend, filament):
    return float("%.2f" % ((hotend['nozzleSize']/0.4)**2*filament['purgeLength']))

def maxFlowValue(hotend, filament, layerHeight):
    if hotend['nozzleSize'] <= 0.6:
        if filament['maxFlow'] == 'None':
            return hotend['nozzleSize']*layerHeight*filament['advisedMaxPrintSpeed']
        else:
            return filament['maxFlow']
    else:
        if filament['maxFlowForHighFlowHotend'] == 'None':
            if filament['maxFlow'] == 'None':
                return hotend['nozzleSize']*layerHeight*filament['advisedMaxPrintSpeed']
            else:
                return filament['maxFlow']
        else:
            return filament['maxFlowForHighFlowHotend']

def temperatureValue(filament, hotend, layerHeight, speed, base = 5):
    # adaptative temperature according to flow values. Rounded to base
    flow = hotend['nozzleSize']*layerHeight*float(speed)/60

    # Warning if something is not working properly
    if int(flow) > int(maxFlowValue(hotend, filament, layerHeight)):
        print "warning! you're trying to print at higher flow than allowed:", filament['id']+':', str(int(flow)), str(int(maxFlowValue(hotend, filament, layerHeight)))

    temperature = int(base * round((filament['printTemperature'][0] + flow/maxFlowValue(hotend, filament, layerHeight) * float(filament['printTemperature'][1]-filament['printTemperature'][0]))/float(base)))
    return temperature

def fanSpeed(filament, temperature, layerHeight, base = 5):
    # adaptative fan speed according to temperature values. Rounded to base
    if filament['printTemperature'][1] - filament['printTemperature'][0] == 0 or filament['fanPercentage'][1] == 0:
        fanSpeed = filament['fanPercentage'][0]
    else:
        fanSpeedForTemperature = int(base * round((filament['fanPercentage'][0] + (temperature-filament['printTemperature'][0])/float(filament['printTemperature'][1]-filament['printTemperature'][0])*float(filament['fanPercentage'][1]-filament['fanPercentage'][0]))/float(base)))
        LayerHeightAtMaxFanSpeed = 0.025
        LayerHeightAtMinFanSpeed = 0.2
        fanSpeedForLayerHeight = int(base * round((filament['fanPercentage'][0] + (layerHeight - LayerHeightAtMaxFanSpeed)/float(LayerHeightAtMinFanSpeed-LayerHeightAtMaxFanSpeed)*float(filament['fanPercentage'][1]-filament['fanPercentage'][0]))/float(base)))
        fanSpeed = max(fanSpeedForTemperature, fanSpeedForLayerHeight)
    return min(fanSpeed, 100) # Repassar. Aquest 100 no hauria de ser necessari

def timeVsTemperature(value, element, action, command):
    hotendParameter1 = 80
    hotendParameter2 = 310
    hotendParameter3 = 25
    bedParameterA1 = 51
    bedParameterA2 = 61
    bedParameterA3 = 19
    bedParameterB1 = 1000
    bedParameterB2 = 90
    bedParameterB3 = 47
    bedParameterB4 = 10

    # return needed time (sec) to reach Temperature (ºC)
    if command == 'getTime':
        temperature = value
        if action == 'heating':
            if element == 'M104 ':
                time = hotendParameter1 * math.log(-(hotendParameter2-hotendParameter3)/(float(temperature)-hotendParameter2))
            elif element == 'M140 ':
                if temperature <= 60:
                    time = bedParameterA1 * math.log(-(bedParameterA2-bedParameterA3)/(float(temperature)-bedParameterA2))
                else:
                    time = bedParameterB1 * math.log(-bedParameterB2/(float(temperature)-bedParameterB2-bedParameterB3))+bedParameterB4
        elif action == 'cooling':
            time = 0
        return max(0, time)

    # return temperature (ºC) reached after heating during given time (sec)
    elif command == 'getTemperature':
        time = value
        if action == 'heating':
            if element == 'M104 ':
                temperature = hotendParameter2 - (hotendParameter2 - hotendParameter3) * math.exp(-time/hotendParameter1)
            elif element == 'M140 ':
                if time <= 180:
                    temperature = bedParameterA2 - (bedParameterA2 - bedParameterA3) * math.exp(-time/bedParameterA1)
                else:
                    temperature = bedParameterB2 + bedParameterB3 - bedParameterB2 * math.exp(-(time - bedParameterB4)/bedParameterB1)
        elif action == 'cooling':
            temperature = 0
        return max(0, temperature)

def firstHeatSequence(leftHotendTemp, rightHotendTemp, bedTemp, software):
    startSequenceString = '; Start Heating Sequence. If you changed temperatures manually all elements may not heat in sync,'
    if software == 'Simplify3D':
        if leftHotendTemp > 0 and rightHotendTemp > 0:
            # IDEX
            timeLeftHotend  = (timeVsTemperature(leftHotendTemp,  'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S[extruder0_temperature]', ' T0,')
            timeRightHotend = (timeVsTemperature(rightHotendTemp, 'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S[extruder1_temperature]', ' T1,')
            timeBed         = (timeVsTemperature(bedTemp,         'M140 ', 'heating', 'getTime'), 'M140 ', 'M190 ', 'S[bed0_temperature]',       ',')
            startTimes = sorted([timeLeftHotend, timeRightHotend, timeBed])
            startSequenceString += startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-2][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
            startSequenceString += startTimes[-2][-4]+startTimes[-2][-2]+startTimes[-2][-1]
            startSequenceString += startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-3][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
            startSequenceString += startTimes[-3][-4]+startTimes[-3][-2]+startTimes[-3][-1]
            startSequenceString += startTimes[-1][-3]+startTimes[-1][-2]+startTimes[-1][-1]
            startSequenceString += startTimes[-2][-3]+startTimes[-2][-2]+startTimes[-2][-1]
            startSequenceString += startTimes[-3][-3]+startTimes[-3][-2]+startTimes[-3][-1]
        else:
            if leftHotendTemp > 0:
                # MEX Left
                timeLeftHotend  = (timeVsTemperature(leftHotendTemp,  'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S[extruder0_temperature]', ' T0,')
                timeBed         = (timeVsTemperature(bedTemp,         'M140 ', 'heating', 'getTime'), 'M140 ', 'M190 ', 'S[bed0_temperature]',       ',')
                startTimes = sorted([timeLeftHotend, timeBed])
                startSequenceString += startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-2][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
                startSequenceString += startTimes[-2][-4]+startTimes[-2][-2]+startTimes[-2][-1]
                startSequenceString += startTimes[-1][-3]+startTimes[-1][-2]+startTimes[-1][-1]
                startSequenceString += startTimes[-2][-3]+startTimes[-2][-2]+startTimes[-2][-1]
            else:
                # MEX Right
                timeRightHotend = (timeVsTemperature(rightHotendTemp, 'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S[extruder1_temperature]', ' T1,')
                timeBed         = (timeVsTemperature(bedTemp,         'M140 ', 'heating', 'getTime'), 'M140 ', 'M190 ', 'S[bed0_temperature]',       ',')
                startTimes = sorted([timeRightHotend, timeBed])
                startSequenceString += startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-2][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
                startSequenceString += startTimes[-2][-4]+startTimes[-2][-2]+startTimes[-2][-1]
                startSequenceString += startTimes[-1][-3]+startTimes[-1][-2]+startTimes[-1][-1]
                startSequenceString += startTimes[-2][-3]+startTimes[-2][-2]+startTimes[-2][-1]
    elif software == 'Cura':
        startSequenceString = '\t;' + startSequenceString[2:-1] + '\n'
        if leftHotendTemp > 0 and rightHotendTemp > 0:
            # IDEX
            timeLeftHotend  = (timeVsTemperature(leftHotendTemp,  'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S{print_temperature}',     ' T0\n')
            timeRightHotend = (timeVsTemperature(rightHotendTemp, 'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S{print_temperature2}',    ' T1\n')
            timeBed         = (timeVsTemperature(bedTemp,         'M140 ', 'heating', 'getTime'), 'M140 ', 'M190 ', 'S{print_bed_temperature}', '\n')
            startTimes = sorted([timeLeftHotend, timeRightHotend, timeBed])
            startSequenceString += '\t'+startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-2][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
            startSequenceString += '\t'+startTimes[-2][-4]+startTimes[-2][-2]+startTimes[-2][-1]
            startSequenceString += '\t'+startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-3][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
            startSequenceString += '\t'+startTimes[-3][-4]+startTimes[-3][-2]+startTimes[-3][-1]
            startSequenceString += '\t'+startTimes[-1][-3]+startTimes[-1][-2]+startTimes[-1][-1]
            startSequenceString += '\t'+startTimes[-2][-3]+startTimes[-2][-2]+startTimes[-2][-1]
            startSequenceString += '\t'+startTimes[-3][-3]+startTimes[-3][-2]+startTimes[-3][-1]
        else:
            if leftHotendTemp > 0:
                # MEX Left
                timeLeftHotend = (timeVsTemperature(leftHotendTemp, 'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S{print_temperature}',     ' T0\n')
                timeBed        = (timeVsTemperature(bedTemp,        'M140 ', 'heating', 'getTime'), 'M140 ', 'M190 ', 'S{print_bed_temperature}', '\n')
                startTimes = sorted([timeLeftHotend, timeBed])
                startSequenceString += '\t'+startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-2][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
                startSequenceString += '\t'+startTimes[-2][-4]+startTimes[-2][-2]+startTimes[-2][-1]
                startSequenceString += '\t'+startTimes[-1][-3]+startTimes[-1][-2]+startTimes[-1][-1]
                startSequenceString += '\t'+startTimes[-2][-3]+startTimes[-2][-2]+startTimes[-2][-1]
            else:
                # MEX Right
                timeRightHotend = (timeVsTemperature(rightHotendTemp, 'M104 ', 'heating', 'getTime'), 'M104 ', 'M109 ', 'S{print_temperature2}', ' T1\n')
                timeBed         = (timeVsTemperature(bedTemp,         'M140 ', 'heating', 'getTime'), 'M140 ', 'M190 ', 'S{print_bed_temperature}',       '\n')
                startTimes = sorted([timeRightHotend, timeBed])
                startSequenceString += '\t'+startTimes[-1][-3]+'S'+str(int(timeVsTemperature(startTimes[-1][0]-startTimes[-2][0], startTimes[-1][-4], 'heating', 'getTemperature')))+startTimes[-1][-1]
                startSequenceString += '\t'+startTimes[-2][-4]+startTimes[-2][-2]+startTimes[-2][-1]
                startSequenceString += '\t'+startTimes[-1][-3]+startTimes[-1][-2]+startTimes[-1][-1]
                startSequenceString += '\t'+startTimes[-2][-3]+startTimes[-2][-2]+startTimes[-2][-1]
    return startSequenceString

def accelerationForPerimeters(nozzleSize, layerHeight, outerWallSpeed, base = 5, multiplier = 30000, defaultAcceleration = 2000):
    return min(defaultAcceleration, int(base * round((nozzleSize * layerHeight * multiplier * 1/(outerWallSpeed**(1/2.)))/float(base))))

def speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, currentLayerHeight, currentInfillLayerInterval, quality, action):
    if action == 'MEX Left' or action == 'IDEX, Infill with Right' or action == 'IDEX, Supports with Right':
        leftExtruderDefaultSpeed = quality['defaultSpeed']*speedMultiplier(hotendLeft, filamentLeft)
        leftExtruderMaxSpeedAtMaxFlow = maxFlowValue(hotendLeft, filamentLeft, currentLayerHeight)/(hotendLeft['nozzleSize']*currentLayerHeight)
        if action == 'IDEX, Infill with Right':
            rightExtruderMaxSpeedAtMaxFlow = maxFlowValue(hotendRight, filamentRight, currentInfillLayerInterval*currentLayerHeight)/(currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize'])
        else:
            rightExtruderMaxSpeedAtMaxFlow = leftExtruderMaxSpeedAtMaxFlow
        if action == 'MEX Left':
            currentDefaultSpeed = int(str(float(min(leftExtruderDefaultSpeed, leftExtruderMaxSpeedAtMaxFlow, rightExtruderMaxSpeedAtMaxFlow, filamentLeft['advisedMaxPrintSpeed'])*60)).split('.')[0])
        else:
            currentDefaultSpeed = int(str(float(min(leftExtruderDefaultSpeed, leftExtruderMaxSpeedAtMaxFlow, rightExtruderMaxSpeedAtMaxFlow, filamentLeft['advisedMaxPrintSpeed'], filamentRight['advisedMaxPrintSpeed'])*60)).split('.')[0])
        maxAllowedUnderspeed = maxFlowValue(hotendLeft, filamentLeft, currentLayerHeight)/(currentLayerHeight*hotendLeft['nozzleSize']*float(currentDefaultSpeed)/60)
        
        if filamentLeft['isFlexibleMaterial']:
            currentFirstLayerUnderspeed = 1.00
            currentOutlineUnderspeed = 1.00
        else:
            currentFirstLayerUnderspeed = float("%.2f" % min(maxAllowedUnderspeed, leftExtruderDefaultSpeed*60*quality['firstLayerUnderspeed'] /float(currentDefaultSpeed)))
            currentOutlineUnderspeed    = float("%.2f" % min(maxAllowedUnderspeed, leftExtruderDefaultSpeed*60*quality['outlineUnderspeed']    /float(currentDefaultSpeed)))

        if action == 'IDEX, Supports with Right':
            currentSupportUnderspeed    = float("%.2f" % min(maxAllowedUnderspeed, maxFlowValue(hotendRight, filamentRight, currentLayerHeight)/float(hotendLeft['nozzleSize'] * quality['layerHeightMultiplier']*hotendRight['nozzleSize']*currentDefaultSpeed/60.)))
        else:
            currentSupportUnderspeed    = float("%.2f" % min(maxAllowedUnderspeed, leftExtruderDefaultSpeed*60*0.9                             /float(currentDefaultSpeed)))

    elif action == 'MEX Right' or action == 'IDEX, Infill with Left' or action == 'IDEX, Supports with Left':
        rightExtruderDefaultSpeed = quality['defaultSpeed']*speedMultiplier(hotendRight, filamentRight)
        rightExtruderMaxSpeedAtMaxFlow = maxFlowValue(hotendRight, filamentRight, currentLayerHeight)/(hotendRight['nozzleSize']*currentLayerHeight)
        if action == 'IDEX, Infill with Left':
            leftExtruderMaxSpeedAtMaxFlow = maxFlowValue(hotendLeft, filamentLeft, currentInfillLayerInterval*currentLayerHeight)/(currentInfillLayerInterval*currentLayerHeight*hotendLeft['nozzleSize'])
        else:
            leftExtruderMaxSpeedAtMaxFlow = rightExtruderMaxSpeedAtMaxFlow
        if action == 'MEX Right':
            currentDefaultSpeed = int(str(float(min(rightExtruderDefaultSpeed, rightExtruderMaxSpeedAtMaxFlow, leftExtruderMaxSpeedAtMaxFlow, filamentRight['advisedMaxPrintSpeed'])*60)).split('.')[0])
        else:
            currentDefaultSpeed = int(str(float(min(rightExtruderDefaultSpeed, rightExtruderMaxSpeedAtMaxFlow, leftExtruderMaxSpeedAtMaxFlow, filamentLeft['advisedMaxPrintSpeed'], filamentRight['advisedMaxPrintSpeed'])*60)).split('.')[0])
        maxAllowedUnderspeed = maxFlowValue(hotendRight, filamentRight, currentLayerHeight)/(currentLayerHeight*hotendRight['nozzleSize']*float(currentDefaultSpeed)/60)

        if filamentRight['isFlexibleMaterial']:
            currentFirstLayerUnderspeed = 1.00
            currentOutlineUnderspeed = 1.00
        else:
            currentFirstLayerUnderspeed = float("%.2f" % min(maxAllowedUnderspeed, rightExtruderDefaultSpeed*60*quality['firstLayerUnderspeed']/float(currentDefaultSpeed)))
            currentOutlineUnderspeed    = float("%.2f" % min(maxAllowedUnderspeed, rightExtruderDefaultSpeed*60*quality['outlineUnderspeed']   /float(currentDefaultSpeed)))

        if action == 'IDEX, Supports with Left':
            currentSupportUnderspeed    = float("%.2f" % min(maxAllowedUnderspeed, maxFlowValue(hotendLeft, filamentLeft, currentLayerHeight)  /float(hotendRight['nozzleSize']*quality['layerHeightMultiplier']*hotendLeft['nozzleSize']*currentDefaultSpeed/60.)))
        else:
            currentSupportUnderspeed    = float("%.2f" % min(maxAllowedUnderspeed, rightExtruderDefaultSpeed*60*0.9                            /float(currentDefaultSpeed)))

    return currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed

def testAllCombinations():

    # Calculate All profiles available for each software
    totalSmaProfiles = (len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2
    totalBigProfiles = (len(profilesData['hotend'])-1)**2 * len(profilesData['filament'])**2
    realSimplify3DProfilesAvailable = totalSmaProfiles + totalBigProfiles

    nozzleSizes = []
    for hotend in sorted(profilesData['hotend'], key=lambda k: k['id'])[:-1]:
        nozzleSizes.append(hotend['nozzleSize'])
    curaGroupedSizes = {x:nozzleSizes.count(x) for x in nozzleSizes}
    curaIDEXHotendsCombinations = 0
    for size in curaGroupedSizes:
        curaIDEXHotendsCombinations += curaGroupedSizes[size]**2

    realCuraProfileaAvailable = (totalSmaProfiles + curaIDEXHotendsCombinations * len(profilesData['filament'])**2) * len(profilesData['quality'])

    # Start iteration
    combinationCount = 0
    totalSimplify3DProfilesAvailable = len(profilesData['hotend'])**2 * len(profilesData['filament'])**2
    for hotendLeft in sorted(profilesData['hotend'], key=lambda k: k['id']):
        for hotendRight in sorted(profilesData['hotend'], key=lambda k: k['id']):
            for filamentLeft in sorted(profilesData['filament'], key=lambda k: k['id']):
                for filamentRight in sorted(profilesData['filament'], key=lambda k: k['id']):
                    createSimplify3DProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, 'noData', 'nothing')
                    combinationCount += 1
                    sys.stdout.write("\r\t\tTesting Simplify3D Profiles: %d%%" % int(float(combinationCount)/totalSimplify3DProfilesAvailable*100))
                    sys.stdout.flush()
    print '\r\t\tTesting Simplify3D Profiles: OK. Profiles tested: '+str(realSimplify3DProfilesAvailable)
    combinationCount = 0
    totalProfilesAvailable = len(profilesData['hotend'])**2 * len(profilesData['filament'])**2 * len(profilesData['quality'])
    for hotendLeft in sorted(profilesData['hotend'], key=lambda k: k['id']):
        for hotendRight in sorted(profilesData['hotend'], key=lambda k: k['id']):
            for filamentLeft in sorted(profilesData['filament'], key=lambda k: k['id']):
                for filamentRight in sorted(profilesData['filament'], key=lambda k: k['id']):
                    for quality in sorted(profilesData['quality'], key=lambda k: k['index']):
                        createCuraProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'noData', 'nothing')
                        combinationCount += 1
                        sys.stdout.write("\r\t\tTesting Cura Profiles:       %d%%" % int(float(combinationCount)/totalProfilesAvailable*100))
                        sys.stdout.flush()
    print '\r\t\tTesting Cura Profiles:       OK. Profiles Tested: '+str(realCuraProfileaAvailable)

    print '\t\tAll '+str(realSimplify3DProfilesAvailable + realCuraProfileaAvailable)+' profiles can be generated!\n'

def selectHotendAndFilament(extruder, header):
    clearDisplay()
    print header
    print "\n\tSelect Sigma's "+extruder+" Hotend (1-"+str(len(profilesData['hotend']))+'):'
    answer0 = ''
    hotendOptions = []
    for c in range(len(profilesData['hotend'])):
        hotendOptions.append(str(c+1))
    materialOptions = []
    for c in range(len(profilesData['filament'])):
        materialOptions.append(str(c+1))
    for hotend in range(len(profilesData['hotend'])):
        print '\t'+str(hotend+1)+'. '+sorted(profilesData['hotend'], key=lambda k: k['id'])[hotend]['id']
    while answer0 not in hotendOptions:
        answer0 = raw_input('\t')
    print '\t'+extruder+' Hotend: '+sorted(profilesData['hotend'], key=lambda k: k['id'])[int(answer0)-1]['id']
    if answer0 != str(int(hotendOptions[-1])):
        clearDisplay()
        print header
        print "\n\tSelect Sigma's "+extruder+" Extruder Loaded Filament (1-"+str(len(profilesData['filament']))+'):'
        answer1 = ''
        for material in range(len(profilesData['filament'])):
            print '\t'+str(material+1)+'. '+sorted(profilesData['filament'], key=lambda k: k['id'])[material]['id']
        while answer1 not in materialOptions:
            answer1 = raw_input('\t')
        print '\t'+extruder+' Extruder Filament: '+sorted(profilesData['filament'], key=lambda k: k['id'])[int(answer1)-1]['id']+'.'
    else:
        answer1 = '1'
    return (int(answer0)-1, int(answer1)-1)

def selectQuality(header):
    clearDisplay()
    print header
    print "\n\tSelect Quality:"
    answer0 = ''
    qualityOptions = []
    for c in range(len(profilesData['quality'])):
        qualityOptions.append(str(c+1))
    for quality in range(len(profilesData['quality'])):
        print '\t'+str(quality+1)+'. '+sorted(profilesData['quality'], key=lambda k: k['index'])[quality]['id']
    while answer0 not in qualityOptions:
        answer0 = raw_input('\t')
    print '\tQuality: '+sorted(profilesData['quality'], key=lambda k: k['index'])[int(answer0)-1]['id']
    return int(answer0)-1   

def validArguments():
    if len(sys.argv) > 1:
        if sys.argv[-1] == '--cura' and (len(sys.argv) == 7 or len(sys.argv) == 8):
            leftHotend = sys.argv[1]+'.json' in os.listdir('./Profiles Data/Hotends') or sys.argv[1] == 'None'
            rightHontend = sys.argv[2]+'.json' in os.listdir('./Profiles Data/Hotends') or sys.argv[2] == 'None'
            leftFilament = sys.argv[3]+'.json' in os.listdir('./Profiles Data/Filaments') or (sys.argv[1] == 'None' and sys.argv[3] == 'None')
            rightFilament = sys.argv[4]+'.json' in os.listdir('./Profiles Data/Filaments') or (sys.argv[2] == 'None' and sys.argv[4] == 'None')
            quality = sys.argv[5]+'.json' in os.listdir('./Profiles Data/Quality Presets')
            if len(sys.argv) == 8:
                fileAction = sys.argv[6] == '--no-file' or sys.argv[6] == '--only-filename'
                return leftHotend and rightHontend and leftFilament and rightFilament and quality and fileAction
            else:
                return leftHotend and rightHontend and leftFilament and rightFilament and quality
        elif sys.argv[-1] == '--simplify3d' and (len(sys.argv) == 6 or len(sys.argv) == 7):
            leftHotend = sys.argv[1]+'.json' in os.listdir('./Profiles Data/Hotends') or sys.argv[1] == 'None'
            rightHontend = sys.argv[2]+'.json' in os.listdir('./Profiles Data/Hotends') or sys.argv[2] == 'None'
            leftFilament = sys.argv[3]+'.json' in os.listdir('./Profiles Data/Filaments') or (sys.argv[1] == 'None' and sys.argv[3] == 'None')
            rightFilament = sys.argv[4]+'.json' in os.listdir('./Profiles Data/Filaments') or (sys.argv[2] == 'None' and sys.argv[4] == 'None')       
            if len(sys.argv) == 7:
                fileAction = sys.argv[5] == '--no-file' or sys.argv[5] == '--only-filename'
                return leftHotend and rightHontend and leftFilament and rightFilament and fileAction
            else:
                return leftHotend and rightHontend and leftFilament and rightFilament           
        else:
            return False
    else:
        return False

def readProfilesData():
    global profilesData
    profilesData = dict([("hotend", []), ("filament", []), ("quality", [])])
    for hotend in os.listdir('./Profiles Data/Hotends'):
        if hotend[-5:] == '.json':
            with open('./Profiles Data/Hotends/'+hotend) as hotend_file:    
                hotendData = json.load(hotend_file)
                profilesData['hotend'].append(hotendData)
    profilesData['hotend'].append(dict([('id', 'None')]))
    for filament in os.listdir('./Profiles Data/Filaments'):
        if filament[-5:] == '.json':
            with open('./Profiles Data/Filaments/'+filament) as filament_file:    
                filamentData = json.load(filament_file)
                profilesData['filament'].append(filamentData)
    for quality in os.listdir('./Profiles Data/Quality Presets'):
        if quality[-5:] == '.json':
            with open('./Profiles Data/Quality Presets/'+quality) as quality_file:    
                qualityData = json.load(quality_file)
                profilesData['quality'].append(qualityData)

def writeData(extruder, currentDefaultSpeed, currentInfillLayerInterval, currentLayerHeight, hotendLeft, hotendRight, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder, filamentLeft, filamentRight, quality, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed, currentFirstLayerHeightPercentage, hotendLeftTemperature, hotendRightTemperature, currentBedTemperature, dataLog):
    if extruder == 'Left Extruder':
        printA = "%.2f" % (float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendLeft['nozzleSize'])
        printB = ""
    elif extruder == 'Right Extruder':
        printA = ""
        printB = "%.2f" % (float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize'])
    else:
        # IDEX
        if filamentLeft['isSupportMaterial'] != filamentRight['isSupportMaterial']:
            if filamentLeft['isSupportMaterial']:
                supportMaterialLoadedLeft  = float(currentSupportUnderspeed)
                supportMaterialLoadedRight = 1
            else:
                supportMaterialLoadedLeft  = 1
                supportMaterialLoadedRight = float(currentSupportUnderspeed)
        else:
            supportMaterialLoadedLeft  = 1
            supportMaterialLoadedRight = 1
        if hotendLeft['nozzleSize'] != hotendRight['nozzleSize']:
            if currentPrimaryExtruder == 0: 
                printA = "%.2f" % (float(currentDefaultSpeed)/60*currentLayerHeight*hotendLeft['nozzleSize']*supportMaterialLoadedLeft)
                printB = "%.2f" % (float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize']*supportMaterialLoadedRight)
            else:
                printA = "%.2f" % (float(currentDefaultSpeed)/60*currentLayerHeight*currentInfillLayerInterval*hotendLeft['nozzleSize']*supportMaterialLoadedLeft)
                printB = "%.2f" % (float(currentDefaultSpeed)/60*currentLayerHeight*hotendRight['nozzleSize']*supportMaterialLoadedRight)
        else:
            printA = "%.2f" % (float(currentDefaultSpeed)/60*1*currentLayerHeight*hotendLeft['nozzleSize']*supportMaterialLoadedLeft)
            printB = "%.2f" % (float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize']*supportMaterialLoadedRight)

        if currentPrimaryExtruder == 0:
            printA = "%.2f" % max(float(printA), float(printA) * currentOutlineUnderspeed, float(printA) * currentFirstLayerHeightPercentage/100. * currentFirstLayerUnderspeed)
        else:
            printB = "%.2f" % max(float(printB), float(printB) * currentOutlineUnderspeed, float(printB) * currentFirstLayerHeightPercentage/100. * currentFirstLayerUnderspeed)


    dataLog.append(filamentLeft['id']+";"+filamentRight['id']+";"+extruder+";"+quality['id']+";"+hotendLeft['id']+";"+hotendRight['id']+";"+'T'+str(currentInfillExtruder)+";"+'T'+str(currentPrimaryExtruder)+";"+'T'+str(currentSupportExtruder)+";"+str(printA)+";"+str(printB)+";"+str(currentInfillLayerInterval)+";"+str("%.2f" % (currentDefaultSpeed/60.))+";"+str(currentFirstLayerUnderspeed)+";"+str(currentOutlineUnderspeed)+";"+str(currentSupportUnderspeed)+";"+str(currentFirstLayerHeightPercentage)+";"+str(hotendLeftTemperature)+";"+str(hotendRightTemperature)+";"+str(currentBedTemperature)+";\n")

def clearDisplay():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

def main():
    if platform.system() == 'Windows':
        # os.system('color f0')
        os.system('mode con: cols=154 lines=35')
    if validArguments():
        readProfilesData()
        for hotend in os.listdir('./Profiles Data/Hotends'):
            if hotend == sys.argv[1]+'.json':
                with open('./Profiles Data/Hotends/'+hotend) as hotend_file:    
                    leftHotend = json.load(hotend_file)
            if hotend == sys.argv[2]+'.json':
                with open('./Profiles Data/Hotends/'+hotend) as hotend_file:    
                    rightHotend = json.load(hotend_file)
        for filament in os.listdir('./Profiles Data/Filaments'):
            if filament == sys.argv[3]+'.json':
                with open('./Profiles Data/Filaments/'+filament) as filament_file:    
                    leftFilament = json.load(filament_file)
            if filament == sys.argv[4]+'.json':
                with open('./Profiles Data/Filaments/'+filament) as filament_file:    
                    rightFilament = json.load(filament_file)
        if sys.argv[1] == 'None':
            leftHotend = dict([('id', 'None')])
        if sys.argv[2] == "None":
            rightHotend = dict([('id', 'None')])
        if sys.argv[3] == 'None':
            leftFilament = profilesData['filament'][0]
        if sys.argv[4] == 'None':
            rightFilament = profilesData['filament'][0]
        if sys.argv[-1] == '--simplify3d':
            if len(sys.argv) == 7:
                if sys.argv[5] == '--no-file' or sys.argv[5] == '--only-filename':
                    createSimplify3DProfile(leftHotend, rightHotend, leftFilament, rightFilament, 'noData', sys.argv[5])
            else:
                createSimplify3DProfile(leftHotend, rightHotend, leftFilament, rightFilament, 'noData', 'createFile')
        elif sys.argv[-1] == '--cura':
            for quality in os.listdir('./Profiles Data/Quality Presets'):
                if quality == sys.argv[5]+'.json':
                    with open('./Profiles Data/Quality Presets/'+quality) as quality_file:    
                        qualityCura = json.load(quality_file)
            if len(sys.argv) == 8:
                if sys.argv[6] == '--no-file' or sys.argv[6] == '--only-filename':
                    createCuraProfile(leftHotend, rightHotend, leftFilament, rightFilament, qualityCura, 'noData', sys.argv[6])
            else:
                createCuraProfile(leftHotend, rightHotend, leftFilament, rightFilament, qualityCura, 'noData', 'createFile')
    else:
        if len(sys.argv) == 1:
            experimentalMenu = False
            while True:
                clearDisplay()
                print '\n Welcome to the BCN3D Sigma Profile Generator \n'
                print ' Choose one option (1-4):'
                print ' 1. Profile for Simplify3D'
                print ' 2. Profile for Cura'
                print ' 3. Experimental features'
                print ' 4. Exit'
                if experimentalMenu:
                    x = '3'
                else: 
                    x = 'x'
                y = 'y'
                while x not in ['1','2','3','4']:
                    x = raw_input(' ')
                dataLog = ["LFilament;RFilament;Extruder;Quality;LNozzle;RNozzle;InfillExt;PrimaryExt;SupportExt;LFlow;RFlow;Layers/Infill;DefaultSpeed;FirstLayerUnderspeed;OutLineUnderspeed;SupportUnderspeed;FirstLayerHeightPercentage;LTemp;RTemp;BTemp;\n"]
                profilesCreatedCount = 0
                readProfilesData()

                if x == '3':
                    clearDisplay()
                    print '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n'
                    print '    Experimental features'
                    print '\n\tChoose one option (1-5):'
                    print '\t1. Generate a bundle of profiles - Simplify3D'
                    print '\t2. Generate a bundle of profiles - Cura'
                    print '\t3. Test all combinations'
                    print '\t4. MacOS Only - Slice a model (with Cura)'
                    print '\t5. Use the SmartPurge algorithm to recalculate purge lengths'
                    print '\t6. Back'
                    x2 = 'x'
                    while x2 not in ['1','2','3','4', '5', '6']:
                        x2 = raw_input('\t')

                singleProfileSimplify3D, singleProfileCura, bundleProfilesSimplify3D, bundleProfilesCura, testComb, sliceModel, smartPurge = False, False, False, False, False, False, False

                if x == '1':
                    singleProfileSimplify3D = True
                    GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n    Profile for Simplify3D'
                elif x == '2':
                    singleProfileCura = True
                    GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n    Profile for Cura'
                elif x == '3':
                    experimentalMenu = True               
                    if x2 == '1':
                        bundleProfilesSimplify3D = True
                        GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n\n    Experimental features\n\n\n\t   Generate a bundle of profiles - Simplify3D\n'
                    elif x2 == '2':
                        bundleProfilesCura = True
                        GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n\n    Experimental features\n\n\n\n\t   Generate a bundle of profiles - Cura\n'
                    elif x2 == '3':
                        testComb = True
                        GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n\n    Experimental features\n\n\n\n\n\t   Test all combinations\n'
                    elif x2 == '4':
                        sliceModel = True
                        GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n\n    Experimental features\n\n\n\n\n\n\t   MacOS Only - Slice a model (with Cura)'
                    elif x2 == '5':
                        smartPurge = True
                        GUIHeader = '\n Welcome to the BCN3D Sigma Profile Generator \n\n\n\n\n    Experimental features\n\n\n\n\n\n\n\t   Use the SmartPurge algorithm to recalculate purge lengths'
                    elif x2 == '6':
                        experimentalMenu = False
                elif x == '4':
                    if platform.system() != 'Windows':
                        print '\n Until next time!\n'
                    break

                if bundleProfilesSimplify3D or bundleProfilesCura or singleProfileSimplify3D or singleProfileCura:
                    if bundleProfilesSimplify3D:
                        clearDisplay()
                        print GUIHeader
                        profilesCreatedCount = createSimplify3DProfilesBundle(dataLog, profilesCreatedCount)
                    elif bundleProfilesCura:
                        clearDisplay()
                        print GUIHeader
                        profilesCreatedCount = createCuraProfilesBundle(dataLog, profilesCreatedCount)
                    elif singleProfileSimplify3D or singleProfileCura:
                        a = selectHotendAndFilament('Left', GUIHeader)
                        b = selectHotendAndFilament('Right', GUIHeader)
                        clearDisplay()
                        print GUIHeader
                        if sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]]['id'] == 'None' and sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]]['id'] == 'None':
                            raw_input("\n\tSelect at least one hotend to create a profile. Press Enter to continue...")
                        else:
                            if singleProfileSimplify3D:
                                print "\n\tYour new Simplify3D profile '"+createSimplify3DProfile(sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]], sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]], sorted(profilesData['filament'], key=lambda k: k['id'])[a[1]], sorted(profilesData['filament'], key=lambda k: k['id'])[b[1]], dataLog, 'createFile')+"' has been created."
                                profilesCreatedCount = 1
                            elif singleProfileCura:
                                makeProfile = True
                                if sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]]['id'] != 'None' and sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]]['id'] != 'None':
                                    if sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]]['nozzleSize'] != sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]]['nozzleSize']:
                                        raw_input("\n\tSelect two hotends with the same nozzle size to create a Cura profile. Press Enter to continue...")
                                        makeProfile = False
                                    elif sorted(profilesData['filament'], key=lambda k: k['id'])[a[1]]['isSupportMaterial'] and not sorted(profilesData['filament'], key=lambda k: k['id'])[b[1]]['isSupportMaterial']:
                                        raw_input("\n\tTo make IDEX prints with Cura using support material, please load the support material to the Right Extruder. Press Enter to continue...")
                                        makeProfile = False
                                if makeProfile:
                                    c = selectQuality(GUIHeader)
                                    clearDisplay()
                                    print GUIHeader
                                    if singleProfileCura:
                                        print "\n\tYour new Cura profile '"+createCuraProfile(sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]], sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]], sorted(profilesData['filament'], key=lambda k: k['id'])[a[1]], sorted(profilesData['filament'], key=lambda k: k['id'])[b[1]], sorted(profilesData['quality'], key=lambda k: k['index'])[c], dataLog, 'createFile')+"' has been created.\n"
                                        print "\tNOTE: To reduce the Ringing effect use the RingingRemover plugin by BCN3D.\n"
                                        profilesCreatedCount = 1

                    if profilesCreatedCount > 0:
                        while y not in ['Y', 'n']:
                            y = raw_input('\tSee profile(s) data? (Y/n) ')
                    if y == 'Y':
                        for l in dataLog:
                            print '\t',
                            for d in string.split(l, ';'):
                                print string.rjust(str(d)[:6], 6),
                        print '\t'+str(profilesCreatedCount)+' profile(s) created with '+str(len(dataLog)-1)+' configurations.\n'
                        raw_input("\tPress Enter to continue...")
                    elif y == 'n':
                        print ''
                elif sliceModel:
                    clearDisplay()
                    print GUIHeader
                    if platform.system() == 'Windows':
                        raw_input("\n\t\tThis feature is not available yet on Windows.\n\t\tPress Enter to continue...")
                    else:
                        if platform.system() == 'Windows':
                            profileFile = raw_input('\n\t\tDrag & Drop your .ini profile to this window. Then press Enter.\n\t\t').replace('"', '')
                            stlFile = raw_input('\n\t\tDrag & Drop your .stl model file to this window. Then press Enter.\n\t\t').replace('"', '')
                        else:
                            profileFile = raw_input('\n\t\tDrag & Drop your .ini profile to this window. Then press Enter.\n\t\t')[:-1].replace('\\', '')
                            stlFile = raw_input('\n\t\tDrag & Drop your .stl model file to this window. Then press Enter.\n\t\t')[:-1].replace('\\', '')
                        os.chdir('..')
                        gcodeFile = stlFile[:-4]+'.gcode'
                        os.system(r'/Applications/Cura/Cura-BCN3D.app/Contents/MacOS/Cura-BCN3D -i "'+profileFile+r'" -s "'+stlFile+r'" -o "'+gcodeFile+r'"')
                        raw_input("\n\t\tYour gcode file '"+string.split(stlFile, '/')[-1][:-4]+'.gcode'+"' has been created! Find it in the same folder as the .stl file.\n\t\tPress Enter to continue...")
                elif testComb:
                    clearDisplay()
                    print GUIHeader              
                    testAllCombinations()
                    raw_input("\t\tPress Enter to continue...")
                elif smartPurge:
                    clearDisplay()
                    print GUIHeader
                    print '\n\t\tWork in progress... Stay tuned!\n\t\t'
                    raw_input("\t\tPress Enter to continue...")

if __name__ == '__main__':
    main() 