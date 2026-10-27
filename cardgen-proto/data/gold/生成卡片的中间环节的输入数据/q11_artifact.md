```cardspec
{
  "title": "电池温度",
  "description": "温度类型和更新",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"电池温度","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/heat_generation.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["temperature"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"temperature","component":"Row","children":["temperature_value"],"itemMargin":0,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"temperature_value","component":"Text","content":"{{ ${/data/phoneBattery/batteryTemperatureText} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["plugged"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"plugged","component":"Column","children":["plugged_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"plugged_item0_label","component":"Text","content":"充电器 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"plugged_item0_value","component":"Text","content":"{{ ${/data/phoneBattery/pluggedTypeDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"plugged_item0","component":"Row","children":["plugged_item0_label","plugged_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"plugged_row0","component":"Row","children":["plugged_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"batteryTemperatureText":"29.0 ℃","pluggedTypeDesc":"未连接充电器"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个电池温度卡片，重点看现在的电池温度，再看充电器类型。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "phoneBattery": {
        "pluggedTypeDesc": {
          "type": "string",
          "description": "当前设备连接的充电器类型文本描述。",
          "sampleValue": "未连接充电器"
        },
        "batteryTemperatureText": {
          "type": "string",
          "description": "可直接显示的当前设备电池实时温度文本，已包含“℃”单位；展示时不得再次追加温度单位。",
          "sampleValue": "29.0 ℃"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.heat_generation",
      "src": "resources/base/media/heat_generation.svg",
      "description": "样式：默认黑色的单色线框温度计，底部为圆形感温泡，内部带弧形刻度；适用：温度、升温、制热或体感温度。"
    },
    {
      "id": "asset.bolt_fill",
      "src": "resources/base/media/bolt_fill.svg",
      "description": "样式：默认黑色的单色实心竖向闪电图标；适用：正在充电、快充、电能或闪电状态。"
    },
    {
      "id": "asset.clock",
      "src": "resources/base/media/clock.svg",
      "description": "样式：时钟线框图标，默认黑色，图形为圆形表盘加指针的线性轮廓；适用：时间显示、定时功能、倒计时。"
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
    "asset.heat_generation",
    "asset.bolt_fill",
    "asset.clock"
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
        "/pluggedTypeDesc",
        "/batteryTemperatureText"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.heat_generation",
    "asset.bolt_fill",
    "asset.clock"
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
  "artifactId": "b66aece6-21cd-4ed3-bdea-c376e7d93da0",
  "createdAt": 1792045394874
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","temperature","plugged"]]
["header","SingleLineTitle",{"title":"电池温度","icon":"resources/base/media/heat_generation.svg","fontSize":12}]
["temperature","EmphasizedData",{"value":{"path":"/data/phoneBattery/batteryTemperatureText"},"fontSize":30}]
["plugged","SecondaryBody",{"items":[{"label":"充电器 ","value":{"path":"/data/phoneBattery/pluggedTypeDesc"}}],"fontSize":14}]
["/data/phoneBattery/batteryTemperatureText","29.0 ℃"]
["/data/phoneBattery/pluggedTypeDesc","未连接充电器"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个电池温度卡片，重点看现在的电池温度，再看充电器类型。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/pluggedTypeDesc",
          "/batteryTemperatureText"
        ]
      }
    ],
    "title": "电池温度",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "温度类型和更新",
    "candidateAssetIds": [
      "asset.heat_generation",
      "asset.bolt_fill",
      "asset.clock"
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
    "time": "20260828000000000"
  },
  "pagination": {
    "limit": 5,
    "start": ""
  },
  "session": {
    "interactionId": "011",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个电池温度卡片，重点看现在的电池温度，再看充电器类型。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个电池温度卡片，重点看现在的电池温度，再看充电器类型。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/pluggedTypeDesc",
        "/batteryTemperatureText"
      ]
    }
  ],
  "title": "电池温度",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "温度类型和更新",
  "candidateAssetIds": [
    "asset.heat_generation",
    "asset.bolt_fill",
    "asset.clock"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"temperature\",\"plugged\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池温度\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"temperature\",\"EmphasizedData\",{\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"},\"fontSize\":30}]\n[\"plugged\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电器 \",\"value\":{\"path\":\"/data/phoneBattery/pluggedTypeDesc\"}}],\"fontSize\":14}]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]\n[\"/data/phoneBattery/pluggedTypeDesc\",\"未连接充电器\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：子组件数量应为 [4]；要求的 children 角色为 [title, primary, support, PillButton]。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"temperature\",\"plugged\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池温度\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"temperature\",\"EmphasizedData\",{\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"},\"fontSize\":30}]\n[\"plugged\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电器 \",\"value\":{\"path\":\"/data/phoneBattery/pluggedTypeDesc\"}}],\"fontSize\":14}]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]\n[\"/data/phoneBattery/pluggedTypeDesc\",\"未连接充电器\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"电池温度\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/heat_generation.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__primary\",\"__layout__root__support\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__primary\",\"component\":\"Column\",\"children\":[\"temperature\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"temperature\",\"component\":\"Row\",\"children\":[\"temperature_value\"],\"itemMargin\":0,\"styles\":{\"justifyContent\":\"start\",\"alignItems\":\"bottom\",\"flexShrink\":0,\"width\":\"matchParent\"}},{\"id\":\"temperature_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batteryTemperatureText} }}\",\"styles\":{\"height\":30,\"fontSize\":30,\"fontWeight\":700,\"lineHeight\":1,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"__layout__root__support\",\"component\":\"Column\",\"children\":[\"plugged\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"end\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"plugged\",\"component\":\"Column\",\"children\":[\"plugged_row0\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"plugged_item0_label\",\"component\":\"Text\",\"content\":\"充电器 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"plugged_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/pluggedTypeDesc} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"plugged_item0\",\"component\":\"Row\",\"children\":[\"plugged_item0_label\",\"plugged_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"plugged_row0\",\"component\":\"Row\",\"children\":[\"plugged_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"batteryTemperatureText\":\"29.0 ℃\",\"pluggedTypeDesc\":\"未连接充电器\"}}}}}",
  "validationErrors": []
}
```
