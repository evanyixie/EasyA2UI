```cardspec
{
  "title": "音乐专注",
  "description": "耳机名称+耳机盒电量+歌单+免打扰",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["__layout__root__content","cta_music","cta_dnd"],"itemMargin":8,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"__layout__root__content","component":"Column","children":["earphone_summary"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1,"flexShrink":0},"itemMargin":0},{"id":"earphone_summary","component":"Column","children":["earphone_summary_row0","earphone_summary_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"earphone_summary_row0","component":"Row","children":["earphone_summary_row0_label","earphone_summary_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"earphone_summary_row0_label","component":"Text","content":"耳机","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"earphone_summary_row0_value","component":"Text","content":"{{ ${/data/earphone/earphoneName} }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"earphone_summary_row1","component":"Row","children":["earphone_summary_row1_label","earphone_summary_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"earphone_summary_row1_label","component":"Text","content":"充电仓","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"earphone_summary_row1_value","component":"Text","content":"{{ ${/data/earphone/batteryLevel} + '%' }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"cta_music","component":"Row","children":["cta_music_icon","cta_music_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"cta_music_icon","component":"Image","src":"resources/base/media/music_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"cta_music_text","component":"Text","content":"每日歌单","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"cta_dnd","component":"Row","children":["cta_dnd_icon","cta_dnd_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"intelligent_scene_entry"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"cta_dnd_icon","component":"Image","src":"resources/base/media/bell_slash_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"cta_dnd_text","component":"Text","content":"免打扰设置","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"earphone":{"earphoneName":"示例耳机","batteryLevel":80}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，展示耳机名称、充电仓还有多少电，可以打开歌单，也能去设置免打扰。",
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
      "id": "event.open.settings.dnd",
      "description": "打开系统设置中的情景模式，用户可以打开免打扰或专注模式",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "intelligent_scene_entry"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "earphone": {
        "earphoneName": {
          "type": "string",
          "description": "耳机的设备广播名称，如果未连接则返回'未连接耳机'。如: 'FreeBuds Pro 3'。",
          "sampleValue": "示例耳机"
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
      "id": "asset.icon_earphone",
      "src": "resources/base/media/icon_earphone.svg",
      "description": "样式：默认黑色的单色左右分体式开放耳机，局部通过镂空表现高光与分隔，支持通过 fillColor 与卡片配色统一；适用：无线耳机本体、耳机连接、左右耳设备状态。"
    },
    {
      "id": "asset.earphone_case_16644",
      "src": "resources/base/media/earphone_case_16644.svg",
      "description": "样式：耳机收纳盒实心图标，默认黑色，图形为无线耳机充电盒造型；适用：蓝牙耳机设备连接、音频设备管理。"
    },
    {
      "id": "asset.music_fill",
      "src": "resources/base/media/music_fill.svg",
      "description": "样式：音乐音符实心图标，默认黑色，图形为双音符连接造型；适用：音乐播放卡片、音频功能入口、歌单展示。"
    },
    {
      "id": "asset.bell_slash_fill",
      "src": "resources/base/media/bell_slash_fill.svg",
      "description": "样式：默认黑色的单色铃铛加斜杠实心图标，内部通过镂空表现细节，支持通过 fillColor 与卡片配色统一；适用：静音模式、关闭通知、勿扰设置。"
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
      "id": "event.open.settings.dnd",
      "description": "打开系统设置中的情景模式，用户可以打开免打扰或专注模式",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "intelligent_scene_entry"
      }
    }
  ],
  "asset": [
    "asset.icon_earphone",
    "asset.earphone_case_16644",
    "asset.music_fill",
    "asset.bell_slash_fill"
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
        "/earphoneName",
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
      "capabilityId": "event.open.settings.dnd",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "intelligent_scene_entry"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.icon_earphone",
    "asset.earphone_case_16644",
    "asset.music_fill",
    "asset.bell_slash_fill"
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
  "artifactId": "2f76dc0f-248e-4fa6-8a2f-1155800d0fbb",
  "createdAt": 1792045600797
}
```
```designcompactdsl
["root","Layout",{"layout":"S-content-dual-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["earphone_summary","cta_music","cta_dnd"]]
["earphone_summary","TableText",{"items":[{"label":"耳机","value":{"path":"/data/earphone/earphoneName"}},{"label":"充电仓","value":"{{ ${/data/earphone/batteryLevel} + '%' }}"}],"fontSize":12}]
["cta_music","PillButton",{"label":"每日歌单","icon":"resources/base/media/music_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"}}]}]
["cta_dnd","PillButton",{"label":"免打扰设置","icon":"resources/base/media/bell_slash_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"intelligent_scene_entry"}}]}]
["/data/earphone/earphoneName","示例耳机"]
["/data/earphone/batteryLevel",80]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，展示耳机名称、充电仓还有多少电，可以打开歌单，也能去设置免打扰。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/earphoneName",
          "/batteryLevel"
        ]
      }
    ],
    "title": "音乐专注",
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
        "capabilityId": "event.open.settings.dnd",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Settings",
            "bundleName": "com.huawei.hmos.settings",
            "abilityName": "com.huawei.hmos.settings.MainAbility",
            "uri": "intelligent_scene_entry"
          }
        }
      }
    ],
    "description": "耳机名称+耳机盒电量+歌单+免打扰",
    "candidateAssetIds": [
      "asset.icon_earphone",
      "asset.earphone_case_16644",
      "asset.music_fill",
      "asset.bell_slash_fill"
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
    "interactionId": "048",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，展示耳机名称、充电仓还有多少电，可以打开歌单，也能去设置免打扰。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，展示耳机名称、充电仓还有多少电，可以打开歌单，也能去设置免打扰。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/earphoneName",
        "/batteryLevel"
      ]
    }
  ],
  "title": "音乐专注",
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
      "capabilityId": "event.open.settings.dnd",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "intelligent_scene_entry"
        }
      }
    }
  ],
  "description": "耳机名称+耳机盒电量+歌单+免打扰",
  "candidateAssetIds": [
    "asset.icon_earphone",
    "asset.earphone_case_16644",
    "asset.music_fill",
    "asset.bell_slash_fill"
  ]
}
```
