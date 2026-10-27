```cardspec
{
  "title": "训练音乐",
  "description": "训练记录和歌单",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"{{ ${/data/healthSport/targetDateText} }}","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/figure_run.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["exercise"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"exercise","component":"Column","children":["exercise_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"exercise_main","component":"Text","content":"{{ ${/data/healthSport/exerciseTypeName} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["heart_rate","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"heart_rate","component":"Column","children":["heart_rate_row0"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"heart_rate_item0_value","component":"Text","content":"{{ '最低心率 ' + (${/data/healthSport/exerciseHeartRateMin} + '次/分钟') }}","styles":{"height":32.0,"fontSize":12,"fontWeight":400,"maxLines":2,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"heart_rate_item0","component":"Row","children":["heart_rate_item0_value"],"itemMargin":0,"styles":{"height":32.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"heart_rate_row0","component":"Row","children":["heart_rate_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":32.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["favorite_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"favorite_action","component":"Stack","children":["favorite_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#338C4B1C","alignContent":"center","clip":true}},{"id":"favorite_action_icon","component":"Image","src":"resources/base/media/music_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"targetDateText":"2026-08-06","exerciseTypeName":"户外跑步","exerciseHeartRateMin":96}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个训练音乐卡片，看今天的运动日期、最近一次练了什么和最低心率，点一下打开收藏的歌单。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.music.favorite",
      "description": "打开音乐app的收藏歌单/心动歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "healthSport": {
        "targetDateText": {
          "type": "string",
          "description": "该组健康与运动数据所归属的确切日期文本，格式为 YYYY-MM-DD，例如 '2026-07-06'。用于明确展示当前查阅的是哪一天的数据。",
          "sampleValue": "2026-08-06"
        },
        "exerciseTypeName": {
          "type": "string",
          "description": "最近一次发生的单次专业运动训练类型的中文映射名称，如“羽毛球”、“自由训练”、“户外跑步”。若无记录则返回“暂无运动”。",
          "sampleValue": "户外跑步"
        },
        "exerciseHeartRateMin": {
          "type": "integer",
          "description": "专业运动期间最低心率的纯整数，单位为次/分钟，返回值不包含单位。若直接用于文本展示，必须在数值后追加“次/分钟”。",
          "sampleValue": 96
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.calendar_fill",
      "src": "resources/base/media/calendar_fill.svg",
      "description": "样式：日历实心图标，默认黑色，图形为带格线的日历本造型；适用：日程管理、日历事件查看、当日安排。"
    },
    {
      "id": "asset.figure_run",
      "src": "resources/base/media/figure_run.svg",
      "description": "样式：跑步人物图标，默认黑色，图形为人体奔跑动作侧视轮廓；适用：运动记录、跑步锻炼追踪、步数统计。"
    },
    {
      "id": "asset.heart_fill",
      "src": "resources/base/media/heart_fill.svg",
      "description": "样式：默认黑色的单色实心爱心图标；适用：喜欢、收藏、关爱、心脏健康或心率栏目入口。"
    },
    {
      "id": "asset.music_fill",
      "src": "resources/base/media/music_fill.svg",
      "description": "样式：音乐音符实心图标，默认黑色，图形为双音符连接造型；适用：音乐播放卡片、音频功能入口、歌单展示。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetHealthAndSportSummary"
  ],
  "event": [
    {
      "id": "event.open.music.favorite",
      "description": "打开音乐app的收藏歌单/心动歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
      }
    }
  ],
  "asset": [
    "asset.calendar_fill",
    "asset.figure_run",
    "asset.heart_fill",
    "asset.music_fill"
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
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/targetDateText",
        "/exerciseTypeName",
        "/exerciseHeartRateMin"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.music.favorite",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Music",
          "bundleName": "",
          "abilityName": "",
          "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.figure_run",
    "asset.heart_fill",
    "asset.music_fill"
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
  "artifactId": "4c7fecdf-b77f-4886-aa1a-3f1523b0aaa8",
  "createdAt": 1792045479232
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["title_area","exercise","heart_rate","favorite_action"]]
["title_area","SingleLineTitle",{"title":{"path":"/data/healthSport/targetDateText"},"icon":"resources/base/media/figure_run.svg","fontSize":12}]
["exercise","EmphasisText",{"mainText":{"path":"/data/healthSport/exerciseTypeName"},"fontSize":18}]
["heart_rate","SecondaryBody",{"items":[{"label":"最低心率 ","value":"{{ ${/data/healthSport/exerciseHeartRateMin} + '次/分钟' }}"}],"fontSize":14}]
["favorite_action","CircleButton",{"icon":"resources/base/media/music_fill.svg","accessibility":{"label":"打开收藏歌单"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"}}]}]
["/data/healthSport/targetDateText","2026-08-06"]
["/data/healthSport/exerciseTypeName","户外跑步"]
["/data/healthSport/exerciseHeartRateMin",96]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个训练音乐卡片，看今天的运动日期、最近一次练了什么和最低心率，点一下打开收藏的歌单。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": 0
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/targetDateText",
          "/exerciseTypeName",
          "/exerciseHeartRateMin"
        ]
      }
    ],
    "title": "训练音乐",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.music.favorite",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Music",
            "bundleName": "",
            "abilityName": "",
            "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
          }
        }
      }
    ],
    "description": "训练记录和歌单",
    "candidateAssetIds": [
      "asset.calendar_fill",
      "asset.figure_run",
      "asset.heart_fill",
      "asset.music_fill"
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
    "interactionId": "027",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个训练音乐卡片，看今天的运动日期、最近一次练了什么和最低心率，点一下打开收藏的歌单。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个训练音乐卡片，看今天的运动日期、最近一次练了什么和最低心率，点一下打开收藏的歌单。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/targetDateText",
        "/exerciseTypeName",
        "/exerciseHeartRateMin"
      ]
    }
  ],
  "title": "训练音乐",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.music.favorite",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Music",
          "bundleName": "",
          "abilityName": "",
          "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
        }
      }
    }
  ],
  "description": "训练记录和歌单",
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.figure_run",
    "asset.heart_fill",
    "asset.music_fill"
  ]
}
```
