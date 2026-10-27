```cardspec
{
  "title": "电池体检",
  "description": "电量+健康+温度",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"电池体检","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/heat_generation.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["details"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"details","component":"Column","children":["details_row0","details_row1","details_row2"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"details_row0","component":"Row","children":["details_row0_label","details_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"details_row0_label","component":"Text","content":"电量等级","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"details_row0_value","component":"Text","content":"{{ ${/data/phoneBattery/batteryCapacityLevelDesc} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"details_row1","component":"Row","children":["details_row1_label","details_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"details_row1_label","component":"Text","content":"健康状态","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"details_row1_value","component":"Text","content":"{{ ${/data/phoneBattery/healthStatusDesc} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"details_row2","component":"Row","children":["details_row2_label","details_row2_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"details_row2_label","component":"Text","content":"实时温度","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"details_row2_value","component":"Text","content":"{{ ${/data/phoneBattery/batteryTemperatureText} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__action","component":"Column","children":["action"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"smart_charge_battery_health"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/battery_leaf_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"action_text","component":"Text","content":"电池健康设置","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"batteryCapacityLevelDesc":"正常电量","healthStatusDesc":"正常","batteryTemperatureText":"29.0 ℃"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个电池体检卡片，手机剩余电量、电量等级、电池健康状态、实时温度，点击查看电池健康设置。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.settings.batteryHealth",
      "description": "打开系统设置中的电池健康页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "smart_charge_battery_health"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "phoneBattery": {
        "batterySOCText": {
          "type": "string",
          "description": "可直接显示的当前手机设备剩余电量文本，已包含“%”单位；展示时不得再次追加“%”。",
          "sampleValue": "68%"
        },
        "batteryCapacityLevelDesc": {
          "type": "string",
          "description": "设备电池电量等级的语义化文本描述。",
          "sampleValue": "正常电量"
        },
        "healthStatusDesc": {
          "type": "string",
          "description": "当前设备电池的物理健康状态文本描述。",
          "sampleValue": "正常"
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
      "id": "asset.battery_leaf_fill",
      "src": "resources/base/media/battery_leaf_fill.svg",
      "description": "样式：默认黑色的单色实心横向电池图标，电池内部为叶片留白；适用：电池相关场景，包括电量、省电模式、节能电池、绿色用电状态，也可作为电池健康或电池温度信息的辅助图标，相关数据可结合 GetPhoneBatteryInfo 展示。图标本身不表示具体电量、健康等级或温度高低。"
    },
    {
      "id": "asset.heat_generation",
      "src": "resources/base/media/heat_generation.svg",
      "description": "样式：默认黑色的单色线框温度计，底部为圆形感温泡，内部带弧形刻度；适用：温度、升温、制热或体感温度。"
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
  "event": [
    {
      "id": "event.open.settings.batteryHealth",
      "description": "打开系统设置中的电池健康页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "smart_charge_battery_health"
      }
    }
  ],
  "asset": [
    "asset.battery_leaf_fill",
    "asset.heat_generation",
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
        "/batterySOCText",
        "/batteryCapacityLevelDesc",
        "/healthStatusDesc",
        "/batteryTemperatureText"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.batteryHealth",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "smart_charge_battery_health"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.heat_generation",
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
  "artifactId": "b10a7057-13b3-4031-b9c2-d671da79f4fb",
  "createdAt": 1792045615144
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","details","action"]]
["header","SingleLineTitle",{"title":"电池体检","icon":"resources/base/media/heat_generation.svg","fontSize":12}]
["details","TableText",{"items":[{"label":"电量等级","value":{"path":"/data/phoneBattery/batteryCapacityLevelDesc"}},{"label":"健康状态","value":{"path":"/data/phoneBattery/healthStatusDesc"}},{"label":"实时温度","value":{"path":"/data/phoneBattery/batteryTemperatureText"}}],"fontSize":10}]
["action","PillButton",{"label":"电池健康设置","icon":"resources/base/media/battery_leaf_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"smart_charge_battery_health"}}]}]
["/data/phoneBattery/batteryCapacityLevelDesc","正常电量"]
["/data/phoneBattery/healthStatusDesc","正常"]
["/data/phoneBattery/batteryTemperatureText","29.0 ℃"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个电池体检卡片，手机剩余电量、电量等级、电池健康状态、实时温度，点击查看电池健康设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/batterySOCText",
          "/batteryCapacityLevelDesc",
          "/healthStatusDesc",
          "/batteryTemperatureText"
        ]
      }
    ],
    "title": "电池体检",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.settings.batteryHealth",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Settings",
            "bundleName": "com.huawei.hmos.settings",
            "abilityName": "com.huawei.hmos.settings.MainAbility",
            "uri": "smart_charge_battery_health"
          }
        }
      }
    ],
    "description": "电量+健康+温度",
    "candidateAssetIds": [
      "asset.battery_leaf_fill",
      "asset.heat_generation",
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
    "time": "20260821000000000"
  },
  "session": {
    "interactionId": "049",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "utterance": {
    "original": "帮我做个电池体检卡片，看手机剩余电量、电量等级、电池健康状态、实时温度，点击查看电池健康设置。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个电池体检卡片，看手机剩余电量、电量等级、电池健康状态、实时温度，点击查看电池健康设置。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOCText",
        "/batteryCapacityLevelDesc",
        "/healthStatusDesc",
        "/batteryTemperatureText"
      ]
    }
  ],
  "title": "电池体检",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.batteryHealth",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "smart_charge_battery_health"
        }
      }
    }
  ],
  "description": "电量+健康+温度",
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.heat_generation",
    "asset.clock"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"soc\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池体检\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"soc\",\"EmphasizedData\",{\"value\":{\"path\":\"/data/phoneBattery/batterySOCText\"},\"fontSize\":30}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"电量等级\",\"value\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"}},{\"label\":\"健康状态\",\"value\":{\"path\":\"/data/phoneBattery/healthStatusDesc\"}},{\"label\":\"实时温度\",\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池健康设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"smart_charge_battery_health\"}}]}]\n[\"/data/phoneBattery/batterySOCText\",\"68%\"]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/healthStatusDesc\",\"正常\"]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 154vp within 126vp; it overflows by 28vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=128vp+margin(0vp), gaps=6vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 154vp within 126vp; it overflows by 28vp. Occupancy: header=20vp+margin(0vp), __layout__root__body=128vp+margin(0vp), gaps=6vp.",
          "legacyMessage": "component root: vertical layout requires at least 154vp within 126vp; it overflows by 28vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=128vp+margin(0vp), gaps=6vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 154.0,
            "overflow": 28.0,
            "occupancy": "header=20vp+margin(0vp), __layout__root__body=128vp+margin(0vp), gaps=6vp"
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
      "message": "component __layout__root__body: vertical layout requires at least 128vp within 100vp; it overflows by 28vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=84vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 128vp within 100vp; it overflows by 28vp. Occupancy: __layout__root__primary_support=84vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 128vp within 100vp; it overflows by 28vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=84vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 100.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 128.0,
            "overflow": 28.0,
            "occupancy": "__layout__root__primary_support=84vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp"
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
      "message": "component __layout__root__primary_support: vertical layout requires at least 84vp within 56vp; it overflows by 28vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__primary_support: vertical layout requires at least 84vp within 56vp; it overflows by 28vp. Occupancy: soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp.",
          "legacyMessage": "component __layout__root__primary_support: vertical layout requires at least 84vp within 56vp; it overflows by 28vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp.",
          "expected": {
            "maximumHeight": 56.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 84.0,
            "overflow": 28.0,
            "occupancy": "soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp"
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
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"variant\":\"direct-dense\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"soc\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池体检\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"soc\",\"EmphasizedData\",{\"value\":{\"path\":\"/data/phoneBattery/batterySOCText\"},\"fontSize\":30}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"电量等级\",\"value\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"}},{\"label\":\"健康状态\",\"value\":{\"path\":\"/data/phoneBattery/healthStatusDesc\"}},{\"label\":\"实时温度\",\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池健康设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"smart_charge_battery_health\"}}]}]\n[\"/data/phoneBattery/batterySOCText\",\"68%\"]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/healthStatusDesc\",\"正常\"]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]",
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
```repair-3
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"variant\":\"direct-dense\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"content\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池体检\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"content\",\"Group\",{\"variant\":\"hero-support\"},[\"soc\",\"details\"]]\n[\"soc\",\"EmphasizedData\",{\"value\":{\"path\":\"/data/phoneBattery/batterySOCText\"},\"fontSize\":30}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"电量等级\",\"value\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"}},{\"label\":\"健康状态\",\"value\":{\"path\":\"/data/phoneBattery/healthStatusDesc\"}},{\"label\":\"实时温度\",\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池健康设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"smart_charge_battery_health\"}}]}]\n[\"/data/phoneBattery/batterySOCText\",\"68%\"]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/healthStatusDesc\",\"正常\"]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), content=84vp+margin(0vp), action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Occupancy: header=20vp+margin(0vp), content=84vp+margin(0vp), action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component root: vertical layout requires at least 148vp within 126vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), content=84vp+margin(0vp), action=36vp+margin(0vp), gaps=8vp.",
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
            "occupancy": "header=20vp+margin(0vp), content=84vp+margin(0vp), action=36vp+margin(0vp), gaps=8vp"
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
      "message": "component content: vertical layout requires at least 84vp within 62vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component content: vertical layout requires at least 84vp within 62vp; it overflows by 22vp. Occupancy: soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp.",
          "legacyMessage": "component content: vertical layout requires at least 84vp within 62vp; it overflows by 22vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp.",
          "expected": {
            "maximumHeight": 62.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 84.0,
            "overflow": 22.0,
            "occupancy": "soc=30vp+margin(0vp), details=52vp+margin(0vp), gaps=2vp"
          },
          "evidenceSource": "expanded",
          "componentId": "content",
          "sourceLine": 3,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    }
  ]
}
```
```repair-4
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池体检\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"电量等级\",\"value\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"}},{\"label\":\"健康状态\",\"value\":{\"path\":\"/data/phoneBattery/healthStatusDesc\"}},{\"label\":\"实时温度\",\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"}}],\"columns\":1,\"fontSize\":12}]\n[\"action\",\"PillButton\",{\"label\":\"电池健康设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"smart_charge_battery_health\"}}]}]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/healthStatusDesc\",\"正常\"]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]",
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
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"details\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"电池体检\",\"icon\":\"resources/base/media/heat_generation.svg\",\"fontSize\":12}]\n[\"details\",\"TableText\",{\"items\":[{\"label\":\"电量等级\",\"value\":{\"path\":\"/data/phoneBattery/batteryCapacityLevelDesc\"}},{\"label\":\"健康状态\",\"value\":{\"path\":\"/data/phoneBattery/healthStatusDesc\"}},{\"label\":\"实时温度\",\"value\":{\"path\":\"/data/phoneBattery/batteryTemperatureText\"}}],\"fontSize\":10}]\n[\"action\",\"PillButton\",{\"label\":\"电池健康设置\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"smart_charge_battery_health\"}}]}]\n[\"/data/phoneBattery/batteryCapacityLevelDesc\",\"正常电量\"]\n[\"/data/phoneBattery/healthStatusDesc\",\"正常\"]\n[\"/data/phoneBattery/batteryTemperatureText\",\"29.0 ℃\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"电池体检\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/heat_generation.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__content\",\"__layout__root__action\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"details\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"details\",\"component\":\"Column\",\"children\":[\"details_row0\",\"details_row1\",\"details_row2\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1}},{\"id\":\"details_row0\",\"component\":\"Row\",\"children\":[\"details_row0_label\",\"details_row0_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":16,\"alignItems\":\"top\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"details_row0_label\",\"component\":\"Text\",\"content\":\"电量等级\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batteryCapacityLevelDesc} }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row1\",\"component\":\"Row\",\"children\":[\"details_row1_label\",\"details_row1_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":16,\"alignItems\":\"top\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"details_row1_label\",\"component\":\"Text\",\"content\":\"健康状态\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/healthStatusDesc} }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row2\",\"component\":\"Row\",\"children\":[\"details_row2_label\",\"details_row2_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":16,\"alignItems\":\"top\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"details_row2_label\",\"component\":\"Text\",\"content\":\"实时温度\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"details_row2_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batteryTemperatureText} }}\",\"styles\":{\"height\":16,\"fontSize\":10,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"__layout__root__action\",\"component\":\"Column\",\"children\":[\"action\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"height\":36,\"flexShrink\":0},\"itemMargin\":0},{\"id\":\"action\",\"component\":\"Row\",\"children\":[\"action_icon\",\"action_text\"],\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"smart_charge_battery_health\"}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#331F4799\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"action_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/battery_leaf_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"action_text\",\"component\":\"Text\",\"content\":\"电池健康设置\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"batteryCapacityLevelDesc\":\"正常电量\",\"healthStatusDesc\":\"正常\",\"batteryTemperatureText\":\"29.0 ℃\"}}}}}",
  "validationErrors": []
}
```
