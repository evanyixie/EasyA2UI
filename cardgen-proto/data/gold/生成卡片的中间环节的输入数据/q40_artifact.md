```cardspec
{
  "title": "充电健康",
  "description": "电量+充电+电池健康",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","body_flow"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"手机电池","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/battery_leaf_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"body_flow","component":"Column","children":["content_flow"],"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"end"},"itemMargin":0},{"id":"content_flow","component":"Column","children":["battery","support"],"itemMargin":6,"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"start"}},{"id":"battery","component":"Row","children":["battery_value","battery_unit"],"itemMargin":2,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"battery_value","component":"Text","content":"{{ ${/data/phoneBattery/batterySOC} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"battery_unit","component":"Text","content":"%","styles":{"height":13.25,"fontSize":12,"fontWeight":500,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","padding":{"top":0,"right":0,"bottom":1.25,"left":0},"textOverflow":"clip"}},{"id":"support","component":"Column","children":["support_row0","support_row1","support_row2"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"support_item0_label","component":"Text","content":"充电状态 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"support_item0_value","component":"Text","content":"{{ ${/data/phoneBattery/chargingStatusDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"support_item0","component":"Row","children":["support_item0_label","support_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"support_row0","component":"Row","children":["support_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"support_item1_label","component":"Text","content":"电池健康 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"support_item1_value","component":"Text","content":"{{ ${/data/phoneBattery/healthStatusDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"support_item1","component":"Row","children":["support_item1_label","support_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"support_row1","component":"Row","children":["support_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"support_item2_label","component":"Text","content":"充电器 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"support_item2_value","component":"Text","content":"{{ ${/data/phoneBattery/pluggedTypeDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"support_item2","component":"Row","children":["support_item2_label","support_item2_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"support_row2","component":"Row","children":["support_item2"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"batterySOC":68,"chargingStatusDesc":"未充电","healthStatusDesc":"正常","pluggedTypeDesc":"未连接充电器"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个电池卡片，查看剩余电量、充电状态和电池健康等信息。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "phoneBattery": {
        "batterySOC": {
          "type": "integer",
          "description": "当前手机设备剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”。若直接用于文本展示，必须在数值后追加“%”；优先使用 batterySOCText。",
          "sampleValue": 68
        },
        "chargingStatusDesc": {
          "type": "string",
          "description": "当前设备电池的充电状态文本描述。",
          "sampleValue": "未充电"
        },
        "healthStatusDesc": {
          "type": "string",
          "description": "当前设备电池的物理健康状态文本描述。",
          "sampleValue": "正常"
        },
        "pluggedTypeDesc": {
          "type": "string",
          "description": "当前设备连接的充电器类型文本描述。",
          "sampleValue": "未连接充电器"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.battery_leaf_fill",
      "src": "resources/base/media/battery_leaf_fill.svg",
      "description": "样式：默认黑色的单色实心横向电池图标，电池内部为叶片留白；适用：电池相关场景，包括电量、省电模式、节能电池、绿色用电状态，也可作为电池健康或电池温度信息的辅助图标，相关数据可结合 GetPhoneBatteryInfo 展示。图标本身不表示具体电量、健康等级或温度高低。"
    },
    {
      "id": "asset.bolt_fill",
      "src": "resources/base/media/bolt_fill.svg",
      "description": "样式：默认黑色的单色实心竖向闪电图标；适用：正在充电、快充、电能或闪电状态。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetPhoneBatteryInfo"
  ],
  "event": [],
  "asset": [
    "asset.battery_leaf_fill",
    "asset.bolt_fill"
  ]
}
```
```removedcapabilities
[]
```
```generationplan
{
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC",
        "/chargingStatusDesc",
        "/healthStatusDesc",
        "/pluggedTypeDesc"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.bolt_fill"
  ]
}
```
```meta
{
  "apiVersion": "v1",
  "taskSpecVersion": "task-spec-v1",
  "cardSpecVersion": "card-spec-v1",
  "dslProtocolVersion": "v0.9",
  "skillVersion": "skill-widget-v1",
  "protocolProfileId": "a2ui-form-rom6.0-v1",
  "capabilityRegistryVersion": "app-11.7.7.300_rom-7.0",
  "artifactSchemaVersion": "widget-artifact-v2",
  "generationMode": "create",
  "artifactId": "edfb4689-945a-4519-99c5-250cd8430bae",
  "createdAt": 1792045552082
}
```
```designcompactdsl
["root","Column",{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"itemMargin":6,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","body_flow"]]
["header","SingleLineTitle",{"title":"手机电池","icon":"resources/base/media/battery_leaf_fill.svg","fontSize":12,"width":"matchParent"}]
["body_flow","Column",{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"end"},["content_flow"]]
["content_flow","Column",{"width":"matchParent","layoutWeight":1,"itemMargin":6,"alignItems":"start","justifyContent":"start"},["battery","support"]]
["battery","EmphasizedData",{"value":"{{ ${/data/phoneBattery/batterySOC} + '%' }}","fontSize":30,"width":"matchParent"}]
["support","SecondaryBody",{"items":[{"label":"充电状态 ","value":{"path":"/data/phoneBattery/chargingStatusDesc"}},{"label":"电池健康 ","value":{"path":"/data/phoneBattery/healthStatusDesc"}},{"label":"充电器 ","value":{"path":"/data/phoneBattery/pluggedTypeDesc"}}],"columns":1,"fontSize":12,"width":"matchParent"}]
["/data/phoneBattery/batterySOC",68]
["/data/phoneBattery/chargingStatusDesc","未充电"]
["/data/phoneBattery/healthStatusDesc","正常"]
["/data/phoneBattery/pluggedTypeDesc","未连接充电器"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个电池卡片，查看剩余电量、充电状态和电池健康等信息。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/batterySOC",
          "/chargingStatusDesc",
          "/healthStatusDesc",
          "/pluggedTypeDesc"
        ]
      }
    ],
    "title": "充电健康",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "电量+充电+电池健康",
    "candidateAssetIds": [
      "asset.battery_leaf_fill",
      "asset.bolt_fill"
    ]
  },
  "deviceInfo": {
    "countryCode": "CN",
    "deviceFormation": "HDSpeaker",
    "deviceType": 0,
    "locale": "zh-CN",
    "phoneType": "SGT-AL10",
    "prdVer": "11.9.9.342",
    "sysVer": "EmotionUI_9.0.0",
    "time": "20260821000000000"
  },
  "pagination": {
    "limit": 5,
    "start": ""
  },
  "session": {
    "interactionId": "040",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个电池卡片，查看剩余电量、充电状态和电池健康等信息。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个电池卡片，查看剩余电量、充电状态和电池健康等信息。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC",
        "/chargingStatusDesc",
        "/healthStatusDesc",
        "/pluggedTypeDesc"
      ]
    }
  ],
  "title": "充电健康",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "电量+充电+电池健康",
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.bolt_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"battery\",\"support\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"手机电池\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"fontSize\":12}]\n[\"battery\",\"EmphasizedData\",{\"value\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\",\"fontSize\":30}]\n[\"support\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电状态 \",\"value\":{\"path\":\"/data/phoneBattery/chargingStatusDesc\"}},{\"label\":\"电池健康 \",\"value\":{\"path\":\"/data/phoneBattery/healthStatusDesc\"}},{\"label\":\"充电器 \",\"value\":{\"path\":\"/data/phoneBattery/pluggedTypeDesc\"}}],\"columns\":1,\"fontSize\":12}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/phoneBattery/chargingStatusDesc\",\"未充电\"]\n[\"/data/phoneBattery/healthStatusDesc\",\"正常\"]\n[\"/data/phoneBattery/pluggedTypeDesc\",\"未连接充电器\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"body_flow\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"手机电池\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/battery_leaf_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"body_flow\",\"component\":\"Column\",\"children\":[\"content_flow\"],\"styles\":{\"width\":\"matchParent\",\"layoutWeight\":1,\"alignItems\":\"start\",\"justifyContent\":\"end\"},\"itemMargin\":0},{\"id\":\"content_flow\",\"component\":\"Column\",\"children\":[\"battery\",\"support\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"layoutWeight\":1,\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"battery\",\"component\":\"Row\",\"children\":[\"battery_value\",\"battery_unit\"],\"itemMargin\":2,\"styles\":{\"justifyContent\":\"start\",\"alignItems\":\"bottom\",\"flexShrink\":0,\"width\":\"matchParent\"}},{\"id\":\"battery_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batterySOC} }}\",\"styles\":{\"height\":30,\"fontSize\":30,\"fontWeight\":700,\"lineHeight\":1,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"battery_unit\",\"component\":\"Text\",\"content\":\"%\",\"styles\":{\"height\":13.25,\"fontSize\":12,\"fontWeight\":500,\"lineHeight\":1,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"padding\":{\"top\":0,\"right\":0,\"bottom\":1.25,\"left\":0},\"textOverflow\":\"clip\"}},{\"id\":\"support\",\"component\":\"Column\",\"children\":[\"support_row0\",\"support_row1\",\"support_row2\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"support_item0_label\",\"component\":\"Text\",\"content\":\"充电状态 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"support_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/chargingStatusDesc} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"support_item0\",\"component\":\"Row\",\"children\":[\"support_item0_label\",\"support_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"support_row0\",\"component\":\"Row\",\"children\":[\"support_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"support_item1_label\",\"component\":\"Text\",\"content\":\"电池健康 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"support_item1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/healthStatusDesc} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"support_item1\",\"component\":\"Row\",\"children\":[\"support_item1_label\",\"support_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"support_row1\",\"component\":\"Row\",\"children\":[\"support_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"support_item2_label\",\"component\":\"Text\",\"content\":\"充电器 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"support_item2_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/pluggedTypeDesc} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"support_item2\",\"component\":\"Row\",\"children\":[\"support_item2_label\",\"support_item2_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"support_row2\",\"component\":\"Row\",\"children\":[\"support_item2\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"batterySOC\":68,\"chargingStatusDesc\":\"未充电\",\"healthStatusDesc\":\"正常\",\"pluggedTypeDesc\":\"未连接充电器\"}}}}}",
  "validationErrors": []
}
```
