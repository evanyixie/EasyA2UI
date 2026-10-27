```cardspec
{
  "title": "充电诊断",
  "description": "充电参数+识别状态",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"电池检查","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/bolt_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["details"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"details","component":"Column","children":["details_row0","details_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"details_row0","component":"Row","children":["details_row0_label","details_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"details_row0_label","component":"Text","content":"充电电流","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"details_row0_value","component":"Text","content":"{{ ${/data/phoneBattery/nowCurrentText} }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"details_row1","component":"Row","children":["details_row1_label","details_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"details_row1_label","component":"Text","content":"充电电压","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"details_row1_value","component":"Text","content":"{{ ${/data/phoneBattery/voltageText} }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__action","component":"Column","children":["action"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"battery"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/battery_leaf_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"action_text","component":"Text","content":"电池设置","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"nowCurrentText":"-151 mA","voltageText":"4 V"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个电池检查卡片，展示充电电流、充电电压、电量等级和电池是否被系统识别，点击打开电池设置。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.settings.battery",
      "description": "打开系统设置中的电池页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "battery"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "phoneBattery": {
        "nowCurrentText": {
          "type": "string",
          "description": "可直接显示的当前设备电池实时电流文本，已包含“mA”单位；展示时不得再次追加电流单位。",
          "sampleValue": "-151 mA"
        },
        "voltageText": {
          "type": "string",
          "description": "可直接显示的当前设备电池实时电压文本，已包含“V”单位；展示时不得再次追加电压单位。",
          "sampleValue": "4 V"
        },
        "batteryCapacityLevelDesc": {
          "type": "string",
          "description": "设备电池电量等级的语义化文本描述。",
          "sampleValue": "正常电量"
        },
        "isBatteryPresentText": {
          "type": "string",
          "description": "当前设备物理电池是否在位或受支持的状态描述。",
          "sampleValue": "在位"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.bolt_fill",
      "src": "resources/base/media/bolt_fill.svg",
      "description": "样式：默认黑色的单色实心竖向闪电图标；适用：正在充电、快充、电能或闪电状态。"
    },
    {
      "id": "asset.battery_leaf_fill",
      "src": "resources/base/media/battery_leaf_fill.svg",
      "description": "样式：默认黑色的单色实心横向电池图标，电池内部为叶片留白；适用：电池相关场景，包括电量、省电模式、节能电池、绿色用电状态，也可作为电池健康或电池温度信息的辅助图标，相关数据可结合 GetPhoneBatteryInfo 展示。图标本身不表示具体电量、健康等级或温度高低。"
    },
    {
      "id": "asset.phone_fill",
      "src": "resources/base/media/phone_fill.svg",
      "description": "样式：电话实心图标，默认黑色，图形为经典听筒造型；适用：拨打电话、通话功能入口。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetPhoneBatteryInfo"
  ],
  "event": [
    {
      "id": "event.open.settings.battery",
      "description": "打开系统设置中的电池页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "battery"
      }
    }
  ],
  "asset": [
    "asset.bolt_fill",
    "asset.battery_leaf_fill",
    "asset.phone_fill"
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
        "/nowCurrentText",
        "/voltageText",
        "/batteryCapacityLevelDesc",
        "/isBatteryPresentText"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.battery",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "battery"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.bolt_fill",
    "asset.battery_leaf_fill",
    "asset.phone_fill"
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
  "artifactId": "8e7e8aeb-182c-44cb-a3ca-36f24f6ba85c",
  "createdAt": 1792045596387
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","details","action"]]
["header","SingleLineTitle",{"title":"电池检查","icon":"resources/base/media/bolt_fill.svg","fontSize":12}]
["details","TableText",{"items":[{"label":"充电电流","value":{"path":"/data/phoneBattery/nowCurrentText"}},{"label":"充电电压","value":{"path":"/data/phoneBattery/voltageText"}}],"fontSize":12}]
["action","PillButton",{"label":"电池设置","icon":"resources/base/media/battery_leaf_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"battery"}}]}]
["/data/phoneBattery/nowCurrentText","-151 mA"]
["/data/phoneBattery/voltageText","4 V"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个电池检查卡片，展示充电电流、充电电压、电量等级和电池是否被系统识别，点击打开电池设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/nowCurrentText",
          "/voltageText",
          "/batteryCapacityLevelDesc",
          "/isBatteryPresentText"
        ]
      }
    ],
    "title": "充电诊断",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.settings.battery",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Settings",
            "bundleName": "com.huawei.hmos.settings",
            "abilityName": "com.huawei.hmos.settings.MainAbility",
            "uri": "battery"
          }
        }
      }
    ],
    "description": "充电参数+识别状态",
    "candidateAssetIds": [
      "asset.bolt_fill",
      "asset.battery_leaf_fill",
      "asset.phone_fill"
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
    "interactionId": "047",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个电池检查卡片，展示充电电流、充电电压、电量等级和电池是否被系统识别，点击打开电池设置。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个电池检查卡片，展示充电电流、充电电压、电量等级和电池是否被系统识别，点击打开电池设置。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/nowCurrentText",
        "/voltageText",
        "/batteryCapacityLevelDesc",
        "/isBatteryPresentText"
      ]
    }
  ],
  "title": "充电诊断",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.battery",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "battery"
        }
      }
    }
  ],
  "description": "充电参数+识别状态",
  "candidateAssetIds": [
    "asset.bolt_fill",
    "asset.battery_leaf_fill",
    "asset.phone_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"level\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池检查\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"fontSize\":12}]\n[\"level\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"},\"secondaryText\":{\"path\":\"/data/phoneBattery/isBatteryPresentText\"},\"fontSize\":18}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电电流\",\"value\":{\"path\":\"/data/phoneBattery/nowCurrentText\"}},{\"label\":\"充电电压\",\"value\":{\"path\":\"/data/phoneBattery/voltageText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"battery\"}}]}]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/isBatteryPresentText\",\"在位\"]\n[\"/data/phoneBattery/nowCurrentText\",\"-151 mA\"]\n[\"/data/phoneBattery/voltageText\",\"4 V\"]",
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
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"body\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池检查\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"fontSize\":12}]\n[\"body\",\"Group\",{\"variant\":\"hero-support\"},[\"level\",\"details\"]]\n[\"level\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"},\"secondaryText\":{\"path\":\"/data/phoneBattery/isBatteryPresentText\"},\"fontSize\":18}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电电流\",\"value\":{\"path\":\"/data/phoneBattery/nowCurrentText\"}},{\"label\":\"充电电压\",\"value\":{\"path\":\"/data/phoneBattery/voltageText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"battery\"}}]}]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/isBatteryPresentText\",\"在位\"]\n[\"/data/phoneBattery/nowCurrentText\",\"-151 mA\"]\n[\"/data/phoneBattery/voltageText\",\"4 V\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Occupancy: header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp.",
          "legacyMessage": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 148.0,
            "overflow": 22.0,
            "occupancy": "header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp"
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
      "message": "component __layout__root__body: vertical layout requires at least 122vp within 100vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__content=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 122vp within 100vp; it overflows by 22vp. Occupancy: __layout__root__content=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 122vp within 100vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__content=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 100.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 122.0,
            "overflow": 22.0,
            "occupancy": "__layout__root__content=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp"
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
      "message": "component __layout__root__content: vertical layout requires at least 78vp within 56vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: body=78vp+margin(0vp), gaps=0vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__content: vertical layout requires at least 78vp within 56vp; it overflows by 22vp. Occupancy: body=78vp+margin(0vp), gaps=0vp.",
          "legacyMessage": "component __layout__root__content: vertical layout requires at least 78vp within 56vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: body=78vp+margin(0vp), gaps=0vp.",
          "expected": {
            "maximumHeight": 56.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 78.0,
            "overflow": 22.0,
            "occupancy": "body=78vp+margin(0vp), gaps=0vp"
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
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"level\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池检查\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"fontSize\":12}]\n[\"level\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"},\"secondaryText\":{\"path\":\"/data/phoneBattery/isBatteryPresentText\"},\"fontSize\":18}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电电流\",\"value\":{\"path\":\"/data/phoneBattery/nowCurrentText\"}},{\"label\":\"充电电压\",\"value\":{\"path\":\"/data/phoneBattery/voltageText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"battery\"}}]}]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/isBatteryPresentText\",\"在位\"]\n[\"/data/phoneBattery/nowCurrentText\",\"-151 mA\"]\n[\"/data/phoneBattery/voltageText\",\"4 V\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Occupancy: header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp.",
          "legacyMessage": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 148.0,
            "overflow": 22.0,
            "occupancy": "header=20vp+margin(0vp), __layout__root__body=122vp+margin(0vp), gaps=6vp"
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
      "message": "component __layout__root__body: vertical layout requires at least 122vp within 100vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 122vp within 100vp; it overflows by 22vp. Occupancy: __layout__root__primary_support=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 122vp within 100vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 100.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 122.0,
            "overflow": 22.0,
            "occupancy": "__layout__root__primary_support=78vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp"
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
      "message": "component __layout__root__primary_support: vertical layout requires at least 78vp within 56vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: level=42vp+margin(0vp), details=34vp+margin(0vp), gaps=2vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__primary_support: vertical layout requires at least 78vp within 56vp; it overflows by 22vp. Occupancy: level=42vp+margin(0vp), details=34vp+margin(0vp), gaps=2vp.",
          "legacyMessage": "component __layout__root__primary_support: vertical layout requires at least 78vp within 56vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: level=42vp+margin(0vp), details=34vp+margin(0vp), gaps=2vp.",
          "expected": {
            "maximumHeight": 56.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 78.0,
            "overflow": 22.0,
            "occupancy": "level=42vp+margin(0vp), details=34vp+margin(0vp), gaps=2vp"
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
```repair-4
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池检查\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"fontSize\":12}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"充电电流\",\"value\":{\"path\":\"/data/phoneBattery/nowCurrentText\"}},{\"label\":\"充电电压\",\"value\":{\"path\":\"/data/phoneBattery/voltageText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"battery\"}}]}]\n[\"/data/phoneBattery/nowCurrentText\",\"-151 mA\"]\n[\"/data/phoneBattery/voltageText\",\"4 V\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component details: SecondaryBody is auxiliary and cannot be the only information component in the card; pair it with a core information component somewhere in the card. Titles, buttons and other SecondaryBody instances do not count."
    }
  ]
}
```
```repair-5
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池检查\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"fontSize\":12}]\n[\"details\",\"TableText\",{\"items\":[{\"label\":\"充电电流\",\"value\":{\"path\":\"/data/phoneBattery/nowCurrentText\"}},{\"label\":\"充电电压\",\"value\":{\"path\":\"/data/phoneBattery/voltageText\"}}],\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"battery\"}}]}]\n[\"/data/phoneBattery/nowCurrentText\",\"-151 mA\"]\n[\"/data/phoneBattery/voltageText\",\"4 V\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"电池检查\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/bolt_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__content\",\"__layout__root__action\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"details\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"details\",\"component\":\"Column\",\"children\":[\"details_row0\",\"details_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1}},{\"id\":\"details_row0\",\"component\":\"Row\",\"children\":[\"details_row0_label\",\"details_row0_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":18,\"alignItems\":\"bottom\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"details_row0_label\",\"component\":\"Text\",\"content\":\"充电电流\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/nowCurrentText} }}\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row1\",\"component\":\"Row\",\"children\":[\"details_row1_label\",\"details_row1_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":18,\"alignItems\":\"bottom\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"details_row1_label\",\"component\":\"Text\",\"content\":\"充电电压\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/voltageText} }}\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"__layout__root__action\",\"component\":\"Column\",\"children\":[\"action\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"height\":36,\"flexShrink\":0},\"itemMargin\":0},{\"id\":\"action\",\"component\":\"Row\",\"children\":[\"action_icon\",\"action_text\"],\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"battery\"}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#331F4799\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"action_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/battery_leaf_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"action_text\",\"component\":\"Text\",\"content\":\"电池设置\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"nowCurrentText\":\"-151 mA\",\"voltageText\":\"4 V\"}}}}}",
  "validationErrors": []
}
```
