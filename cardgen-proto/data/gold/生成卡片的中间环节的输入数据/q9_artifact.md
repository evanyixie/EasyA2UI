```cardspec
{
  "title": "左右耳机",
  "description": "双耳电量和充电状态",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title"],"itemMargin":0,"styles":{"width":"matchParent","height":12,"flexShrink":0,"justifyContent":"start","alignItems":"center"}},{"id":"header_title","component":"Text","content":"耳机状态","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":0,"width":"matchParent","fontColor":"#991F4799"}},{"id":"__layout__root__body","component":"Column","children":["left","right"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1,"height":108}},{"id":"left","component":"Column","children":["left_text"],"itemMargin":0,"styles":{"padding":{"left":8,"right":8},"borderRadius":16,"alignItems":"start","justifyContent":"center","clip":true,"flexShrink":0,"width":"matchParent","backgroundColor":"#CCFFFFFF","layoutWeight":50.0}},{"id":"left_text","component":"Column","children":["left_primary","left_secondary"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"center","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"left_primary","component":"Text","content":"{{ '左耳 ' + ${/data/earphone/leftBatteryLevel} + '%' }}","styles":{"height":22,"fontSize":16,"fontWeight":700,"maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"left_secondary","component":"Text","content":"{{ ${/data/earphone/leftChargingStatusDesc} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"textOverflow":"ellipsis","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#991F4799"}},{"id":"right","component":"Column","children":["right_text"],"itemMargin":0,"styles":{"padding":{"left":8,"right":8},"borderRadius":16,"alignItems":"start","justifyContent":"center","clip":true,"flexShrink":0,"width":"matchParent","backgroundColor":"#CCFFFFFF","layoutWeight":50.0}},{"id":"right_text","component":"Column","children":["right_primary","right_secondary"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"center","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"right_primary","component":"Text","content":"{{ '右耳 ' + ${/data/earphone/rightBatteryLevel} + '%' }}","styles":{"height":22,"fontSize":16,"fontWeight":700,"maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"right_secondary","component":"Text","content":"{{ ${/data/earphone/rightChargingStatusDesc} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"textOverflow":"ellipsis","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#991F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"earphone":{"leftBatteryLevel":76,"leftChargingStatusDesc":"未充电","rightBatteryLevel":78,"rightChargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个耳机状态卡片，分别看左右耳机电量，再看各自是否在充电。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "earphone": {
        "leftBatteryLevel": {
          "type": "integer",
          "description": "左耳机当前剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”；未连接时为 0。若直接用于文本展示，必须在数值后追加“%”。",
          "sampleValue": 76
        },
        "leftChargingStatusDesc": {
          "type": "string",
          "description": "左耳机当前的充电状态中文语义描述，'充电中' 或 '未充电'。",
          "sampleValue": "未充电"
        },
        "rightBatteryLevel": {
          "type": "integer",
          "description": "右耳机当前剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”；未连接时为 0。若直接用于文本展示，必须在数值后追加“%”。",
          "sampleValue": 78
        },
        "rightChargingStatusDesc": {
          "type": "string",
          "description": "右耳机当前的充电状态中文语义描述，'充电中' 或 '未充电'。",
          "sampleValue": "未充电"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.icon_left",
      "src": "resources/base/media/icon_left.svg",
      "description": "样式：默认黑色的单色实心圆形徽标，内部以镂空显示大写 L，源文件语义为左耳机，支持通过 fillColor 与卡片配色统一；适用：左耳、左声道、左侧耳机电量。"
    },
    {
      "id": "asset.icon_right",
      "src": "resources/base/media/icon_right.svg",
      "description": "样式：默认黑色的单色实心圆形徽标，内部以镂空显示大写 R，源文件语义为右耳机，支持通过 fillColor 与卡片配色统一；适用：右耳、右声道、右侧耳机电量。"
    },
    {
      "id": "asset.icon_earphone",
      "src": "resources/base/media/icon_earphone.svg",
      "description": "样式：默认黑色的单色左右分体式开放耳机，局部通过镂空表现高光与分隔，支持通过 fillColor 与卡片配色统一；适用：无线耳机本体、耳机连接、左右耳设备状态。"
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
    "GetEarphoneInfo"
  ],
  "event": [],
  "asset": [
    "asset.icon_left",
    "asset.icon_right",
    "asset.icon_earphone",
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
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/leftBatteryLevel",
        "/leftChargingStatusDesc",
        "/rightBatteryLevel",
        "/rightChargingStatusDesc"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.icon_left",
    "asset.icon_right",
    "asset.icon_earphone",
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
  "artifactId": "57e54536-fa90-488b-aad7-be18c2a4b2eb",
  "createdAt": 1792045385633
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","variant":"stacked-info","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","left","right"]]
["header","SingleLineTitle",{"title":"耳机状态","fontSize":12}]
["left","InfoBlock",{"variant":"stacked","primaryText":"{{ '左耳 ' + ${/data/earphone/leftBatteryLevel} + '%' }}","secondaryText":{"path":"/data/earphone/leftChargingStatusDesc"},"backgroundColor":"#CCFFFFFF"}]
["right","InfoBlock",{"variant":"stacked","primaryText":"{{ '右耳 ' + ${/data/earphone/rightBatteryLevel} + '%' }}","secondaryText":{"path":"/data/earphone/rightChargingStatusDesc"},"backgroundColor":"#CCFFFFFF"}]
["/data/earphone/leftBatteryLevel",76]
["/data/earphone/leftChargingStatusDesc","未充电"]
["/data/earphone/rightBatteryLevel",78]
["/data/earphone/rightChargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个耳机状态卡片，分别看左右耳机电量，再看各自是否在充电。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/leftBatteryLevel",
          "/leftChargingStatusDesc",
          "/rightBatteryLevel",
          "/rightChargingStatusDesc"
        ]
      }
    ],
    "title": "左右耳机",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "双耳电量和充电状态",
    "candidateAssetIds": [
      "asset.icon_left",
      "asset.icon_right",
      "asset.icon_earphone",
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
    "time": "20260828000000000"
  },
  "pagination": {
    "limit": 5,
    "start": ""
  },
  "session": {
    "interactionId": "009",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个耳机状态卡片，分别看左右耳机电量，再看各自是否在充电。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个耳机状态卡片，分别看左右耳机电量，再看各自是否在充电。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/leftBatteryLevel",
        "/leftChargingStatusDesc",
        "/rightBatteryLevel",
        "/rightChargingStatusDesc"
      ]
    }
  ],
  "title": "左右耳机",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "双耳电量和充电状态",
  "candidateAssetIds": [
    "asset.icon_left",
    "asset.icon_right",
    "asset.icon_earphone",
    "asset.bolt_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"variant\":\"stacked-info\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"left\",\"right\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"耳机状态\",\"fontSize\":12}]\n[\"left\",\"InfoBlock\",{\"variant\":\"stacked\",\"primaryText\":\"{{ '左耳 ' + ${/data/earphone/leftBatteryLevel} + '%' }}\",\"secondaryText\":{\"path\":\"/data/earphone/leftChargingStatusDesc\"},\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"right\",\"InfoBlock\",{\"variant\":\"stacked\",\"primaryText\":\"{{ '右耳 ' + ${/data/earphone/rightBatteryLevel} + '%' }}\",\"secondaryText\":{\"path\":\"/data/earphone/rightChargingStatusDesc\"},\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"/data/earphone/leftBatteryLevel\",76]\n[\"/data/earphone/leftChargingStatusDesc\",\"未充电\"]\n[\"/data/earphone/rightBatteryLevel\",78]\n[\"/data/earphone/rightChargingStatusDesc\",\"未充电\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":12,\"flexShrink\":0,\"justifyContent\":\"start\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"耳机状态\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":0,\"width\":\"matchParent\",\"fontColor\":\"#991F4799\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"left\",\"right\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1,\"height\":108}},{\"id\":\"left\",\"component\":\"Column\",\"children\":[\"left_text\"],\"itemMargin\":0,\"styles\":{\"padding\":{\"left\":8,\"right\":8},\"borderRadius\":16,\"alignItems\":\"start\",\"justifyContent\":\"center\",\"clip\":true,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#CCFFFFFF\",\"layoutWeight\":50.0}},{\"id\":\"left_text\",\"component\":\"Column\",\"children\":[\"left_primary\",\"left_secondary\"],\"itemMargin\":0,\"styles\":{\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"left_primary\",\"component\":\"Text\",\"content\":\"{{ '左耳 ' + ${/data/earphone/leftBatteryLevel} + '%' }}\",\"styles\":{\"height\":22,\"fontSize\":16,\"fontWeight\":700,\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\",\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"left_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/leftChargingStatusDesc} }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"textOverflow\":\"ellipsis\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\",\"fontColor\":\"#991F4799\"}},{\"id\":\"right\",\"component\":\"Column\",\"children\":[\"right_text\"],\"itemMargin\":0,\"styles\":{\"padding\":{\"left\":8,\"right\":8},\"borderRadius\":16,\"alignItems\":\"start\",\"justifyContent\":\"center\",\"clip\":true,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#CCFFFFFF\",\"layoutWeight\":50.0}},{\"id\":\"right_text\",\"component\":\"Column\",\"children\":[\"right_primary\",\"right_secondary\"],\"itemMargin\":0,\"styles\":{\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"right_primary\",\"component\":\"Text\",\"content\":\"{{ '右耳 ' + ${/data/earphone/rightBatteryLevel} + '%' }}\",\"styles\":{\"height\":22,\"fontSize\":16,\"fontWeight\":700,\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\",\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"right_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/rightChargingStatusDesc} }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"textOverflow\":\"ellipsis\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\",\"fontColor\":\"#991F4799\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"earphone\":{\"leftBatteryLevel\":76,\"leftChargingStatusDesc\":\"未充电\",\"rightBatteryLevel\":78,\"rightChargingStatusDesc\":\"未充电\"}}}}}",
  "validationErrors": []
}
```
