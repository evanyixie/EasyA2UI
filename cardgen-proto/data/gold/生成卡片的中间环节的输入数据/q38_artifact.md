```cardspec
{
  "title": "睡眠健康",
  "description": "昨晚睡眠+健康使用设置",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"昨晚睡眠","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#99563D99"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/moon_z_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF563D99"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["score"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"score","component":"Row","children":["score_value","score_unit"],"itemMargin":2,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"score_value","component":"Text","content":"{{ ${/data/healthSport/sleepScore} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"score_unit","component":"Text","content":"分","styles":{"height":14.0,"fontSize":12,"fontWeight":500,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#99563D99","padding":{"top":0,"right":0,"bottom":2,"left":0},"textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["sleep_detail","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"sleep_detail","component":"Column","children":["sleep_detail_row0","sleep_detail_row1"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"sleep_detail_item0_label","component":"Text","content":"状态 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"sleep_detail_item0_value","component":"Text","content":"{{ ${/data/healthSport/sleepStatus} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#99563D99","layoutWeight":1,"textOverflow":"clip"}},{"id":"sleep_detail_item0","component":"Row","children":["sleep_detail_item0_label","sleep_detail_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"sleep_detail_row0","component":"Row","children":["sleep_detail_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"sleep_detail_item1_value","component":"Text","content":"{{ '时长 ' + ${/data/healthSport/nightSleepDurationText} }}","styles":{"height":32.0,"fontSize":12,"fontWeight":400,"maxLines":2,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#99563D99","layoutWeight":1,"textOverflow":"clip"}},{"id":"sleep_detail_item1","component":"Row","children":["sleep_detail_item1_value"],"itemMargin":0,"styles":{"height":32.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"sleep_detail_row1","component":"Row","children":["sleep_detail_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":32.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["usage_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"usage_action","component":"Stack","children":["usage_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"parent_control"}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#33563D99","alignContent":"center","clip":true}},{"id":"usage_action_icon","component":"Image","src":"resources/base/media/clock_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF563D99"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"sleepScore":82,"sleepStatus":"良好","nightSleepDurationText":"7小时1分"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，看昨晚睡眠得分、睡眠状态和睡了多久，点一下能去设置手机使用时长。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.settings.parentControl",
      "description": "打开系统设置中的健康使用App页面，为了设置应用使用时长",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "parent_control"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "healthSport": {
        "sleepScore": {
          "type": "integer",
          "description": "睡眠综合得分，取值范围 0-100。",
          "sampleValue": 82
        },
        "sleepStatus": {
          "type": "string",
          "description": "基于得分智能生成的睡眠状态语义判定，包括：'优秀'、'良好'、'一般'、'较差'。",
          "sampleValue": "良好"
        },
        "nightSleepDurationText": {
          "type": "string",
          "description": "可直接显示的夜间正式睡眠总时长文本，已包含“小时”或“分”等时间单位；展示时不得再次追加时间单位。例如“7小时1分”。",
          "sampleValue": "7小时1分"
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
    "GetHealthAndSportSummary"
  ],
  "event": [
    {
      "id": "event.open.settings.parentControl",
      "description": "打开系统设置中的健康使用App页面，为了设置应用使用时长",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Settings",
        "bundleName": "com.huawei.hmos.settings",
        "abilityName": "com.huawei.hmos.settings.MainAbility",
        "uri": "parent_control"
      }
    }
  ],
  "asset": [
    "asset.moon_z_fill_1",
    "asset.clock_fill",
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
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/sleepScore",
        "/sleepStatus",
        "/nightSleepDurationText"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.parentControl",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "parent_control"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.moon_z_fill_1",
    "asset.clock_fill",
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
  "artifactId": "8bbc9525-e6c8-47f3-b779-4e78b601c8c4",
  "createdAt": 1792045528848
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}},["title_area","score","sleep_detail","usage_action"]]
["title_area","SingleLineTitle",{"title":"昨晚睡眠","icon":"resources/base/media/moon_z_fill_1.svg","fontSize":12}]
["score","EmphasizedData",{"value":{"path":"/data/healthSport/sleepScore"},"unit":"分","fontSize":30}]
["sleep_detail","SecondaryBody",{"items":[{"label":"状态 ","value":{"path":"/data/healthSport/sleepStatus"}},{"label":"时长 ","value":{"path":"/data/healthSport/nightSleepDurationText"}}],"separator":" | ","fontSize":14}]
["usage_action","CircleButton",{"icon":"resources/base/media/clock_fill.svg","accessibility":{"label":"设置应用使用时长"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"parent_control"}}]}]
["/data/healthSport/sleepScore",82]
["/data/healthSport/sleepStatus","良好"]
["/data/healthSport/nightSleepDurationText","7小时1分"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，看昨晚睡眠得分、睡眠状态和睡了多久，点一下能去设置手机使用时长。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": -1
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/sleepScore",
          "/sleepStatus",
          "/nightSleepDurationText"
        ]
      }
    ],
    "title": "睡眠健康",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.settings.parentControl",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Settings",
            "bundleName": "com.huawei.hmos.settings",
            "abilityName": "com.huawei.hmos.settings.MainAbility",
            "uri": "parent_control"
          }
        }
      }
    ],
    "description": "昨晚睡眠+健康使用设置",
    "candidateAssetIds": [
      "asset.moon_z_fill_1",
      "asset.clock_fill",
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
    "interactionId": "038",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，看昨晚睡眠得分、睡眠状态和睡了多久，点一下能去设置手机使用时长。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，看昨晚睡眠得分、睡眠状态和睡了多久，点一下能去设置手机使用时长。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/sleepScore",
        "/sleepStatus",
        "/nightSleepDurationText"
      ]
    }
  ],
  "title": "睡眠健康",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.settings.parentControl",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Settings",
          "bundleName": "com.huawei.hmos.settings",
          "abilityName": "com.huawei.hmos.settings.MainAbility",
          "uri": "parent_control"
        }
      }
    }
  ],
  "description": "昨晚睡眠+健康使用设置",
  "candidateAssetIds": [
    "asset.moon_z_fill_1",
    "asset.clock_fill",
    "asset.phone_fill"
  ]
}
```
