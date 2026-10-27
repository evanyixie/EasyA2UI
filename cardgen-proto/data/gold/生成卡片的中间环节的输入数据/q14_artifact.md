```cardspec
{
  "title": "设备充电",
  "description": "手机和耳机充电",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","content_flow","action"],"itemMargin":4,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"充电状态","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/earphone_case_16644.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"content_flow","component":"Column","children":["status","detail"],"itemMargin":2,"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"start"}},{"id":"status","component":"Column","children":["status_main","status_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"status_main","component":"Text","content":"{{ ${/data/phoneBattery/chargingStatusDesc} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"status_secondary","component":"Text","content":"{{ ${/data/phoneBattery/pluggedTypeDesc} }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#991F4799","textOverflow":"clip"}},{"id":"detail","component":"Column","children":["detail_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"detail_item0_label","component":"Text","content":"耳机仓 ","styles":{"height":19,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3571428571428572,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"detail_item0_value","component":"Text","content":"{{ ${/data/earphone/chargingStatusDesc} }}","styles":{"height":19.0,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3571428571428572,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"detail_item0","component":"Row","children":["detail_item0_label","detail_item0_value"],"itemMargin":0,"styles":{"height":19.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"detail_row0","component":"Row","children":["detail_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":19.0,"alignItems":"top","flexShrink":0}},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"battery"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/bolt_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"action_text","component":"Text","content":"电池设置","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"chargingStatusDesc":"未充电","pluggedTypeDesc":"未连接充电器"},"earphone":{"chargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个充电状态卡片，看手机是否在充电、使用的充电器类型和耳机仓是否在充电，点一下打开电池设置。",
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
        "chargingStatusDesc": {
          "type": "string",
          "description": "当前设备电池的充电状态文本描述。",
          "sampleValue": "未充电"
        },
        "pluggedTypeDesc": {
          "type": "string",
          "description": "当前设备连接的充电器类型文本描述。",
          "sampleValue": "未连接充电器"
        }
      },
      "earphone": {
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
      "id": "asset.bolt_fill",
      "src": "resources/base/media/bolt_fill.svg",
      "description": "样式：默认黑色的单色实心竖向闪电图标；适用：正在充电、快充、电能或闪电状态。"
    },
    {
      "id": "asset.phone_fill",
      "src": "resources/base/media/phone_fill.svg",
      "description": "样式：电话实心图标，默认黑色，图形为经典听筒造型；适用：拨打电话、通话功能入口。"
    },
    {
      "id": "asset.earphone_case_16644",
      "src": "resources/base/media/earphone_case_16644.svg",
      "description": "样式：耳机收纳盒实心图标，默认黑色，图形为无线耳机充电盒造型；适用：蓝牙耳机设备连接、音频设备管理。"
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
    "asset.phone_fill",
    "asset.earphone_case_16644"
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
        "/chargingStatusDesc",
        "/pluggedTypeDesc"
      ]
    },
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/chargingStatusDesc"
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
    "asset.phone_fill",
    "asset.earphone_case_16644"
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
  "artifactId": "cf8661ef-2f39-4848-920b-0468885789a9",
  "createdAt": 1792045405638
}
```
```designcompactdsl
["root","Column",{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"itemMargin":4,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","content_flow","action"]]
["header","SingleLineTitle",{"title":"充电状态","icon":"resources/base/media/earphone_case_16644.svg","fontSize":12,"width":"matchParent"}]
["content_flow","Column",{"width":"matchParent","layoutWeight":1,"itemMargin":2,"alignItems":"start","justifyContent":"start"},["status","detail"]]
["status","EmphasisText",{"mainText":{"path":"/data/phoneBattery/chargingStatusDesc"},"secondaryText":{"path":"/data/phoneBattery/pluggedTypeDesc"},"fontSize":18,"width":"matchParent"}]
["detail","SecondaryBody",{"items":[{"label":"耳机仓 ","value":{"path":"/data/earphone/chargingStatusDesc"}}],"fontSize":14,"width":"matchParent"}]
["action","PillButton",{"label":"电池设置","icon":"resources/base/media/bolt_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"battery"}}]}]
["/data/phoneBattery/chargingStatusDesc","未充电"]
["/data/phoneBattery/pluggedTypeDesc","未连接充电器"]
["/data/earphone/chargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个充电状态卡片，看手机是否在充电、使用的充电器类型和耳机仓是否在充电，点一下打开电池设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/chargingStatusDesc",
          "/pluggedTypeDesc"
        ]
      },
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/chargingStatusDesc"
        ]
      }
    ],
    "title": "设备充电",
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
    "description": "手机和耳机充电",
    "candidateAssetIds": [
      "asset.bolt_fill",
      "asset.phone_fill",
      "asset.earphone_case_16644"
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
    "interactionId": "014",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个充电状态卡片，看手机是否在充电、使用的充电器类型和耳机仓是否在充电，点一下打开电池设置。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个充电状态卡片，看手机是否在充电、使用的充电器类型和耳机仓是否在充电，点一下打开电池设置。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/chargingStatusDesc",
        "/pluggedTypeDesc"
      ]
    },
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/chargingStatusDesc"
      ]
    }
  ],
  "title": "设备充电",
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
  "description": "手机和耳机充电",
  "candidateAssetIds": [
    "asset.bolt_fill",
    "asset.phone_fill",
    "asset.earphone_case_16644"
  ]
}
```
