```cardspec
{
  "title": "作息提醒",
  "description": "小睡作息和闹钟",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"昨日作息","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#99563D99"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/moon_z_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF563D99"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["nap"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"nap","component":"Column","children":["nap_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"nap_main","component":"Text","content":"{{ '白天小睡 ' + ${/data/healthSport/totalNapDurationText} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["sleep_detail","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"sleep_detail","component":"Column","children":["sleep_detail_row0","sleep_detail_row1"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"sleep_detail_item0_label","component":"Text","content":"入睡 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"sleep_detail_item0_value","component":"Text","content":"{{ ${/data/healthSport/fallAsleepTimeText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#99563D99","layoutWeight":1,"textOverflow":"clip"}},{"id":"sleep_detail_item0","component":"Row","children":["sleep_detail_item0_label","sleep_detail_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"sleep_detail_row0","component":"Row","children":["sleep_detail_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"sleep_detail_item1_label","component":"Text","content":"醒来 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"sleep_detail_item1_value","component":"Text","content":"{{ ${/data/healthSport/wakeupTimeText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#99563D99","layoutWeight":1,"textOverflow":"clip"}},{"id":"sleep_detail_item1","component":"Row","children":["sleep_detail_item1_label","sleep_detail_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"sleep_detail_row1","component":"Row","children":["sleep_detail_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["alarm_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"alarm_action","component":"Stack","children":["alarm_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#33563D99","alignContent":"center","clip":true}},{"id":"alarm_action_icon","component":"Image","src":"resources/base/media/alarm_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF563D99"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"totalNapDurationText":"0分","fallAsleepTimeText":"23:15","wakeupTimeText":"07:30"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个作息卡片，看昨天白天小睡多久、晚上几点睡着和早上几点醒，点一下打开闹钟应用。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
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
      "healthSport": {
        "totalNapDurationText": {
          "type": "string",
          "description": "可直接显示的白天零星小睡累计总时长文本，已包含“小时”或“分”等时间单位；展示时不得再次追加时间单位。例如“45分”或“0分”。",
          "sampleValue": "0分"
        },
        "fallAsleepTimeText": {
          "type": "string",
          "description": "格式化后的确切入睡时刻短文本（HH:mm），例如“23:15”。",
          "sampleValue": "23:15"
        },
        "wakeupTimeText": {
          "type": "string",
          "description": "格式化后的确切醒来时刻短文本（HH:mm），例如“07:30”。",
          "sampleValue": "07:30"
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
    "GetHealthAndSportSummary"
  ],
  "event": [
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
    "asset.moon_z_fill_1",
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
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/totalNapDurationText",
        "/fallAsleepTimeText",
        "/wakeupTimeText"
      ]
    }
  ],
  "candidateEventCandidates": [
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
    "asset.moon_z_fill_1",
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
  "artifactId": "271c1348-a5c1-49a5-98b4-5a17f1e1946c",
  "createdAt": 1792045443663
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}},["title_area","nap","sleep_detail","alarm_action"]]
["title_area","SingleLineTitle",{"title":"昨日作息","icon":"resources/base/media/moon_z_fill_1.svg","fontSize":12}]
["nap","EmphasisText",{"mainText":"{{ '白天小睡 ' + ${/data/healthSport/totalNapDurationText} }}","fontSize":18}]
["sleep_detail","SecondaryBody",{"items":[{"label":"入睡 ","value":{"path":"/data/healthSport/fallAsleepTimeText"}},{"label":"醒来 ","value":{"path":"/data/healthSport/wakeupTimeText"}}],"columns":1,"fontSize":12}]
["alarm_action","CircleButton",{"icon":"resources/base/media/alarm_fill_1.svg","accessibility":{"label":"打开闹钟应用"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}]}]
["/data/healthSport/totalNapDurationText","0分"]
["/data/healthSport/fallAsleepTimeText","23:15"]
["/data/healthSport/wakeupTimeText","07:30"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个作息卡片，看昨天白天小睡多久、晚上几点睡着和早上几点醒，点一下打开闹钟应用。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": -1
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/totalNapDurationText",
          "/fallAsleepTimeText",
          "/wakeupTimeText"
        ]
      }
    ],
    "title": "作息提醒",
    "size": "2x2",
    "candidateEventCandidates": [
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
    "description": "小睡作息和闹钟",
    "candidateAssetIds": [
      "asset.moon_z_fill_1",
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
    "time": "20260828000000000"
  },
  "pagination": {
    "limit": 5,
    "start": ""
  },
  "session": {
    "interactionId": "021",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个作息卡片，看昨天白天小睡多久、晚上几点睡着和早上几点醒，点一下打开闹钟应用。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个作息卡片，看昨天白天小睡多久、晚上几点睡着和早上几点醒，点一下打开闹钟应用。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": -1
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/totalNapDurationText",
        "/fallAsleepTimeText",
        "/wakeupTimeText"
      ]
    }
  ],
  "title": "作息提醒",
  "size": "2x2",
  "candidateEventCandidates": [
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
  "description": "小睡作息和闹钟",
  "candidateAssetIds": [
    "asset.moon_z_fill_1",
    "asset.alarm_fill_1"
  ]
}
```
