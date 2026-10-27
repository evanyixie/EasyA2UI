```cardspec
{
  "title": "出门设备",
  "description": "手机和耳机状态",
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
    },
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__content"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title"],"itemMargin":0,"styles":{"width":"matchParent","height":12,"flexShrink":0,"justifyContent":"start","alignItems":"center"}},{"id":"header_title","component":"Text","content":"出门设备状态","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":0,"width":"matchParent","fontColor":"#991F4799"}},{"id":"__layout__root__content","component":"Column","children":["devices"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"devices","component":"Column","children":["devices_row0","devices_row1","devices_row2"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"devices_row0","component":"Row","children":["devices_row0_label","devices_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"devices_row0_label","component":"Text","content":"手机电量","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"devices_row0_value","component":"Text","content":"{{ ${/data/phoneBattery/batterySOC} + '%' }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"devices_row1","component":"Row","children":["devices_row1_label","devices_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"devices_row1_label","component":"Text","content":"耳机仓电量","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"devices_row1_value","component":"Text","content":"{{ ${/data/earphone/batteryLevel} + '%' }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"devices_row2","component":"Row","children":["devices_row2_label","devices_row2_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"devices_row2_label","component":"Text","content":"耳机连接","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"devices_row2_value","component":"Text","content":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"batterySOC":68},"earphone":{"batteryLevel":80,"isConnected":true}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "出门前帮我做个设备状态卡片，看手机剩余电量、耳机仓电量和耳机是否连接。",
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
        }
      },
      "earphone": {
        "batteryLevel": {
          "type": "integer",
          "description": "耳机盒（或整体）当前剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”。若直接用于文本展示，必须在数值后追加“%”。",
          "sampleValue": 80
        },
        "isConnected": {
          "type": "boolean",
          "description": "当前是否有蓝牙耳机处于连接活跃状态。",
          "sampleValue": true
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.phone_fill",
      "src": "resources/base/media/phone_fill.svg",
      "description": "样式：电话实心图标，默认黑色，图形为经典听筒造型；适用：拨打电话、通话功能入口。"
    },
    {
      "id": "asset.earphone_case_16644",
      "src": "resources/base/media/earphone_case_16644.svg",
      "description": "样式：耳机收纳盒实心图标，默认黑色，图形为无线耳机充电盒造型；适用：蓝牙耳机设备连接、音频设备管理。"
    },
    {
      "id": "asset.icon_earphone",
      "src": "resources/base/media/icon_earphone.svg",
      "description": "样式：默认黑色的单色左右分体式开放耳机，局部通过镂空表现高光与分隔，支持通过 fillColor 与卡片配色统一；适用：无线耳机本体、耳机连接、左右耳设备状态。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetPhoneBatteryInfo",
    "GetEarphoneInfo"
  ],
  "event": [],
  "asset": [
    "asset.phone_fill",
    "asset.earphone_case_16644",
    "asset.icon_earphone"
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
        "/batterySOC"
      ]
    },
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/batteryLevel",
        "/isConnected"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.phone_fill",
    "asset.earphone_case_16644",
    "asset.icon_earphone"
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
  "artifactId": "8cc62c25-9e36-4696-acf6-e1fa8a255ffe",
  "createdAt": 1792045439483
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","devices"]]
["header","SingleLineTitle",{"title":"出门设备状态","fontSize":12}]
["devices","TableText",{"items":[{"label":"手机电量","value":"{{ ${/data/phoneBattery/batterySOC} + '%' }}"},{"label":"耳机仓电量","value":"{{ ${/data/earphone/batteryLevel} + '%' }}"},{"label":"耳机连接","value":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}"}],"fontSize":10}]
["/data/phoneBattery/batterySOC",68]
["/data/earphone/batteryLevel",80]
["/data/earphone/isConnected",true]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "出门前帮我做个设备状态卡片，看手机剩余电量、耳机仓电量和耳机是否连接。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/batterySOC"
        ]
      },
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/batteryLevel",
          "/isConnected"
        ]
      }
    ],
    "title": "出门设备",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "手机和耳机状态",
    "candidateAssetIds": [
      "asset.phone_fill",
      "asset.earphone_case_16644",
      "asset.icon_earphone"
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
    "interactionId": "020",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "出门前帮我做个设备状态卡片，看手机剩余电量、耳机仓电量和耳机是否连接。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "出门前帮我做个设备状态卡片，看手机剩余电量、耳机仓电量和耳机是否连接。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC"
      ]
    },
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/batteryLevel",
        "/isConnected"
      ]
    }
  ],
  "title": "出门设备",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "手机和耳机状态",
  "candidateAssetIds": [
    "asset.phone_fill",
    "asset.earphone_case_16644",
    "asset.icon_earphone"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"phone_battery\",\"earphone_battery\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"出门设备状态\",\"icon\":\"resources/base/media/icon_earphone.svg\",\"fontSize\":12}]\n[\"phone_battery\",\"InfoBlock\",{\"primaryText\":{\"path\":\"/data/phoneBattery/batterySOC\"},\"unit\":\"%\",\"secondaryText\":\"手机剩余电量\",\"visual\":{\"type\":\"progressCircle\",\"icon\":\"resources/base/media/phone_fill.svg\"},\"fillColor\":\"#991F4799\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"earphone_battery\",\"InfoBlock\",{\"primaryText\":{\"path\":\"/data/earphone/batteryLevel\"},\"unit\":\"%\",\"secondaryText\":\"耳机仓剩余电量\",\"visual\":{\"type\":\"progressCircle\",\"icon\":\"resources/base/media/earphone_case_16644.svg\"},\"fillColor\":\"#991F4799\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/earphone/batteryLevel\",80]\n[\"/data/earphone/isConnected\",true]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：两个 InfoBlock 必须使用 stacked-info 变体。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"variant\":\"stacked-info\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"phone_battery\",\"earphone_battery\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"出门设备状态\",\"icon\":\"resources/base/media/icon_earphone.svg\",\"fontSize\":12}]\n[\"phone_battery\",\"InfoBlock\",{\"variant\":\"stacked\",\"primaryText\":{\"path\":\"/data/phoneBattery/batterySOC\"},\"unit\":\"%\",\"secondaryText\":\"手机剩余电量\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"earphone_battery\",\"InfoBlock\",{\"variant\":\"stacked\",\"primaryText\":{\"path\":\"/data/earphone/batteryLevel\"},\"unit\":\"%\",\"secondaryText\":\"耳机仓剩余电量\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/earphone/batteryLevel\",80]\n[\"/data/earphone/isConnected\",true]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_PLAN_COVERAGE_FAILED",
      "message": "Plan fact is missing from visible DSL: 耳机是否连接 (/data/earphone/isConnected)."
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 134vp within 126vp; it overflows by 8vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=108vp+margin(0vp), gaps=6vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 134vp within 126vp; it overflows by 8vp. Occupancy: header=20vp+margin(0vp), __layout__root__body=108vp+margin(0vp), gaps=6vp.",
          "legacyMessage": "component root: vertical layout requires at least 134vp within 126vp; it overflows by 8vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=108vp+margin(0vp), gaps=6vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 134.0,
            "overflow": 8.0,
            "occupancy": "header=20vp+margin(0vp), __layout__root__body=108vp+margin(0vp), gaps=6vp",
            "removableTitleIcon": {
              "componentId": "header",
              "heightSaving": 8.0
            }
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__body: vertical layout requires at least 108vp within 100vp; it overflows by 8vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: phone_battery=50vp+margin(0vp), earphone_battery=50vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 108vp within 100vp; it overflows by 8vp. Occupancy: phone_battery=50vp+margin(0vp), earphone_battery=50vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 108vp within 100vp; it overflows by 8vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: phone_battery=50vp+margin(0vp), earphone_battery=50vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 100.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 108.0,
            "overflow": 8.0,
            "occupancy": "phone_battery=50vp+margin(0vp), earphone_battery=50vp+margin(0vp), gaps=8vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    }
  ]
}
```
```repair-3
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"battery_group\",\"connection\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"出门设备状态\",\"fontSize\":12}]\n[\"battery_group\",\"Group\",{\"variant\":\"peer-pair\"},[\"phone_battery\",\"earphone_battery\"]]\n[\"phone_battery\",\"InfoBlock\",{\"primaryText\":{\"path\":\"/data/phoneBattery/batterySOC\"},\"unit\":\"%\",\"secondaryText\":\"手机剩余电量\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"earphone_battery\",\"InfoBlock\",{\"primaryText\":{\"path\":\"/data/earphone/batteryLevel\"},\"unit\":\"%\",\"secondaryText\":\"耳机仓剩余电量\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"connection\",\"SecondaryBody\",{\"items\":[{\"label\":\"耳机\",\"value\":\"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}\"}],\"fontSize\":14}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/earphone/batteryLevel\",80]\n[\"/data/earphone/isConnected\",true]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 battery_group：小卡 Group 只能包含同一区域内的只读内容。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-4
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"phone_battery\",\"earphone_battery\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"出门设备状态\",\"fontSize\":12}]\n[\"phone_battery\",\"InfoBlock\",{\"primaryText\":{\"path\":\"/data/phoneBattery/batterySOC\"},\"unit\":\"%\",\"secondaryText\":\"手机剩余电量\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"earphone_battery\",\"InfoBlock\",{\"primaryText\":{\"path\":\"/data/earphone/batteryLevel\"},\"unit\":\"%\",\"secondaryText\":\"耳机仓剩余电量\",\"backgroundColor\":\"#CCFFFFFF\"}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/earphone/batteryLevel\",80]\n[\"/data/earphone/isConnected\",true]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：两个 InfoBlock 必须使用 stacked-info 变体。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-5
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"devices\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"出门设备状态\",\"fontSize\":12}]\n[\"devices\",\"TableText\",{\"items\":[{\"label\":\"手机电量\",\"value\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\"},{\"label\":\"耳机仓电量\",\"value\":\"{{ ${/data/earphone/batteryLevel} + '%' }}\"},{\"label\":\"耳机连接\",\"value\":\"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}\"}],\"fontSize\":10}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/earphone/batteryLevel\",80]\n[\"/data/earphone/isConnected\",true]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__content\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":12,\"flexShrink\":0,\"justifyContent\":\"start\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"出门设备状态\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":0,\"width\":\"matchParent\",\"fontColor\":\"#991F4799\"}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"devices\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"end\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"devices\",\"component\":\"Column\",\"children\":[\"devices_row0\",\"devices_row1\",\"devices_row2\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1}},{\"id\":\"devices_row0\",\"component\":\"Row\",\"children\":[\"devices_row0_label\",\"devices_row0_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":16,\"alignItems\":\"top\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"devices_row0_label\",\"component\":\"Text\",\"content\":\"手机电量\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"devices_row0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"devices_row1\",\"component\":\"Row\",\"children\":[\"devices_row1_label\",\"devices_row1_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":16,\"alignItems\":\"top\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"devices_row1_label\",\"component\":\"Text\",\"content\":\"耳机仓电量\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"devices_row1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/batteryLevel} + '%' }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"devices_row2\",\"component\":\"Row\",\"children\":[\"devices_row2_label\",\"devices_row2_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":16,\"alignItems\":\"top\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"devices_row2_label\",\"component\":\"Text\",\"content\":\"耳机连接\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"devices_row2_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"batterySOC\":68},\"earphone\":{\"batteryLevel\":80,\"isConnected\":true}}}}}",
  "validationErrors": []
}
```
