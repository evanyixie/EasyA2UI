```cardspec
{
  "title": "会前提醒",
  "description": "会议日期倒计时+免打扰",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["countdown"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"countdown","component":"Row","children":["countdown_value","countdown_unit"],"itemMargin":2,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"countdown_value","component":"Text","content":"{{ ${/data/calendar/events/0/countdownDays} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"countdown_unit","component":"Text","content":"天","styles":{"height":13.75,"fontSize":12,"fontWeight":500,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#998C4B1C","padding":{"top":0,"right":0,"bottom":1.75,"left":0},"textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["meeting_info","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"meeting_info","component":"Column","children":["meeting_info_row0","meeting_info_row1"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"meeting_info_item0_label","component":"Text","content":"日期 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"meeting_info_item0_value","component":"Text","content":"{{ ${/data/calendar/events/0/startDate} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"meeting_info_item0","component":"Row","children":["meeting_info_item0_label","meeting_info_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"meeting_info_row0","component":"Row","children":["meeting_info_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"meeting_info_item1_label","component":"Text","content":"开始 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"meeting_info_item1_value","component":"Text","content":"{{ ${/data/calendar/events/0/dtStart} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"meeting_info_item1","component":"Row","children":["meeting_info_item1_label","meeting_info_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"meeting_info_row1","component":"Row","children":["meeting_info_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["dnd_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"dnd_action","component":"Stack","children":["dnd_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"intelligent_scene_entry"}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#338C4B1C","alignContent":"center","clip":true}},{"id":"dnd_action_icon","component":"Image","src":"resources/base/media/bell_slash_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"title":"项目例会","startDate":"08-06","dtStart":"14:00","countdownDays":0}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个会议提醒卡片，看会议名称、会议日期、几点开始和离会议还有几天，点击进入免打扰设置。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
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
      "calendar": {
        "events": [
          {
            "title": {
              "type": "string",
              "description": "日程标题，例如“咪咕视频《西班牙 VS 奥地利》”或航“项目进展会”。",
              "sampleValue": "项目例会"
            },
            "startDate": {
              "type": "string",
              "description": "日程开始日期格式化文本，例如 '07-03'。",
              "sampleValue": "08-06"
            },
            "dtStart": {
              "type": "string",
              "description": "格式化后的日程开始时间短文本，如 '03:00'，若为全天日程可能为特殊标记。",
              "sampleValue": "14:00"
            },
            "countdownDays": {
              "type": "integer",
              "description": "距离日程开始的自然日天数纯整数，返回值不包含“天”。0 表示今天发生或已经发生，正整数表示距离开始还有多少天；若直接用于文本展示，必须在数值后追加“天”。",
              "sampleValue": 0
            }
          }
        ]
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.icon_meeting",
      "src": "resources/base/media/icon_meeting.svg",
      "description": "样式：默认白色的单色线面结合会议演示板图标，画板内有两条横线，原始尺寸为 14×14，支持通过 fillColor 与卡片配色统一；适用：会议、汇报、演示、议程。"
    },
    {
      "id": "asset.calendar_fill",
      "src": "resources/base/media/calendar_fill.svg",
      "description": "样式：日历实心图标，默认黑色，图形为带格线的日历本造型；适用：日程管理、日历事件查看、当日安排。"
    },
    {
      "id": "asset.icon_timing",
      "src": "resources/base/media/icon_timing.svg",
      "description": "样式：默认白色的单色秒表实心图标，内部通过镂空表现表盘指针，支持通过 fillColor 与卡片配色统一；适用：计时、使用时长、倒计时或时限。"
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
    "GetCalendarEvents"
  ],
  "event": [
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
    "asset.icon_meeting",
    "asset.calendar_fill",
    "asset.icon_timing",
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
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/startDate",
        "/events/0/dtStart",
        "/events/0/countdownDays"
      ]
    }
  ],
  "candidateEventCandidates": [
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
    "asset.icon_meeting",
    "asset.calendar_fill",
    "asset.icon_timing",
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
  "artifactId": "d864d0c4-480e-40fb-938a-dd8dbdd2500a",
  "createdAt": 1792045619555
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","countdown","meeting_info","dnd_action"]]
["header","SingleLineTitle",{"title":{"path":"/data/calendar/events/0/title"},"icon":"resources/base/media/icon_meeting.svg","fontSize":12}]
["countdown","EmphasizedData",{"value":{"path":"/data/calendar/events/0/countdownDays"},"unit":"天","fontSize":30}]
["meeting_info","SecondaryBody",{"items":[{"label":"日期 ","value":{"path":"/data/calendar/events/0/startDate"}},{"label":"开始 ","value":{"path":"/data/calendar/events/0/dtStart"}}],"separator":" | ","fontSize":14}]
["dnd_action","CircleButton",{"icon":"resources/base/media/bell_slash_fill.svg","accessibility":{"label":"打开免打扰设置"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"intelligent_scene_entry"}}]}]
["/data/calendar/events/0/title","项目例会"]
["/data/calendar/events/0/startDate","08-06"]
["/data/calendar/events/0/dtStart","14:00"]
["/data/calendar/events/0/countdownDays",0]
```
```request
{
  "content": {
    "userQuery": "帮我做个会议提醒卡片，看会议名称、会议日期、几点开始和离会议还有几天，点击进入免打扰设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 7
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/title",
          "/events/0/startDate",
          "/events/0/dtStart",
          "/events/0/countdownDays"
        ]
      }
    ],
    "title": "会前提醒",
    "size": "2x2",
    "candidateEventCandidates": [
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
    "description": "会议日期倒计时+免打扰",
    "candidateAssetIds": [
      "asset.icon_meeting",
      "asset.calendar_fill",
      "asset.icon_timing",
      "asset.bell_slash_fill"
    ],
    "bundleName": "com.omega_w_0823.hmservice"
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
  "session": {
    "interactionId": "050",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "utterance": {
    "original": "帮我做个会议提醒卡片，看会议名称、会议日期、几点开始和离会议还有几天，点击进入免打扰设置。",
    "type": "text"
  },
  "userQuery": "帮我做个会议提醒卡片，看会议名称、会议日期、几点开始和离会议还有几天，点击进入免打扰设置。",
  "size": "2x2",
  "candidateEventCandidates": [
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
  "bundleName": "com.omega_w_0823.hmservice",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/startDate",
        "/events/0/dtStart",
        "/events/0/countdownDays"
      ]
    }
  ],
  "title": "会前提醒",
  "description": "会议日期倒计时+免打扰",
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.calendar_fill",
    "asset.icon_timing",
    "asset.bell_slash_fill"
  ]
}
```
