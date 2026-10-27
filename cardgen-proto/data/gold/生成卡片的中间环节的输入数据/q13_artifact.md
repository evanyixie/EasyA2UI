```cardspec
{
  "title": "线上评审",
  "description": "会议和耳机状态",
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
    },
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"线上评审","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/clock_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["start_time"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"start_time","component":"Column","children":["start_time_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"start_time_main","component":"Text","content":"{{ '会议开始 ' + ${/data/calendar/events/0/dtStart} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["earphone_summary","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"earphone_summary","component":"Column","children":["earphone_summary_row0","earphone_summary_row1"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"earphone_summary_item0_label","component":"Text","content":"耳机 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"earphone_summary_item0_value","component":"Text","content":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"earphone_summary_item0","component":"Row","children":["earphone_summary_item0_label","earphone_summary_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"earphone_summary_row0","component":"Row","children":["earphone_summary_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"earphone_summary_item1_label","component":"Text","content":"耳机仓 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"earphone_summary_item1_value","component":"Text","content":"{{ ${/data/earphone/batteryLevel} + '%' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"earphone_summary_item1","component":"Row","children":["earphone_summary_item1_label","earphone_summary_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"earphone_summary_row1","component":"Row","children":["earphone_summary_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["meeting_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"meeting_action","component":"Stack","children":["meeting_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"EnterMeeting","bundleName":"","abilityName":"","uri":"{{ ${/data/calendar/events/0/oneClickServiceLink} }}"}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#338C4B1C","alignContent":"center","clip":true}},{"id":"meeting_action_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"dtStart":"14:00","oneClickServiceLink":""}]},"earphone":{"isConnected":true,"batteryLevel":80}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "下午三点有合作方线上评审会，日程中有可用的入会链接，帮我做个卡片，看会议开始时间、耳机是否连接和耳机仓电量，点击按钮一键入会。",
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
            "dtStart": {
              "type": "string",
              "description": "格式化后的日程开始时间短文本，如 '03:00'，若为全天日程可能为特殊标记。",
              "sampleValue": "14:00"
            },
            "oneClickServiceType": {
              "type": "string",
              "description": "绑定的轻服务类型名称。大模型生成一键服务按钮时，应按照端侧能力声明的枚举选择文案。",
              "sampleValue": "Meeting"
            },
            "oneClickServiceLink": {
              "type": "string",
              "description": "一键直达的 URI 深度跳转链接，UI 卡片可直接通过此链接拉起第三方 App 落地页。",
              "sampleValue": ""
            },
            "isServiceValid": {
              "type": "integer",
              "description": "跳转服务连接是否有效。1代表存在有效跳转链接，0代表没有。",
              "sampleValue": 0
            }
          }
        ]
      },
      "earphone": {
        "isConnected": {
          "type": "boolean",
          "description": "当前是否有蓝牙耳机处于连接活跃状态。",
          "sampleValue": true
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
      "id": "asset.icon_meeting",
      "src": "resources/base/media/icon_meeting.svg",
      "description": "样式：默认白色的单色线面结合会议演示板图标，画板内有两条横线，原始尺寸为 14×14，支持通过 fillColor 与卡片配色统一；适用：会议、汇报、演示、议程。"
    },
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
    "GetCalendarEvents",
    "GetEarphoneInfo"
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
    "asset.icon_earphone",
    "asset.earphone_case_16644",
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
        "/events/0/dtStart",
        "/events/0/oneClickServiceType",
        "/events/0/oneClickServiceLink",
        "/events/0/isServiceValid"
      ]
    },
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/isConnected",
        "/batteryLevel"
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
    "asset.icon_earphone",
    "asset.earphone_case_16644",
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
  "artifactId": "c8b470b3-9baf-444e-ae4b-97a6ce01987f",
  "createdAt": 1792045402119
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["title_area","start_time","earphone_summary","meeting_action"]]
["title_area","SingleLineTitle",{"title":"线上评审","icon":"resources/base/media/clock_fill.svg","fontSize":12}]
["start_time","EmphasisText",{"mainText":"{{ '会议开始 ' + ${/data/calendar/events/0/dtStart} }}","fontSize":18}]
["earphone_summary","SecondaryBody",{"items":[{"label":"耳机 ","value":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}"},{"label":"耳机仓 ","value":"{{ ${/data/earphone/batteryLevel} + '%' }}"}],"columns":1,"fontSize":12}]
["meeting_action","CircleButton",{"icon":"resources/base/media/icon_meeting.svg","accessibility":{"label":"一键入会"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"EnterMeeting","bundleName":"","abilityName":"","uri":"{{ ${/data/calendar/events/0/oneClickServiceLink} }}"}}]}]
["/data/calendar/events/0/dtStart","14:00"]
["/data/calendar/events/0/oneClickServiceLink",""]
["/data/earphone/isConnected",true]
["/data/earphone/batteryLevel",80]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "下午三点有合作方线上评审会，日程中有可用的入会链接，帮我做个卡片，看会议开始时间、耳机是否连接和耳机仓电量，点击按钮一键入会。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 1
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/dtStart",
          "/events/0/oneClickServiceType",
          "/events/0/oneClickServiceLink",
          "/events/0/isServiceValid"
        ]
      },
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/isConnected",
          "/batteryLevel"
        ]
      }
    ],
    "title": "线上评审",
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
    "description": "会议和耳机状态",
    "candidateAssetIds": [
      "asset.icon_meeting",
      "asset.icon_earphone",
      "asset.earphone_case_16644",
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
    "interactionId": "013",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "下午三点有合作方线上评审会，日程中有可用的入会链接，帮我做个卡片，看会议开始时间、耳机是否连接和耳机仓电量，点击按钮一键入会。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "下午三点有合作方线上评审会，日程中有可用的入会链接，帮我做个卡片，看会议开始时间、耳机是否连接和耳机仓电量，点击按钮一键入会。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/dtStart",
        "/events/0/oneClickServiceType",
        "/events/0/oneClickServiceLink",
        "/events/0/isServiceValid"
      ]
    },
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/isConnected",
        "/batteryLevel"
      ]
    }
  ],
  "title": "线上评审",
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
  "description": "会议和耳机状态",
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.icon_earphone",
    "asset.earphone_case_16644",
    "asset.clock_fill"
  ]
}
```
