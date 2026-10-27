```cardspec
{
  "title": "耳机排障",
  "description": "耳机连接充电状态+蓝牙设置",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","content_flow","action"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"{{ ${/data/earphone/earphoneName} }}","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_earphone.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"content_flow","component":"Column","children":["connection","charging"],"itemMargin":2,"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"start"}},{"id":"connection","component":"Column","children":["connection_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"connection_main","component":"Text","content":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"charging","component":"Column","children":["charging_row0","charging_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"charging_item0_label","component":"Text","content":"左耳","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"charging_item0_value","component":"Text","content":"{{ ${/data/earphone/leftChargingStatusDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"charging_item0","component":"Row","children":["charging_item0_label","charging_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"charging_row0","component":"Row","children":["charging_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"charging_item1_label","component":"Text","content":"右耳","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"charging_item1_value","component":"Text","content":"{{ ${/data/earphone/rightChargingStatusDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"charging_item1","component":"Row","children":["charging_item1_label","charging_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"charging_row1","component":"Row","children":["charging_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"bluetooth_entry"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/bolt_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"action_text","component":"Text","content":"蓝牙设置","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"earphone":{"earphoneName":"示例耳机","isConnected":true,"leftChargingStatusDesc":"未充电","rightChargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个耳机排障卡片，看耳机名称、连接状态和左右耳机充电状态，点击打开蓝牙设置。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.settings.bluetooth",
      "description": "打开系统设置中的蓝牙设置页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "bluetooth_entry"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "earphone": {
        "isConnected": {
          "type": "boolean",
          "description": "当前是否有蓝牙耳机处于连接活跃状态。",
          "sampleValue": true
        },
        "earphoneName": {
          "type": "string",
          "description": "耳机的设备广播名称，如果未连接则返回'未连接耳机'。如: 'FreeBuds Pro 3'。",
          "sampleValue": "示例耳机"
        },
        "leftChargingStatusDesc": {
          "type": "string",
          "description": "左耳机当前的充电状态中文语义描述，'充电中' 或 '未充电'。",
          "sampleValue": "未充电"
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
      "id": "asset.icon_earphone",
      "src": "resources/base/media/icon_earphone.svg",
      "description": "样式：默认黑色的单色左右分体式开放耳机，局部通过镂空表现高光与分隔，支持通过 fillColor 与卡片配色统一；适用：无线耳机本体、耳机连接、左右耳设备状态。"
    },
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
  "event": [
    {
      "id": "event.open.settings.bluetooth",
      "description": "打开系统设置中的蓝牙设置页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "bluetooth_entry"
      }
    }
  ],
  "asset": [
    "asset.icon_earphone",
    "asset.icon_left",
    "asset.icon_right",
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
        "/isConnected",
        "/earphoneName",
        "/leftChargingStatusDesc",
        "/rightChargingStatusDesc"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.bluetooth",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "bluetooth_entry"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.icon_earphone",
    "asset.icon_left",
    "asset.icon_right",
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
  "artifactId": "89c92b5a-d5df-418e-9957-4d2f3b551e2b",
  "createdAt": 1792045631734
}
```
```designcompactdsl
["root","Column",{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"itemMargin":6,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","content_flow","action"]]
["header","SingleLineTitle",{"title":{"path":"/data/earphone/earphoneName"},"icon":"resources/base/media/icon_earphone.svg","fontSize":12,"width":"matchParent"}]
["content_flow","Column",{"width":"matchParent","layoutWeight":1,"itemMargin":2,"alignItems":"start","justifyContent":"start"},["connection","charging"]]
["connection","EmphasisText",{"mainText":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}","fontSize":18,"width":"matchParent"}]
["charging","SecondaryBody",{"items":[{"label":"左耳","value":{"path":"/data/earphone/leftChargingStatusDesc"}},{"label":"右耳","value":{"path":"/data/earphone/rightChargingStatusDesc"}}],"columns":1,"fontSize":12,"width":"matchParent"}]
["action","PillButton",{"label":"蓝牙设置","icon":"resources/base/media/bolt_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"bluetooth_entry"}}]}]
["/data/earphone/earphoneName","示例耳机"]
["/data/earphone/isConnected",true]
["/data/earphone/leftChargingStatusDesc","未充电"]
["/data/earphone/rightChargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个耳机排障卡片，看耳机名称、连接状态和左右耳机充电状态，点击打开蓝牙设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/isConnected",
          "/earphoneName",
          "/leftChargingStatusDesc",
          "/rightChargingStatusDesc"
        ]
      }
    ],
    "title": "耳机排障",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.settings.bluetooth",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Settings",
            "bundleName": "com.huawei.hmos.settings",
            "abilityName": "com.huawei.hmos.settings.MainAbility",
            "uri": "bluetooth_entry"
          }
        }
      }
    ],
    "description": "耳机连接充电状态+蓝牙设置",
    "candidateAssetIds": [
      "asset.icon_earphone",
      "asset.icon_left",
      "asset.icon_right",
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
  "session": {
    "interactionId": "052",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "utterance": {
    "original": "帮我做个耳机排障卡片，看耳机名称、连接状态和左右耳机充电状态，点击打开蓝牙设置。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个耳机排障卡片，看耳机名称、连接状态和左右耳机充电状态，点击打开蓝牙设置。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/isConnected",
        "/earphoneName",
        "/leftChargingStatusDesc",
        "/rightChargingStatusDesc"
      ]
    }
  ],
  "title": "耳机排障",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.bluetooth",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "bluetooth_entry"
        }
      }
    }
  ],
  "description": "耳机连接充电状态+蓝牙设置",
  "candidateAssetIds": [
    "asset.icon_earphone",
    "asset.icon_left",
    "asset.icon_right",
    "asset.bolt_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"connection\",\"charging\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/earphone/earphoneName\"},\"icon\":\"resources/base/media/icon_earphone.svg\",\"fontSize\":12}]\n[\"connection\",\"EmphasisText\",{\"mainText\":\"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}\",\"fontSize\":18}]\n[\"charging\",\"SecondaryBody\",{\"items\":[{\"label\":\"左耳\",\"value\":{\"path\":\"/data/earphone/leftChargingStatusDesc\"}},{\"label\":\"右耳\",\"value\":{\"path\":\"/data/earphone/rightChargingStatusDesc\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"蓝牙设置\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"bluetooth_entry\"}}]}]\n[\"/data/earphone/earphoneName\",\"示例耳机\"]\n[\"/data/earphone/isConnected\",true]\n[\"/data/earphone/leftChargingStatusDesc\",\"未充电\"]\n[\"/data/earphone/rightChargingStatusDesc\",\"未充电\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：子组件数量应为 [3]；要求的 children 角色为 [title, content, PillButton]。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"body\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/earphone/earphoneName\"},\"icon\":\"resources/base/media/icon_earphone.svg\",\"fontSize\":12}]\n[\"body\",\"Group\",{\"variant\":\"hero-support\"},[\"connection\",\"charging\"]]\n[\"connection\",\"EmphasisText\",{\"mainText\":\"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}\",\"fontSize\":18}]\n[\"charging\",\"SecondaryBody\",{\"items\":[{\"label\":\"左耳\",\"value\":{\"path\":\"/data/earphone/leftChargingStatusDesc\"}},{\"label\":\"右耳\",\"value\":{\"path\":\"/data/earphone/rightChargingStatusDesc\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"蓝牙设置\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"bluetooth_entry\"}}]}]\n[\"/data/earphone/earphoneName\",\"示例耳机\"]\n[\"/data/earphone/isConnected\",true]\n[\"/data/earphone/leftChargingStatusDesc\",\"未充电\"]\n[\"/data/earphone/rightChargingStatusDesc\",\"未充电\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"content_flow\",\"action\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/earphoneName} }}\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/icon_earphone.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"content_flow\",\"component\":\"Column\",\"children\":[\"connection\",\"charging\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"layoutWeight\":1,\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"connection\",\"component\":\"Column\",\"children\":[\"connection_main\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"connection_main\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"charging\",\"component\":\"Column\",\"children\":[\"charging_row0\",\"charging_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"charging_item0_label\",\"component\":\"Text\",\"content\":\"左耳\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"charging_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/leftChargingStatusDesc} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"charging_item0\",\"component\":\"Row\",\"children\":[\"charging_item0_label\",\"charging_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"charging_row0\",\"component\":\"Row\",\"children\":[\"charging_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"charging_item1_label\",\"component\":\"Text\",\"content\":\"右耳\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"charging_item1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/earphone/rightChargingStatusDesc} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"charging_item1\",\"component\":\"Row\",\"children\":[\"charging_item1_label\",\"charging_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"charging_row1\",\"component\":\"Row\",\"children\":[\"charging_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"action\",\"component\":\"Row\",\"children\":[\"action_icon\",\"action_text\"],\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"bluetooth_entry\"}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#331F4799\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"action_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/bolt_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"action_text\",\"component\":\"Text\",\"content\":\"蓝牙设置\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"earphone\":{\"earphoneName\":\"示例耳机\",\"isConnected\":true,\"leftChargingStatusDesc\":\"未充电\",\"rightChargingStatusDesc\":\"未充电\"}}}}}",
  "validationErrors": []
}
```
