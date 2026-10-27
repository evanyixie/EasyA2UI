```cardspec
{
  "title": "睡眠分析",
  "description": "睡眠时长与记录",
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
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"睡眠分析","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#99563D99"}},{"id":"header_icon","component":"Image","src":"resources/base/media/moon_z_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF563D99"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["duration"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"duration","component":"Column","children":["duration_main","duration_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"duration_main","component":"Text","content":"{{ ${/data/healthSport/nightSleepDurationText} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"duration_secondary","component":"Text","content":"昨晚总睡眠","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#99563D99","textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["detail"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"detail","component":"Column","children":["detail_row0","detail_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"detail_item0_label","component":"Text","content":"记录类型 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"detail_item0_value","component":"Text","content":"{{ ${/data/healthSport/sleepTypeDesc} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#99563D99","layoutWeight":1,"textOverflow":"clip"}},{"id":"detail_item0","component":"Row","children":["detail_item0_label","detail_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"detail_row0","component":"Row","children":["detail_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"detail_item1_label","component":"Text","content":"深睡 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"detail_item1_value","component":"Text","content":"{{ ${/data/healthSport/deepSleepDurationText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#99563D99","layoutWeight":1,"textOverflow":"clip"}},{"id":"detail_item1","component":"Row","children":["detail_item1_label","detail_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"detail_row1","component":"Row","children":["detail_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"nightSleepDurationText":"7小时1分","sleepTypeDesc":"科学睡眠","deepSleepDurationText":"2小时15分"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个睡眠分析卡片，看昨晚总睡眠时长，再看睡眠记录类型和深睡时长。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "healthSport": {
        "sleepTypeDesc": {
          "type": "string",
          "description": "睡眠记录方式或类型的描述，例如“科学睡眠”、“普通睡眠”、“手动输入睡眠”、“手机记录睡眠”。",
          "sampleValue": "科学睡眠"
        },
        "nightSleepDurationText": {
          "type": "string",
          "description": "可直接显示的夜间正式睡眠总时长文本，已包含“小时”或“分”等时间单位；展示时不得再次追加时间单位。例如“7小时1分”。",
          "sampleValue": "7小时1分"
        },
        "deepSleepDurationText": {
          "type": "string",
          "description": "可直接显示的夜间正式睡眠深睡总时长文本，已包含“小时”或“分”等时间单位；展示时不得再次追加时间单位。例如“2小时15分”。",
          "sampleValue": "2小时15分"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.moon_z_fill_1",
      "src": "resources/base/media/moon_z_fill_1.svg",
      "description": "样式：月亮加Z睡眠实心图标，默认黑色，图形为月牙旁附带字母Z表示入睡；适用：睡眠模式开启、休息提醒、晚安场景。"
    },
    {
      "id": "asset.clock_fill",
      "src": "resources/base/media/clock_fill.svg",
      "description": "样式：默认黑色的单色实心圆形时钟图标，内部通过镂空表现表盘指针，原始尺寸为 24×24，支持通过 fillColor 与卡片配色统一；适用：时间显示、闹钟设置、定时器、提醒时间、应用使用时长与运动时长。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetHealthAndSportSummary"
  ],
  "event": [],
  "asset": [
    "asset.moon_z_fill_1",
    "asset.clock_fill"
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
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/sleepTypeDesc",
        "/nightSleepDurationText",
        "/deepSleepDurationText"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.moon_z_fill_1",
    "asset.clock_fill"
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
  "artifactId": "b0b2b53b-ebbc-44e7-a62b-1035c7d3e202",
  "createdAt": 1792045398085
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}},["header","duration","detail"]]
["header","SingleLineTitle",{"title":"睡眠分析","icon":"resources/base/media/moon_z_fill_1.svg","fontSize":12}]
["duration","EmphasisText",{"mainText":{"path":"/data/healthSport/nightSleepDurationText"},"secondaryText":"昨晚总睡眠","fontSize":18}]
["detail","SecondaryBody",{"items":[{"label":"记录类型 ","value":{"path":"/data/healthSport/sleepTypeDesc"}},{"label":"深睡 ","value":{"path":"/data/healthSport/deepSleepDurationText"}}],"separator":" | ","fontSize":14}]
["/data/healthSport/nightSleepDurationText","7小时1分"]
["/data/healthSport/sleepTypeDesc","科学睡眠"]
["/data/healthSport/deepSleepDurationText","2小时15分"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个睡眠分析卡片，看昨晚总睡眠时长，再看睡眠记录类型和深睡时长。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": -1
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/sleepTypeDesc",
          "/nightSleepDurationText",
          "/deepSleepDurationText"
        ]
      }
    ],
    "title": "睡眠分析",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "睡眠时长与记录",
    "candidateAssetIds": [
      "asset.moon_z_fill_1",
      "asset.clock_fill"
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
    "interactionId": "012",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个睡眠分析卡片，看昨晚总睡眠时长，再看睡眠记录类型和深睡时长。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个睡眠分析卡片，看昨晚总睡眠时长，再看睡眠记录类型和深睡时长。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/sleepTypeDesc",
        "/nightSleepDurationText",
        "/deepSleepDurationText"
      ]
    }
  ],
  "title": "睡眠分析",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "睡眠时长与记录",
  "candidateAssetIds": [
    "asset.moon_z_fill_1",
    "asset.clock_fill"
  ]
}
```
