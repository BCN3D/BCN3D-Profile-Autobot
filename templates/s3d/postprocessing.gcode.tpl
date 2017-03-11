{REPLACE "; outer perimeter" "; outer perimeter\nM204 S{{quality_preset.perimeter_acceleration()}}"}
{REPLACE "; inner perimeter" "; inner perimeter\nM204 S2000"}
{REPLACE "; solid layer" "; solid layer\nM204 S2000"}
{REPLACE "; infill" "; infill\nM204 S2000"}
{REPLACE "; support" "; support\nM204 S2000"}
{REPLACE "; layer end" "; layer end\nM204 S2000"}
{REPLACE "F12000\nG1 Z{{quality_preset.first_layer_height}} F1002\nG92 E0" "F12000\nG1 Z{{quality_preset.first_layer_height}} F1002\nG1 E0.0000 F720\nG92 E0"}
