    <temperatureController name="{{name}}">
        <temperatureNumber>{{temperature_number|default(0)}}</temperatureNumber>
        <isHeatedBed>{{is_heated_bed|int}}</isHeatedBed>
        <relayBetweenLayers>0</relayBetweenLayers>
        <relayBetweenLoops>0</relayBetweenLoops>
        <stabilizeAtStartup>0</stabilizeAtStartup>
        <setpoint layer="1" temperature="{{temperature}}"/>
    </temperatureController>
