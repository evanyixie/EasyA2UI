```cardspec
{
  "title": "下一场日程",
  "description": "会议时间+一键入会",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"需求评审会","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/clock_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["event"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"event","component":"Row","children":["event_rail","event_texts"],"itemMargin":7,"styles":{"width":"matchParent","alignItems":"top","flexShrink":1,"clip":true,"height":34}},{"id":"event_rail","component":"Column","children":["event_rail_dot","event_rail_line"],"itemMargin":5,"styles":{"width":8,"padding":{"top":5,"bottom":0},"alignItems":"center","justifyContent":"start","flexShrink":0,"height":34,"clip":true}},{"id":"event_rail_dot","component":"Divider","styles":{"width":8,"height":8,"borderRadius":4,"borderWidth":1.5,"strokeWidth":0,"color":"#00FFFFFF","flexShrink":0,"borderColor":"#FF8C4B1C","backgroundColor":"#00FFFFFF"}},{"id":"event_rail_line","component":"Divider","styles":{"width":1,"strokeWidth":1,"vertical":true,"flexShrink":0,"height":16,"color":"#998C4B1C"}},{"id":"event_texts","component":"Column","children":["event_title","event_time"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"start","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"height":34}},{"id":"event_title","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"width":"matchParent","fontSize":14,"fontWeight":700,"maxLines":2,"flexShrink":0,"constraintSize":{"minWidth":0,"minHeight":18},"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"event_time","component":"Text","content":"{{ ${/data/calendar/events/0/dtStart} + ' - ' + ${/data/calendar/events/0/dtEnd} }}","styles":{"width":"matchParent","height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"__layout__root__action","component":"Column","children":["cta"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"cta","component":"Row","children":["cta_icon","cta_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"EnterMeeting","bundleName":"","abilityName":"","uri":"{{ ${/data/calendar/events/0/oneClickServiceLink} }}"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#338C4B1C","justifyContent":"center","alignItems":"center"}},{"id":"cta_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"cta_text","component":"Text","content":"一键入会","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"title":"需求评审会","dtStart":"14:00","dtEnd":"15:00","oneClickServiceLink":""}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个日程卡片，下午两点有需求评审会，卡片可以看会议名称、开始和结束时间，点击按钮一键入会。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.enter.meeting",
      "description": "点击一键加入下一个日程对应的Welink会议。uri取自数据能力GetCalendarEvents返回结果中event的oneClickServiceLink字段。注意：模板中events/i的i需替换为当前事件的实际索引，如events/0、events/1等。",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "EnterMeeting",
        "bundleName": "",
        "abilityName": "",
        "uri": "{{ ${/data/calendar/events/0/oneClickServiceLink} }}"
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
            },
            "dtEnd": {
              "type": "string",
              "description": "格式化后的日程结束时间短文本，如 '05:00'。",
              "sampleValue": "15:00"
            },
            "oneClickServiceLink": {
              "type": "string",
              "description": "一键直达的 URI 深度跳转链接，UI 卡片可直接通过此链接拉起第三方 App 落地页。",
              "sampleValue": ""
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
    "GetCalendarEvents"
  ],
  "event": [
    {
      "id": "event.enter.meeting",
      "description": "点击一键加入下一个日程对应的Welink会议。uri取自数据能力GetCalendarEvents返回结果中event的oneClickServiceLink字段。注意：模板中events/i的i需替换为当前事件的实际索引，如events/0、events/1等。",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "EnterMeeting",
        "bundleName": "",
        "abilityName": "",
        "uri": "{{ ${/data/calendar/events/0/oneClickServiceLink} }}"
      }
    }
  ],
  "asset": [
    "asset.icon_meeting",
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
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/dtStart",
        "/events/0/dtEnd",
        "/events/0/oneClickServiceLink"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.enter.meeting",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "EnterMeeting",
          "bundleName": "",
          "abilityName": "",
          "uri": "{{ ${/data/calendar/events/0/oneClickServiceLink} }}"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.icon_meeting",
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
  "artifactId": "83453610-1bf4-443b-901e-2d3cd0d60390",
  "createdAt": 1792045491795
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","event","cta"]]
["header","SingleLineTitle",{"title":"需求评审会","icon":"resources/base/media/clock_fill.svg","fontSize":12}]
["event","EventCard",{"items":[{"title":{"path":"/data/calendar/events/0/title"},"time":"{{ ${/data/calendar/events/0/dtStart} + ' - ' + ${/data/calendar/events/0/dtEnd} }}"}]}]
["cta","PillButton",{"label":"一键入会","icon":"resources/base/media/icon_meeting.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"EnterMeeting","bundleName":"","abilityName":"","uri":"{{ ${/data/calendar/events/0/oneClickServiceLink} }}"}}]}]
["/data/calendar/events/0/title","需求评审会"]
["/data/calendar/events/0/dtStart","14:00"]
["/data/calendar/events/0/dtEnd","15:00"]
["/data/calendar/events/0/oneClickServiceLink",""]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个日程卡片，下午两点有需求评审会，卡片可以看会议名称、开始和结束时间，点击按钮一键入会。",
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
          "/events/0/dtEnd",
          "/events/0/oneClickServiceLink"
        ]
      }
    ],
    "title": "下一场日程",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.enter.meeting",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "EnterMeeting",
            "bundleName": "",
            "abilityName": "",
            "uri": "{{ ${/data/calendar/events/0/oneClickServiceLink} }}"
          }
        }
      }
    ],
    "description": "会议时间+一键入会",
    "candidateAssetIds": [
      "asset.icon_meeting",
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
    "time": "20260821000000000"
  },
  "pagination": {
    "limit": 5,
    "start": ""
  },
  "session": {
    "interactionId": "030",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个日程卡片，下午两点有需求评审会，卡片可以看会议名称、开始和结束时间，点击按钮一键入会。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个日程卡片，下午两点有需求评审会，卡片可以看会议名称、开始和结束时间，点击按钮一键入会。",
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
        "/events/0/dtEnd",
        "/events/0/oneClickServiceLink"
      ]
    }
  ],
  "title": "下一场日程",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.enter.meeting",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "EnterMeeting",
          "bundleName": "",
          "abilityName": "",
          "uri": "{{ ${/data/calendar/events/0/oneClickServiceLink} }}"
        }
      }
    }
  ],
  "description": "会议时间+一键入会",
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.clock_fill"
  ]
}
```
