```cardspec
{
  "title": "就医提醒",
  "description": "日程时间+闹钟入口",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"明日日程","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/calendar_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["event"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"event","component":"Column","children":["event_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"event_main","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["time_info","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"time_info","component":"Column","children":["time_info_row0"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"time_info_item0_value","component":"Text","content":"{{ '开始时间 ' + ${/data/calendar/events/0/dtStart} }}","styles":{"height":32.0,"fontSize":12,"fontWeight":400,"maxLines":2,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"time_info_item0","component":"Row","children":["time_info_item0_value"],"itemMargin":0,"styles":{"height":32.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"time_info_row0","component":"Row","children":["time_info_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":32.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["alarm_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"alarm_action","component":"Stack","children":["alarm_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#338C4B1C","alignContent":"center","clip":true}},{"id":"alarm_action_icon","component":"Image","src":"resources/base/media/alarm_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"title":"项目例会","dtStart":"14:00"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，我明天上午10点要去医院复查，卡片展示日程信息、时间信息，点一下能进闹钟。",
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
      "calendar": {
        "events": [
          {
            "title": {
              "type": "string",
              "description": "日程标题，例如“咪咕视频《西班牙 VS 奥地利》”或航“项目进展会”。",
              "sampleValue": "项目例会"
            },
            "dtStart": {
              "type": "string",
              "description": "格式化后的日程开始时间短文本，如 '03:00'，若为全天日程可能为特殊标记。",
              "sampleValue": "14:00"
            }
          }
        ]
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
    "GetCalendarEvents"
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
    "asset.calendar_fill",
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
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/dtStart"
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
    "asset.calendar_fill",
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
  "artifactId": "fa823848-9fb4-49b1-8679-3c6f4969e35e",
  "createdAt": 1792045503304
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["title_area","event","time_info","alarm_action"]]
["title_area","SingleLineTitle",{"title":"明日日程","icon":"resources/base/media/calendar_fill.svg","fontSize":12}]
["event","EmphasisText",{"mainText":{"path":"/data/calendar/events/0/title"},"fontSize":18}]
["time_info","SecondaryBody",{"items":[{"label":"开始时间 ","value":{"path":"/data/calendar/events/0/dtStart"}}],"fontSize":14}]
["alarm_action","CircleButton",{"icon":"resources/base/media/alarm_fill_1.svg","accessibility":{"label":"打开闹钟"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}]}]
["/data/calendar/events/0/title","项目例会"]
["/data/calendar/events/0/dtStart","14:00"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，我明天上午10点要去医院复查，卡片展示日程信息、时间信息，点一下能进闹钟。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 7
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/title",
          "/events/0/dtStart"
        ]
      }
    ],
    "title": "就医提醒",
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
    "description": "日程时间+闹钟入口",
    "candidateAssetIds": [
      "asset.calendar_fill",
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
    "interactionId": "033",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，我明天上午10点要去医院复查，卡片展示日程信息、时间信息，点一下能进闹钟。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，我明天上午10点要去医院复查，卡片展示日程信息、时间信息，点一下能进闹钟。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/dtStart"
      ]
    }
  ],
  "title": "就医提醒",
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
  "description": "日程时间+闹钟入口",
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.alarm_fill_1"
  ]
}
```
