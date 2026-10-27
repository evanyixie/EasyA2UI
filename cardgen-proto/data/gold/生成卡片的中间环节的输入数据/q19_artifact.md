```cardspec
{
  "title": "耳机仓状态",
  "description": "仓电量和蓝牙",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"耳机仓","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/earphone_case_16644.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["battery"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"battery","component":"Row","children":["battery_ring_stack","battery_labels"],"itemMargin":8,"styles":{"width":"matchParent","height":52,"alignItems":"center","justifyContent":"center","flexShrink":0}},{"id":"battery_ring_stack","component":"Stack","children":["battery_ring","battery_icon"],"styles":{"width":52,"height":52,"alignContent":"center","flexShrink":0}},{"id":"battery_ring","component":"Progress","value":"{{ ${/data/earphone/batteryLevel} }}","total":100,"styles":{"width":52,"height":52,"strokeWidth":6,"flexShrink":0,"type":"ring","color":"#FF1F4799","backgroundColor":"#331F4799"}},{"id":"battery_icon","component":"Image","src":"resources/base/media/earphone_case_16644.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#991F4799"}},{"id":"battery_labels","component":"Column","children":["battery_label","battery_display","battery_secondary"],"itemMargin":0,"styles":{"height":52,"alignItems":"start","justifyContent":"center","flexShrink":1,"layoutWeight":1}},{"id":"battery_label","component":"Text","content":"剩余电量","styles":{"width":"matchParent","height":18,"fontSize":14,"fontWeight":700,"maxLines":1,"textOverflow":"clip","fontColor":"#FF1F4799"}},{"id":"battery_display","component":"Text","content":"{{ ${/data/earphone/batteryLevel} + '%' }}","styles":{"width":"matchParent","height":16,"fontSize":10,"fontWeight":400,"maxLines":1,"textOverflow":"clip","fontColor":"#991F4799"}},{"id":"battery_secondary","component":"Text","content":"{{ ${/data/earphone/chargingStatusDesc} }}","styles":{"width":"matchParent","height":16,"fontSize":10,"fontWeight":400,"maxLines":1,"textOverflow":"clip","fontColor":"#991F4799"}},{"id":"__layout__root__action","component":"Column","children":["action"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"action","component":"Button","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"bluetooth_entry"}}],"label":"蓝牙设置","styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","fontColor":"#FF1F4799","fontSize":14,"fontWeight":500,"textAlign":"center"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"earphone":{"batteryLevel":80,"chargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "出门前检查耳机仓，帮我做个卡片，看耳机仓电量和充电状态，点一下打开蓝牙设置。",
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
        "batteryLevel": {
          "type": "integer",
          "description": "耳机盒（或整体）当前剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”。若直接用于文本展示，必须在数值后追加“%”。",
          "sampleValue": 80
        },
        "chargingStatusDesc": {
          "type": "string",
          "description": "耳机盒（或整体）当前的充电状态中文语义描述，'充电中' 或 '未充电'。",
          "sampleValue": "未充电"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.earphone_case_16644",
      "src": "resources/base/media/earphone_case_16644.svg",
      "description": "样式：耳机收纳盒实心图标，默认黑色，图形为无线耳机充电盒造型；适用：蓝牙耳机设备连接、音频设备管理。"
    },
    {
      "id": "asset.bolt_fill",
      "src": "resources/base/media/bolt_fill.svg",
      "description": "样式：默认黑色的单色实心竖向闪电图标；适用：正在充电、快充、电能或闪电状态。"
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
    "asset.earphone_case_16644",
    "asset.bolt_fill",
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
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/batteryLevel",
        "/chargingStatusDesc"
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
    "asset.earphone_case_16644",
    "asset.bolt_fill",
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
  "artifactId": "cb663f26-381b-4f3c-acf0-1bc7b742c0b1",
  "createdAt": 1792045427282
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","battery","action"]]
["header","SingleLineTitle",{"title":"耳机仓","icon":"resources/base/media/earphone_case_16644.svg","fontSize":12}]
["battery","ProgressCircleSingle",{"value":{"path":"/data/earphone/batteryLevel"},"total":100,"icon":"resources/base/media/earphone_case_16644.svg","displayValue":"{{ ${/data/earphone/batteryLevel} + '%' }}","label":"剩余电量","secondaryLabel":{"path":"/data/earphone/chargingStatusDesc"},"color":"#FF1F4799","backgroundColor":"#331F4799"}]
["action","PillButton",{"label":"蓝牙设置","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"bluetooth_entry"}}]}]
["/data/earphone/batteryLevel",80]
["/data/earphone/chargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "出门前检查耳机仓，帮我做个卡片，看耳机仓电量和充电状态，点一下打开蓝牙设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/batteryLevel",
          "/chargingStatusDesc"
        ]
      }
    ],
    "title": "耳机仓状态",
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
    "description": "仓电量和蓝牙",
    "candidateAssetIds": [
      "asset.earphone_case_16644",
      "asset.bolt_fill",
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
    "interactionId": "019",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "出门前检查耳机仓，帮我做个卡片，看耳机仓电量和充电状态，点一下打开蓝牙设置。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "出门前检查耳机仓，帮我做个卡片，看耳机仓电量和充电状态，点一下打开蓝牙设置。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/batteryLevel",
        "/chargingStatusDesc"
      ]
    }
  ],
  "title": "耳机仓状态",
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
  "description": "仓电量和蓝牙",
  "candidateAssetIds": [
    "asset.earphone_case_16644",
    "asset.bolt_fill",
    "asset.icon_earphone"
  ]
}
```
