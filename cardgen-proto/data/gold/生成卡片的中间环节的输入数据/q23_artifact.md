```cardspec
{
  "title": "全球周会",
  "description": "会议日期和时区",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__content"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__content","component":"Column","children":["content"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"content","component":"Column","children":["summary","details"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start"}},{"id":"summary","component":"Column","children":["summary_main","summary_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"summary_main","component":"Text","content":"{{ ${/data/calendar/events/0/startDate} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"summary_secondary","component":"Text","content":"{{ ${/data/calendar/events/0/dtEnd} }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"details","component":"Column","children":["details_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"details_item0_label","component":"Text","content":"时区 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"details_item0_value","component":"Text","content":"{{ ${/data/calendar/events/0/timeZone} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"details_item0","component":"Row","children":["details_item0_label","details_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"details_row0","component":"Row","children":["details_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"title":"项目例会","startDate":"08-06","dtEnd":"15:00","timeZone":"Asia/Shanghai"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "下周一上午九点有一个全球项目周会，帮我做个卡片，看会议标题、会议日期、结束时间和所在时区。",
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
            "startDate": {
              "type": "string",
              "description": "日程开始日期格式化文本，例如 '07-03'。",
              "sampleValue": "08-06"
            },
            "dtEnd": {
              "type": "string",
              "description": "格式化后的日程结束时间短文本，如 '05:00'。",
              "sampleValue": "15:00"
            },
            "timeZone": {
              "type": "string",
              "description": "日程所处的时区标识，例如 'Asia/Shanghai'。",
              "sampleValue": "Asia/Shanghai"
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
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/title",
        "/events/0/startDate",
        "/events/0/dtEnd",
        "/events/0/timeZone"
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
  "artifactId": "36ebcffe-044c-42c3-a539-034356127149",
  "createdAt": 1792045455953
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","content"]]
["header","SingleLineTitle",{"title":{"path":"/data/calendar/events/0/title"},"icon":"resources/base/media/icon_meeting.svg","fontSize":12}]
["content","Group",{"variant":"hero-support"},["summary","details"]]
["summary","EmphasisText",{"mainText":{"path":"/data/calendar/events/0/startDate"},"secondaryText":{"path":"/data/calendar/events/0/dtEnd"},"fontSize":18}]
["details","SecondaryBody",{"items":[{"label":"时区 ","value":{"path":"/data/calendar/events/0/timeZone"}}],"columns":1,"fontSize":14}]
["/data/calendar/events/0/title","项目例会"]
["/data/calendar/events/0/startDate","08-06"]
["/data/calendar/events/0/dtEnd","15:00"]
["/data/calendar/events/0/timeZone","Asia/Shanghai"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "下周一上午九点有一个全球项目周会，帮我做个卡片，看会议标题、会议日期、结束时间和所在时区。",
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
          "/events/0/dtEnd",
          "/events/0/timeZone"
        ]
      }
    ],
    "title": "全球周会",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "会议日期和时区",
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
    "interactionId": "023",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "下一场日程是下周一上午九点的全球项目周会，帮我做个卡片，看会议标题、会议日期、结束时间和所在时区。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "下一场日程是下周一上午九点的全球项目周会，帮我做个卡片，看会议标题、会议日期、结束时间和所在时区。",
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
        "/events/0/dtEnd",
        "/events/0/timeZone"
      ]
    }
  ],
  "title": "全球周会",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "会议日期和时区",
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.clock_fill",
    "asset.icon_meeting"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"summary\",\"details\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/calendar/events/0/title\"},\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"summary\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/calendar/events/0/startDate\"},\"secondaryText\":{\"path\":\"/data/calendar/events/0/dtEnd\"},\"fontSize\":18}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"时区 \",\"value\":{\"path\":\"/data/calendar/events/0/timeZone\"}}],\"columns\":1,\"fontSize\":14}]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/startDate\",\"08-06\"]\n[\"/data/calendar/events/0/dtEnd\",\"15:00\"]\n[\"/data/calendar/events/0/timeZone\",\"Asia/Shanghai\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：子组件数量应为 [2]；要求的 children 角色为 [title, content]。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"content\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":{\"path\":\"/data/calendar/events/0/title\"},\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"content\",\"Group\",{\"variant\":\"hero-support\"},[\"summary\",\"details\"]]\n[\"summary\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/calendar/events/0/startDate\"},\"secondaryText\":{\"path\":\"/data/calendar/events/0/dtEnd\"},\"fontSize\":18}]\n[\"details\",\"SecondaryBody\",{\"items\":[{\"label\":\"时区 \",\"value\":{\"path\":\"/data/calendar/events/0/timeZone\"}}],\"columns\":1,\"fontSize\":14}]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/startDate\",\"08-06\"]\n[\"/data/calendar/events/0/dtEnd\",\"15:00\"]\n[\"/data/calendar/events/0/timeZone\",\"Asia/Shanghai\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__content\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/title} }}\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#998C4B1C\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/icon_meeting.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"content\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"end\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"content\",\"component\":\"Column\",\"children\":[\"summary\",\"details\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"summary\",\"component\":\"Column\",\"children\":[\"summary_main\",\"summary_secondary\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"summary_main\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/startDate} }}\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"summary_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/dtEnd} }}\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#998C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"details\",\"component\":\"Column\",\"children\":[\"details_row0\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"details_item0_label\",\"component\":\"Text\",\"content\":\"时区 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"details_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/timeZone} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"details_item0\",\"component\":\"Row\",\"children\":[\"details_item0_label\",\"details_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"details_row0\",\"component\":\"Row\",\"children\":[\"details_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"calendar\":{\"events\":[{\"title\":\"项目例会\",\"startDate\":\"08-06\",\"dtEnd\":\"15:00\",\"timeZone\":\"Asia/Shanghai\"}]}}}}}",
  "validationErrors": []
}
```
