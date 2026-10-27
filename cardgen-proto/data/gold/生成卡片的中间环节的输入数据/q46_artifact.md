```cardspec
{
  "title": "睡前准备",
  "description": "耳机盒电量+歌单+闹钟",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["__layout__root__content","cta_music","cta_alarm"],"itemMargin":8,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"__layout__root__content","component":"Column","children":["battery_summary"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1,"flexShrink":0},"itemMargin":0},{"id":"battery_summary","component":"Column","children":["battery_summary_row0","battery_summary_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"battery_summary_row0","component":"Row","children":["battery_summary_row0_label","battery_summary_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"battery_summary_row0_label","component":"Text","content":"耳机盒","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"battery_summary_row0_value","component":"Text","content":"{{ ${/data/earphone/batteryLevel} + '%' }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"battery_summary_row1","component":"Row","children":["battery_summary_row1_label","battery_summary_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"battery_summary_row1_label","component":"Text","content":"状态","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"battery_summary_row1_value","component":"Text","content":"{{ ${/data/earphone/chargingStatusDesc} }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"cta_music","component":"Row","children":["cta_music_icon","cta_music_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"cta_music_icon","component":"Image","src":"resources/base/media/music_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"cta_music_text","component":"Text","content":"每日歌单","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"cta_alarm","component":"Row","children":["cta_alarm_icon","cta_alarm_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"cta_alarm_icon","component":"Image","src":"resources/base/media/alarm_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"cta_alarm_text","component":"Text","content":"闹钟","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"earphone":{"batteryLevel":80,"chargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，可以看耳机盒是否在充电、电量有多少，卡片可以点击跳转歌单和闹钟。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.music.daily",
      "description": "打开音乐app的每日30首歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"
      }
    },
    {
      "id": "event.open.clock.alarm",
      "description": "打开闹钟应用首页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Clock",
        "bundleName": "com.huawei.hmos.clock",
        "abilityName": "com.huawei.hmos.clock.phone",
        "uri": ""
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "earphone": {
        "chargingStatusDesc": {
          "type": "string",
          "description": "耳机盒（或整体）当前的充电状态中文语义描述，'充电中' 或 '未充电'。",
          "sampleValue": "未充电"
        },
        "batteryLevel": {
          "type": "integer",
          "description": "耳机盒（或整体）当前剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”。若直接用于文本展示，必须在数值后追加“%”。",
          "sampleValue": 80
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
      "id": "asset.music_fill",
      "src": "resources/base/media/music_fill.svg",
      "description": "样式：音乐音符实心图标，默认黑色，图形为双音符连接造型；适用：音乐播放卡片、音频功能入口、歌单展示。"
    },
    {
      "id": "asset.alarm_fill_1",
      "src": "resources/base/media/alarm_fill_1.svg",
      "description": "样式：默认黑色的单色闹钟实心图标，内部通过镂空表现表盘指针，支持通过 fillColor 与卡片配色统一；适用：闹钟设置、定时提醒、日程提醒。"
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
      "id": "event.open.music.daily",
      "description": "打开音乐app的每日30首歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"
      }
    },
    {
      "id": "event.open.clock.alarm",
      "description": "打开闹钟应用首页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Clock",
        "bundleName": "com.huawei.hmos.clock",
        "abilityName": "com.huawei.hmos.clock.phone",
        "uri": ""
      }
    }
  ],
  "asset": [
    "asset.earphone_case_16644",
    "asset.bolt_fill",
    "asset.music_fill",
    "asset.alarm_fill_1"
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
        "/chargingStatusDesc",
        "/batteryLevel"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.music.daily",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Music",
          "bundleName": "",
          "abilityName": "",
          "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"
        }
      }
    },
    {
      "capabilityId": "event.open.clock.alarm",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Clock",
          "bundleName": "com.huawei.hmos.clock",
          "abilityName": "com.huawei.hmos.clock.phone",
          "uri": ""
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.earphone_case_16644",
    "asset.bolt_fill",
    "asset.music_fill",
    "asset.alarm_fill_1"
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
  "artifactId": "88cc824b-aa98-450f-8bd6-4a7a5cbf4bd3",
  "createdAt": 1792045581952
}
```
```designcompactdsl
["root","Layout",{"layout":"S-content-dual-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["battery_summary","cta_music","cta_alarm"]]
["battery_summary","TableText",{"items":[{"label":"耳机盒","value":"{{ ${/data/earphone/batteryLevel} + '%' }}"},{"label":"状态","value":{"path":"/data/earphone/chargingStatusDesc"}}],"fontSize":12}]
["cta_music","PillButton",{"label":"每日歌单","icon":"resources/base/media/music_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"}}]}]
["cta_alarm","PillButton",{"label":"闹钟","icon":"resources/base/media/alarm_fill_1.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}]}]
["/data/earphone/batteryLevel",80]
["/data/earphone/chargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，可以看耳机盒是否在充电、电量有多少，卡片可以点击跳转歌单和闹钟。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/chargingStatusDesc",
          "/batteryLevel"
        ]
      }
    ],
    "title": "睡前准备",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.music.daily",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Music",
            "bundleName": "",
            "abilityName": "",
            "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"
          }
        }
      },
      {
        "capabilityId": "event.open.clock.alarm",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Clock",
            "bundleName": "com.huawei.hmos.clock",
            "abilityName": "com.huawei.hmos.clock.phone",
            "uri": ""
          }
        }
      }
    ],
    "description": "耳机盒电量+歌单+闹钟",
    "candidateAssetIds": [
      "asset.earphone_case_16644",
      "asset.bolt_fill",
      "asset.music_fill",
      "asset.alarm_fill_1"
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
    "interactionId": "046",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，可以看耳机盒是否在充电、电量有多少，卡片可以点击跳转歌单和闹钟。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，可以看耳机盒是否在充电、电量有多少，卡片可以点击跳转歌单和闹钟。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/chargingStatusDesc",
        "/batteryLevel"
      ]
    }
  ],
  "title": "睡前准备",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.music.daily",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Music",
          "bundleName": "",
          "abilityName": "",
          "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"
        }
      }
    },
    {
      "capabilityId": "event.open.clock.alarm",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Clock",
          "bundleName": "com.huawei.hmos.clock",
          "abilityName": "com.huawei.hmos.clock.phone",
          "uri": ""
        }
      }
    }
  ],
  "description": "耳机盒电量+歌单+闹钟",
  "candidateAssetIds": [
    "asset.earphone_case_16644",
    "asset.bolt_fill",
    "asset.music_fill",
    "asset.alarm_fill_1"
  ]
}
```
