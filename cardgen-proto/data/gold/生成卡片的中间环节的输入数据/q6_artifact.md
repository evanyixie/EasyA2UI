```cardspec
{
  "title": "明日双会",
  "description": "两场会议安排",
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
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__content"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"明日会议","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__content","component":"Column","children":["events"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"events","component":"Column","children":["events_item0","events_item1"],"itemMargin":4,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","flexShrink":1,"clip":true,"height":68}},{"id":"events_item0","component":"Row","children":["events_item0_rail","events_item0_texts"],"itemMargin":7,"styles":{"width":"matchParent","alignItems":"top","flexShrink":0,"clip":true,"height":32}},{"id":"events_item0_rail","component":"Column","children":["events_item0_rail_dot","events_item0_rail_line"],"itemMargin":4,"styles":{"width":8,"padding":{"top":4,"bottom":0},"alignItems":"center","justifyContent":"start","flexShrink":0,"height":32,"clip":true}},{"id":"events_item0_rail_dot","component":"Divider","styles":{"width":8,"height":8,"borderRadius":4,"borderWidth":1.5,"strokeWidth":0,"color":"#00FFFFFF","flexShrink":0,"borderColor":"#FF8C4B1C","backgroundColor":"#00FFFFFF"}},{"id":"events_item0_rail_line","component":"Divider","styles":{"width":1,"strokeWidth":1,"vertical":true,"flexShrink":0,"height":16,"color":"#998C4B1C"}},{"id":"events_item0_texts","component":"Column","children":["events_item0_title","events_item0_meta"],"itemMargin":2,"styles":{"alignItems":"start","justifyContent":"start","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"height":32}},{"id":"events_item0_title","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"width":"matchParent","fontSize":12,"fontWeight":700,"maxLines":1,"flexShrink":0,"constraintSize":{"minWidth":0,"minHeight":16},"height":16,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"events_item0_time","component":"Text","content":"{{ ${/data/calendar/events/0/dtStart} }}","styles":{"width":"matchParent","height":14,"fontSize":10,"fontWeight":400,"maxLines":1,"flexShrink":0,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"events_item0_meta","component":"Row","children":["events_item0_time"],"itemMargin":4,"styles":{"width":"matchParent","height":14,"alignItems":"center","flexShrink":0,"clip":true}},{"id":"events_item1","component":"Row","children":["events_item1_rail","events_item1_texts"],"itemMargin":7,"styles":{"width":"matchParent","alignItems":"top","flexShrink":0,"clip":true,"height":32}},{"id":"events_item1_rail","component":"Column","children":["events_item1_rail_dot","events_item1_rail_line"],"itemMargin":4,"styles":{"width":8,"padding":{"top":4,"bottom":0},"alignItems":"center","justifyContent":"start","flexShrink":0,"height":32,"clip":true}},{"id":"events_item1_rail_dot","component":"Divider","styles":{"width":8,"height":8,"borderRadius":4,"borderWidth":1.5,"strokeWidth":0,"color":"#00FFFFFF","flexShrink":0,"borderColor":"#FF8C4B1C","backgroundColor":"#00FFFFFF"}},{"id":"events_item1_rail_line","component":"Divider","styles":{"width":1,"strokeWidth":1,"vertical":true,"flexShrink":0,"height":16,"color":"#998C4B1C"}},{"id":"events_item1_texts","component":"Column","children":["events_item1_title","events_item1_meta"],"itemMargin":2,"styles":{"alignItems":"start","justifyContent":"start","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"height":32}},{"id":"events_item1_title","component":"Text","content":"{{ ${/data/calendar/events/1/title} }}","styles":{"width":"matchParent","fontSize":12,"fontWeight":700,"maxLines":1,"flexShrink":0,"constraintSize":{"minWidth":0,"minHeight":16},"height":16,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"events_item1_time","component":"Text","content":"{{ ${/data/calendar/events/1/dtStart} }}","styles":{"width":"matchParent","height":14,"fontSize":10,"fontWeight":400,"maxLines":1,"flexShrink":0,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"events_item1_meta","component":"Row","children":["events_item1_time"],"itemMargin":4,"styles":{"width":"matchParent","height":14,"alignItems":"center","flexShrink":0,"clip":true}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"title":"产品立项会","dtStart":"09:00"},{"title":"客户交流会","dtStart":"15:00"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "明天上午九点有产品立项会，下午三点有客户交流会，帮我做个卡片，分别看两场会议的标题和开始时间。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
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
          },
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
      "id": "asset.clock_fill",
      "src": "resources/base/media/clock_fill.svg",
      "description": "样式：默认黑色的单色实心圆形时钟图标，内部通过镂空表现表盘指针，原始尺寸为 24×24，支持通过 fillColor 与卡片配色统一；适用：时间显示、闹钟设置、定时器、提醒时间、应用使用时长与运动时长。"
    },
    {
      "id": "asset.icon_meeting",
      "src": "resources/base/media/icon_meeting.svg",
      "description": "样式：默认白色的单色线面结合会议演示板图标，画板内有两条横线，原始尺寸为 14×14，支持通过 fillColor 与卡片配色统一；适用：会议、汇报、演示、议程。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetCalendarEvents"
  ],
  "event": [],
  "asset": [
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.icon_meeting"
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
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/dtStart",
        "/events/1/title",
        "/events/1/dtStart"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.icon_meeting"
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
  "artifactId": "61c074a5-6494-4241-9b5a-a53512c50739",
  "createdAt": 1792045372502
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","events"]]
["header","SingleLineTitle",{"title":"明日会议","icon":"resources/base/media/icon_meeting.svg","fontSize":12}]
["events","EventCard",{"items":[{"title":{"path":"/data/calendar/events/0/title"},"time":{"path":"/data/calendar/events/0/dtStart"}},{"title":{"path":"/data/calendar/events/1/title"},"time":{"path":"/data/calendar/events/1/dtStart"}}],"density":"compact"}]
["/data/calendar/events/0/title","产品立项会"]
["/data/calendar/events/0/dtStart","09:00"]
["/data/calendar/events/1/title","客户交流会"]
["/data/calendar/events/1/dtStart","15:00"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "明天上午九点有产品立项会，下午三点有客户交流会，帮我做个卡片，分别看两场会议的标题和开始时间。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 1
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/title",
          "/events/0/dtStart",
          "/events/1/title",
          "/events/1/dtStart"
        ]
      }
    ],
    "title": "明日双会",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "两场会议安排",
    "candidateAssetIds": [
      "asset.calendar_fill",
      "asset.clock_fill",
      "asset.icon_meeting"
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
    "interactionId": "006",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "明天上午九点有产品立项会，下午三点有客户交流会，帮我做个卡片，分别看两场会议的标题和开始时间。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "明天上午九点有产品立项会，下午三点有客户交流会，帮我做个卡片，分别看两场会议的标题和开始时间。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/dtStart",
        "/events/1/title",
        "/events/1/dtStart"
      ]
    }
  ],
  "title": "明日双会",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "两场会议安排",
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.icon_meeting"
  ]
}
```
