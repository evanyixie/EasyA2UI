```cardspec
{
  "title": "日程详情",
  "description": "时区+全天+地址",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__content"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__content","component":"Column","children":["content"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"content","component":"Column","children":["timezone","allday","location"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start"}},{"id":"timezone","component":"Column","children":["timezone_main","timezone_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"timezone_main","component":"Text","content":"时区","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"timezone_secondary","component":"Text","content":"{{ ${/data/calendar/events/0/timeZone} }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"allday","component":"Column","children":["allday_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"allday_item0_label","component":"Text","content":"全天 ","styles":{"height":19,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3571428571428572,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"allday_item0_value","component":"Text","content":"{{ ${/data/calendar/events/0/isAllDay} ? '是' : '否' }}","styles":{"height":19.0,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3571428571428572,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"allday_item0","component":"Row","children":["allday_item0_label","allday_item0_value"],"itemMargin":0,"styles":{"height":19.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"allday_row0","component":"Row","children":["allday_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":19.0,"alignItems":"top","flexShrink":0}},{"id":"location","component":"Column","children":["location_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"location_item0_label","component":"Text","content":"地点 ","styles":{"height":19,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3571428571428572,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"location_item0_value","component":"Text","content":"{{ ${/data/calendar/events/0/eventLocation} }}","styles":{"height":19.0,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3571428571428572,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"location_item0","component":"Row","children":["location_item0_label","location_item0_value"],"itemMargin":0,"styles":{"height":19.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"location_row0","component":"Row","children":["location_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":19.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"title":"项目例会","timeZone":"Asia/Shanghai","isAllDay":false,"eventLocation":"会议室"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个日程卡片，下周一要和美国团队开会，展示标题、时区、是不是全天、开会地点。",
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
            "timeZone": {
              "type": "string",
              "description": "日程所处的时区标识，例如 'Asia/Shanghai'。",
              "sampleValue": "Asia/Shanghai"
            },
            "isAllDay": {
              "type": "boolean",
              "description": "标识该日程是否为全天日程。",
              "sampleValue": false
            },
            "eventLocation": {
              "type": "string",
              "description": "日程的具体地点描述，若未填写则为空字符串。",
              "sampleValue": "会议室"
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
      "id": "asset.clock_fill",
      "src": "resources/base/media/clock_fill.svg",
      "description": "样式：默认黑色的单色实心圆形时钟图标，内部通过镂空表现表盘指针，原始尺寸为 24×24，支持通过 fillColor 与卡片配色统一；适用：时间显示、闹钟设置、定时器、提醒时间、应用使用时长与运动时长。"
    },
    {
      "id": "asset.local_fill",
      "src": "resources/base/media/local_fill.svg",
      "description": "样式：默认黑色的单色实心地图定位针，中央为圆形留白；适用：当前位置、地点、地图标记、位置服务。"
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
    "asset.icon_meeting",
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.local_fill"
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
        "/events/0/timeZone",
        "/events/0/isAllDay",
        "/events/0/eventLocation"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.local_fill"
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
  "artifactId": "729547b9-c158-46ce-a52b-de9658a8490b",
  "createdAt": 1792045561513
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","content"]]
["header","SingleLineTitle",{"title":{"path":"/data/calendar/events/0/title"},"icon":"resources/base/media/icon_meeting.svg","fontSize":12}]
["content","Group",{"variant":"supporting-items"},["timezone","allday","location"]]
["timezone","EmphasisText",{"mainText":"时区","secondaryText":{"path":"/data/calendar/events/0/timeZone"},"fontSize":18}]
["allday","SecondaryBody",{"items":[{"label":"全天 ","value":"{{ ${/data/calendar/events/0/isAllDay} ? '是' : '否' }}"}],"fontSize":14}]
["location","SecondaryBody",{"items":[{"label":"地点 ","value":{"path":"/data/calendar/events/0/eventLocation"}}],"fontSize":14}]
["/data/calendar/events/0/title","项目例会"]
["/data/calendar/events/0/timeZone","Asia/Shanghai"]
["/data/calendar/events/0/isAllDay",false]
["/data/calendar/events/0/eventLocation","会议室"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个日程卡片，下周一要和美国团队开会，展示标题、时区、是不是全天、开会地点。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 7
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/title",
          "/events/0/timeZone",
          "/events/0/isAllDay",
          "/events/0/eventLocation"
        ]
      }
    ],
    "title": "日程详情",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "时区+全天+地址",
    "candidateAssetIds": [
      "asset.icon_meeting",
      "asset.calendar_fill",
      "asset.clock_fill",
      "asset.local_fill"
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
    "interactionId": "041",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个日程卡片，下周一要和美国团队开会，展示标题、时区、是不是全天、开会地点。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个日程卡片，下周一要和美国团队开会，展示标题、时区、是不是全天、开会地点。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/timeZone",
        "/events/0/isAllDay",
        "/events/0/eventLocation"
      ]
    }
  ],
  "title": "日程详情",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "时区+全天+地址",
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.local_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"primary\",\"support\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/calendar/events/0/title\"},\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"primary\",\"SecondaryBody\",{\"items\":[{\"label\":\"时区 \",\"value\":{\"path\":\"/data/calendar/events/0/timeZone\"},\"maxLines\":2}],\"columns\":1,\"fontSize\":12}]\n[\"support\",\"SecondaryBody\",{\"items\":[{\"label\":\"全天 \",\"value\":\"{{ ${/data/calendar/events/0/isAllDay} ? '是' : '否' }}\"},{\"label\":\"地点 \",\"value\":{\"path\":\"/data/calendar/events/0/eventLocation\"}}],\"columns\":1,\"fontSize\":12}]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/timeZone\",\"Asia/Shanghai\"]\n[\"/data/calendar/events/0/isAllDay\",false]\n[\"/data/calendar/events/0/eventLocation\",\"会议室\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component primary: SecondaryBody is auxiliary and cannot be the only information component in the card; pair it with a core information component somewhere in the card. Titles, buttons and other SecondaryBody instances do not count."
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component support: SecondaryBody is auxiliary and cannot be the only information component in the card; pair it with a core information component somewhere in the card. Titles, buttons and other SecondaryBody instances do not count."
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"primary\",\"support\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/calendar/events/0/title\"},\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"primary\",\"EmphasisText\",{\"mainText\":\"{{ '时区 ' + ${/data/calendar/events/0/timeZone} }}\",\"fontSize\":18}]\n[\"support\",\"SecondaryBody\",{\"items\":[{\"label\":\"全天 \",\"value\":\"{{ ${/data/calendar/events/0/isAllDay} ? '是' : '否' }}\"},{\"label\":\"地点 \",\"value\":{\"path\":\"/data/calendar/events/0/eventLocation\"}}],\"columns\":1,\"fontSize\":12}]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/timeZone\",\"Asia/Shanghai\"]\n[\"/data/calendar/events/0/isAllDay\",false]\n[\"/data/calendar/events/0/eventLocation\",\"会议室\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component primary_main: text width overflow; complete text '时区 Asia/Shanghai' at original font 18 needs about 162vp in one line, but its allocated text area is 126vp. Keep every label, prefix, value and action; use legal lines at the same font or regroup into a wider region. A fixed single-line component needs same-font separate lines or a different legal composition, not clipping, smaller secondary text or weight."
    }
  ]
}
```
```repair-3
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"content\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/calendar/events/0/title\"},\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"content\",\"Group\",{\"variant\":\"supporting-items\"},[\"timezone\",\"allday\",\"location\"]]\n[\"timezone\",\"EmphasisText\",{\"mainText\":\"时区\",\"secondaryText\":{\"path\":\"/data/calendar/events/0/timeZone\"},\"fontSize\":18}]\n[\"allday\",\"SecondaryBody\",{\"items\":[{\"label\":\"全天 \",\"value\":\"{{ ${/data/calendar/events/0/isAllDay} ? '是' : '否' }}\"}],\"fontSize\":14}]\n[\"location\",\"SecondaryBody\",{\"items\":[{\"label\":\"地点 \",\"value\":{\"path\":\"/data/calendar/events/0/eventLocation\"}}],\"fontSize\":14}]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/timeZone\",\"Asia/Shanghai\"]\n[\"/data/calendar/events/0/isAllDay\",false]\n[\"/data/calendar/events/0/eventLocation\",\"会议室\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__content\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/title} }}\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#998C4B1C\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/icon_meeting.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"content\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"end\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"content\",\"component\":\"Column\",\"children\":[\"timezone\",\"allday\",\"location\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"timezone\",\"component\":\"Column\",\"children\":[\"timezone_main\",\"timezone_secondary\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"timezone_main\",\"component\":\"Text\",\"content\":\"时区\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"timezone_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/timeZone} }}\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#998C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"allday\",\"component\":\"Column\",\"children\":[\"allday_row0\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"allday_item0_label\",\"component\":\"Text\",\"content\":\"全天 \",\"styles\":{\"height\":19,\"fontSize\":14,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3571428571428572,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"allday_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/isAllDay} ? '是' : '否' }}\",\"styles\":{\"height\":19.0,\"fontSize\":14,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3571428571428572,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"allday_item0\",\"component\":\"Row\",\"children\":[\"allday_item0_label\",\"allday_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":19.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"allday_row0\",\"component\":\"Row\",\"children\":[\"allday_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":19.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"location\",\"component\":\"Column\",\"children\":[\"location_row0\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"location_item0_label\",\"component\":\"Text\",\"content\":\"地点 \",\"styles\":{\"height\":19,\"fontSize\":14,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3571428571428572,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"location_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/eventLocation} }}\",\"styles\":{\"height\":19.0,\"fontSize\":14,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3571428571428572,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"location_item0\",\"component\":\"Row\",\"children\":[\"location_item0_label\",\"location_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":19.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"location_row0\",\"component\":\"Row\",\"children\":[\"location_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":19.0,\"alignItems\":\"top\",\"flexShrink\":0}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"calendar\":{\"events\":[{\"title\":\"项目例会\",\"timeZone\":\"Asia/Shanghai\",\"isAllDay\":false,\"eventLocation\":\"会议室\"}]}}}}}",
  "validationErrors": []
}
```
