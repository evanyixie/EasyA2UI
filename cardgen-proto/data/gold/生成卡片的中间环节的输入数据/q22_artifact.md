```cardspec
{
  "title": "运动音乐",
  "description": "运动数据和歌单",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","content_flow","cta"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"最近运动","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/figure_run.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"content_flow","component":"Column","children":["duration","metrics"],"itemMargin":2,"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"start"}},{"id":"duration","component":"Column","children":["duration_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"duration_main","component":"Text","content":"{{ ${/data/healthSport/exerciseDurationText} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"metrics","component":"Column","children":["metrics_row0","metrics_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"metrics_item0_label","component":"Text","content":"消耗 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"metrics_item0_value","component":"Text","content":"{{ ${/data/healthSport/exerciseCalorieText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"metrics_item0","component":"Row","children":["metrics_item0_label","metrics_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"metrics_row0","component":"Row","children":["metrics_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"metrics_item1_label","component":"Text","content":"平均心率 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"metrics_item1_value","component":"Text","content":"{{ ${/data/healthSport/exerciseHeartRateAvg} + '次/分钟' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"metrics_item1","component":"Row","children":["metrics_item1_label","metrics_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"metrics_row1","component":"Row","children":["metrics_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"cta","component":"Row","children":["cta_icon","cta_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#338C4B1C","justifyContent":"center","alignItems":"center"}},{"id":"cta_icon","component":"Image","src":"resources/base/media/music_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"cta_text","component":"Text","content":"打开歌单","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"exerciseDurationText":"40分","exerciseCalorieText":"260 千卡","exerciseHeartRateAvg":135}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个运动音乐卡片，看今天最近一次运动的时长、消耗热量和平均心率，训练时可以打开歌单。",
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
    }
  ],
  "dataModelSchema": {
    "data": {
      "healthSport": {
        "exerciseDurationText": {
          "type": "string",
          "description": "可直接显示的单次专业运动实际持续时长文本，已包含“小时”或“分”等时间单位；展示时不得再次追加时间单位。例如“1小时40分”。",
          "sampleValue": "40分"
        },
        "exerciseCalorieText": {
          "type": "string",
          "description": "可直接显示的单次专业运动净热量消耗文本，已换算并包含“千卡”单位；展示时不得再次追加热量单位。例如“98 千卡”。",
          "sampleValue": "260 千卡"
        },
        "exerciseHeartRateAvg": {
          "type": "integer",
          "description": "专业运动期间平均心率的纯整数，单位为次/分钟，返回值不包含单位。若直接用于文本展示，必须在数值后追加“次/分钟”。",
          "sampleValue": 135
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.figure_run",
      "src": "resources/base/media/figure_run.svg",
      "description": "样式：跑步人物图标，默认黑色，图形为人体奔跑动作侧视轮廓；适用：运动记录、跑步锻炼追踪、步数统计。"
    },
    {
      "id": "asset.flame_fill",
      "src": "resources/base/media/flame_fill.svg",
      "description": "样式：默认黑色的单色实心火焰图标；适用：运动热量消耗、燃烧、火焰或加热状态。"
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
      "id": "event.open.music.daily",
      "description": "打开音乐app的每日30首歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"
      }
    }
  ],
  "asset": [
    "asset.figure_run",
    "asset.flame_fill",
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
        "/exerciseDurationText",
        "/exerciseCalorieText",
        "/exerciseHeartRateAvg"
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
    }
  ],
  "candidateAssetIds": [
    "asset.figure_run",
    "asset.flame_fill",
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
  "artifactId": "fafbb9f7-9fa8-44d3-a994-11207b768ce4",
  "createdAt": 1792045448963
}
```
```designcompactdsl
["root","Column",{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"itemMargin":6,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","content_flow","cta"]]
["header","SingleLineTitle",{"title":"最近运动","icon":"resources/base/media/figure_run.svg","fontSize":12,"width":"matchParent"}]
["content_flow","Column",{"width":"matchParent","layoutWeight":1,"itemMargin":2,"alignItems":"start","justifyContent":"start"},["duration","metrics"]]
["duration","EmphasisText",{"mainText":{"path":"/data/healthSport/exerciseDurationText"},"fontSize":18,"width":"matchParent"}]
["metrics","SecondaryBody",{"items":[{"label":"消耗 ","value":{"path":"/data/healthSport/exerciseCalorieText"}},{"label":"平均心率 ","value":"{{ ${/data/healthSport/exerciseHeartRateAvg} + '次/分钟' }}"}],"columns":1,"fontSize":12,"width":"matchParent"}]
["cta","PillButton",{"label":"打开歌单","icon":"resources/base/media/music_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4"}}]}]
["/data/healthSport/exerciseDurationText","40分"]
["/data/healthSport/exerciseCalorieText","260 千卡"]
["/data/healthSport/exerciseHeartRateAvg",135]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个运动音乐卡片，看今天最近一次运动的时长、消耗热量和平均心率，训练时可以打开歌单。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": 0
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/exerciseDurationText",
          "/exerciseCalorieText",
          "/exerciseHeartRateAvg"
        ]
      }
    ],
    "title": "运动音乐",
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
      }
    ],
    "description": "运动数据和歌单",
    "candidateAssetIds": [
      "asset.figure_run",
      "asset.flame_fill",
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
    "interactionId": "022",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个运动音乐卡片，看今天最近一次运动的时长、消耗热量和平均心率，训练时可以打开歌单。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个运动音乐卡片，看今天最近一次运动的时长、消耗热量和平均心率，训练时可以打开歌单。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/exerciseDurationText",
        "/exerciseCalorieText",
        "/exerciseHeartRateAvg"
      ]
    }
  ],
  "title": "运动音乐",
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
    }
  ],
  "description": "运动数据和歌单",
  "candidateAssetIds": [
    "asset.figure_run",
    "asset.flame_fill",
    "asset.heart_fill",
    "asset.music_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"duration\",\"metrics\",\"cta\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"最近运动\",\"icon\":\"resources/base/media/figure_run.svg\",\"fontSize\":12}]\n[\"duration\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/healthSport/exerciseDurationText\"},\"fontSize\":18}]\n[\"metrics\",\"SecondaryBody\",{\"items\":[{\"label\":\"消耗 \",\"value\":{\"path\":\"/data/healthSport/exerciseCalorieText\"}},{\"label\":\"平均心率 \",\"value\":\"{{ ${/data/healthSport/exerciseHeartRateAvg} + '次/分钟' }}\"}],\"columns\":1,\"fontSize\":12}]\n[\"cta\",\"PillButton\",{\"label\":\"打开歌单\",\"icon\":\"resources/base/media/music_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Music\",\"bundleName\":\"\",\"abilityName\":\"\",\"uri\":\"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4\"}}]}]\n[\"/data/healthSport/exerciseDurationText\",\"40分\"]\n[\"/data/healthSport/exerciseCalorieText\",\"260 千卡\"]\n[\"/data/healthSport/exerciseHeartRateAvg\",135]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"content_flow\",\"cta\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"最近运动\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#998C4B1C\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/figure_run.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"content_flow\",\"component\":\"Column\",\"children\":[\"duration\",\"metrics\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"layoutWeight\":1,\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"duration\",\"component\":\"Column\",\"children\":[\"duration_main\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"duration_main\",\"component\":\"Text\",\"content\":\"{{ ${/data/healthSport/exerciseDurationText} }}\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"metrics\",\"component\":\"Column\",\"children\":[\"metrics_row0\",\"metrics_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"metrics_item0_label\",\"component\":\"Text\",\"content\":\"消耗 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"metrics_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/healthSport/exerciseCalorieText} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"metrics_item0\",\"component\":\"Row\",\"children\":[\"metrics_item0_label\",\"metrics_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"metrics_row0\",\"component\":\"Row\",\"children\":[\"metrics_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"metrics_item1_label\",\"component\":\"Text\",\"content\":\"平均心率 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"metrics_item1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/healthSport/exerciseHeartRateAvg} + '次/分钟' }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"metrics_item1\",\"component\":\"Row\",\"children\":[\"metrics_item1_label\",\"metrics_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"metrics_row1\",\"component\":\"Row\",\"children\":[\"metrics_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"cta\",\"component\":\"Row\",\"children\":[\"cta_icon\",\"cta_text\"],\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Music\",\"bundleName\":\"\",\"abilityName\":\"\",\"uri\":\"hwmusic://com.huawei.hmsapp.music/showMusicList?code=a001&type=4\"}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#338C4B1C\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"cta_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/music_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"cta_text\",\"component\":\"Text\",\"content\":\"打开歌单\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"healthSport\":{\"exerciseDurationText\":\"40分\",\"exerciseCalorieText\":\"260 千卡\",\"exerciseHeartRateAvg\":135}}}}}",
  "validationErrors": []
}
```
