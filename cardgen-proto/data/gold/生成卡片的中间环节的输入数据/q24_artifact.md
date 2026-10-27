```cardspec
{
  "title": "评审会议",
  "description": "会议提醒和勿扰",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","content_flow","cta"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"下一场日程","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"content_flow","component":"Column","children":["primary","support"],"itemMargin":2,"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"start"}},{"id":"primary","component":"Column","children":["primary_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"primary_main","component":"Text","content":"{{ '发起人 ' + ${/data/calendar/events/0/senderName} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"support","component":"Column","children":["support_row0","support_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"support_item0_label","component":"Text","content":"重要日程 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"support_item0_value","component":"Text","content":"{{ ${/data/calendar/events/0/importantEventType} == 1 ? '是' : '否' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"support_item0","component":"Row","children":["support_item0_label","support_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"support_row0","component":"Row","children":["support_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"support_item1_label","component":"Text","content":"提前提醒 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"support_item1_value","component":"Text","content":"{{ ${/data/calendar/events/0/remindTime/0} + '分钟' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"support_item1","component":"Row","children":["support_item1_label","support_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"support_row1","component":"Row","children":["support_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"cta","component":"Row","children":["cta_icon","cta_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"intelligent_scene_entry"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#338C4B1C","justifyContent":"center","alignItems":"center"}},{"id":"cta_icon","component":"Image","src":"resources/base/media/bell_slash_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"cta_text","component":"Text","content":"免打扰设置","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"senderName":"李四","importantEventType":1,"remindTime":["15"]}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "下一场日程是李四发起的下午两点需求评审会，帮我做个卡片，看会议发起人、是不是重要日程、提前提醒时间，开会前可以打开免打扰设置。",
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
            "senderName": {
              "type": "string",
              "description": "日程数据标识符或发起方标识（如邀请人），若无则为空字符串。",
              "sampleValue": ""
            },
            "importantEventType": {
              "type": "integer",
              "description": "日程事件的重要程度或分类枚举值（Type）。",
              "sampleValue": 0
            },
            "remindTime": [
              {
                "type": "string",
                "description": "提前提醒分钟数（字符串形式）。",
                "sampleValue": "15"
              }
            ]
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
      "id": "asset.bell_fill",
      "src": "resources/base/media/bell_fill.svg",
      "description": "样式：默认黑色的单色实心铃铛图标，采用经典吊铃造型，底部带铃舌，原始尺寸为 24×24；适用：通知提醒、消息提示、备忘录提醒、闹钟响铃或开启状态，以及日历事项提醒。"
    },
    {
      "id": "asset.bell_slash_fill",
      "src": "resources/base/media/bell_slash_fill.svg",
      "description": "样式：默认黑色的单色铃铛加斜杠实心图标，内部通过镂空表现细节，支持通过 fillColor 与卡片配色统一；适用：静音模式、关闭通知、勿扰设置。"
    },
    {
      "id": "asset.clock",
      "src": "resources/base/media/clock.svg",
      "description": "样式：时钟线框图标，默认黑色，图形为圆形表盘加指针的线性轮廓；适用：时间显示、定时功能、倒计时。"
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
    "asset.bell_fill",
    "asset.bell_slash_fill",
    "asset.clock"
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
        "/events/0/senderName",
        "/events/0/importantEventType",
        "/events/0/remindTime/0"
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
    "asset.bell_fill",
    "asset.bell_slash_fill",
    "asset.clock"
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
  "artifactId": "576361b4-8d68-4065-b01c-2ac75e1aebc3",
  "createdAt": 1792045463439
}
```
```designcompactdsl
["root","Column",{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"itemMargin":6,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","content_flow","cta"]]
["header","SingleLineTitle",{"title":"下一场日程","icon":"resources/base/media/icon_meeting.svg","fontSize":12,"width":"matchParent"}]
["content_flow","Column",{"width":"matchParent","layoutWeight":1,"itemMargin":2,"alignItems":"start","justifyContent":"start"},["primary","support"]]
["primary","EmphasisText",{"mainText":"{{ '发起人 ' + ${/data/calendar/events/0/senderName} }}","fontSize":18,"width":"matchParent"}]
["support","SecondaryBody",{"items":[{"label":"重要日程 ","value":"{{ ${/data/calendar/events/0/importantEventType} == 1 ? '是' : '否' }}"},{"label":"提前提醒 ","value":"{{ ${/data/calendar/events/0/remindTime/0} + '分钟' }}"}],"columns":1,"fontSize":12,"width":"matchParent"}]
["cta","PillButton",{"label":"免打扰设置","icon":"resources/base/media/bell_slash_fill.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Settings","bundleName":"com.huawei.hmos.settings","abilityName":"com.huawei.hmos.settings.MainAbility","uri":"intelligent_scene_entry"}}]}]
["/data/calendar/events/0/senderName","李四"]
["/data/calendar/events/0/importantEventType",1]
["/data/calendar/events/0/remindTime/0","15"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "下一场日程是李四发起的下午两点需求评审会，帮我做个卡片，看会议发起人、是不是重要日程、提前提醒时间，开会前可以打开免打扰设置。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 7
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/senderName",
          "/events/0/importantEventType",
          "/events/0/remindTime/0"
        ]
      }
    ],
    "title": "评审会议",
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
    "description": "会议提醒和勿扰",
    "candidateAssetIds": [
      "asset.icon_meeting",
      "asset.bell_fill",
      "asset.bell_slash_fill",
      "asset.clock"
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
    "interactionId": "024",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "下一场日程是李四发起的下午两点需求评审会，帮我做个卡片，看会议发起人、是不是重要日程、提前提醒时间，开会前可以打开免打扰设置。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "下一场日程是李四发起的下午两点需求评审会，帮我做个卡片，看会议发起人、是不是重要日程、提前提醒时间，开会前可以打开免打扰设置。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/senderName",
        "/events/0/importantEventType",
        "/events/0/remindTime/0"
      ]
    }
  ],
  "title": "评审会议",
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
  "description": "会议提醒和勿扰",
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.bell_fill",
    "asset.bell_slash_fill",
    "asset.clock"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"info\",\"cta\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"下一场日程\",\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"info\",\"EmphasisText\",{\"mainText\":\"{{ '发起人 ' + ${/data/calendar/events/0/senderName} }}\",\"secondaryText\":\"{{ '重要日程 ' + (${/data/calendar/events/0/importantEventType} == 1 ? '是' : '否') + ' | 提前提醒 ' + ${/data/calendar/events/0/remindTime/0} + '分钟' }}\",\"fontSize\":18}]\n[\"cta\",\"PillButton\",{\"label\":\"免打扰设置\",\"icon\":\"resources/base/media/bell_slash_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"intelligent_scene_entry\"}}]}]\n[\"/data/calendar/events/0/senderName\",\"李四\"]\n[\"/data/calendar/events/0/importantEventType\",1]\n[\"/data/calendar/events/0/remindTime/0\",\"15\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：子组件数量应为 [4]；要求的 children 角色为 [title, primary, support, PillButton]。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"primary\",\"support\",\"cta\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"下一场日程\",\"icon\":\"resources/base/media/icon_meeting.svg\",\"fontSize\":12}]\n[\"primary\",\"EmphasisText\",{\"mainText\":\"{{ '发起人 ' + ${/data/calendar/events/0/senderName} }}\",\"fontSize\":18}]\n[\"support\",\"SecondaryBody\",{\"items\":[{\"label\":\"重要日程 \",\"value\":\"{{ ${/data/calendar/events/0/importantEventType} == 1 ? '是' : '否' }}\"},{\"label\":\"提前提醒 \",\"value\":\"{{ ${/data/calendar/events/0/remindTime/0} + '分钟' }}\"}],\"columns\":1,\"fontSize\":12}]\n[\"cta\",\"PillButton\",{\"label\":\"免打扰设置\",\"icon\":\"resources/base/media/bell_slash_fill.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"intelligent_scene_entry\"}}]}]\n[\"/data/calendar/events/0/senderName\",\"李四\"]\n[\"/data/calendar/events/0/importantEventType\",1]\n[\"/data/calendar/events/0/remindTime/0\",\"15\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"content_flow\",\"cta\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"下一场日程\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#998C4B1C\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/icon_meeting.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"content_flow\",\"component\":\"Column\",\"children\":[\"primary\",\"support\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"layoutWeight\":1,\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"primary\",\"component\":\"Column\",\"children\":[\"primary_main\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"primary_main\",\"component\":\"Text\",\"content\":\"{{ '发起人 ' + ${/data/calendar/events/0/senderName} }}\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"support\",\"component\":\"Column\",\"children\":[\"support_row0\",\"support_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"support_item0_label\",\"component\":\"Text\",\"content\":\"重要日程 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"support_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/importantEventType} == 1 ? '是' : '否' }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"support_item0\",\"component\":\"Row\",\"children\":[\"support_item0_label\",\"support_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"support_row0\",\"component\":\"Row\",\"children\":[\"support_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"support_item1_label\",\"component\":\"Text\",\"content\":\"提前提醒 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"support_item1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/remindTime/0} + '分钟' }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"support_item1\",\"component\":\"Row\",\"children\":[\"support_item1_label\",\"support_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"support_row1\",\"component\":\"Row\",\"children\":[\"support_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"cta\",\"component\":\"Row\",\"children\":[\"cta_icon\",\"cta_text\"],\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Settings\",\"bundleName\":\"com.huawei.hmos.settings\",\"abilityName\":\"com.huawei.hmos.settings.MainAbility\",\"uri\":\"intelligent_scene_entry\"}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#338C4B1C\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"cta_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/bell_slash_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"cta_text\",\"component\":\"Text\",\"content\":\"免打扰设置\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"calendar\":{\"events\":[{\"senderName\":\"李四\",\"importantEventType\":1,\"remindTime\":[\"15\"]}]}}}}}",
  "validationErrors": []
}
```
