```cardspec
{
  "title": "近期日程清点",
  "description": "日程总数+最近日程详情",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","content_flow","action"],"itemMargin":2,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title"],"itemMargin":0,"styles":{"width":"matchParent","height":12,"flexShrink":0,"justifyContent":"start","alignItems":"center"}},{"id":"header_title","component":"Text","content":"未来7天日程","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":0,"width":"matchParent","fontColor":"#998C4B1C"}},{"id":"content_flow","component":"Column","children":["summary","event_meta"],"itemMargin":0,"styles":{"width":"matchParent","layoutWeight":1,"alignItems":"start","justifyContent":"start"}},{"id":"summary","component":"Column","children":["summary_main","summary_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"summary_main","component":"Text","content":"{{ '共 ' + ${/data/calendar/eventCount} + ' 件事' }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"summary_secondary","component":"Text","content":"{{ ${/data/calendar/events/0/title} }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"event_meta","component":"Column","children":["event_meta_row0","event_meta_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"event_meta_item0_label","component":"Text","content":"开始时间 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"event_meta_item0_value","component":"Text","content":"{{ ${/data/calendar/events/0/dtStart} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"event_meta_item0","component":"Row","children":["event_meta_item0_label","event_meta_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"event_meta_row0","component":"Row","children":["event_meta_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"event_meta_item1_label","component":"Text","content":"备注 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"event_meta_item1_value","component":"Text","content":"{{ ${/data/calendar/events/0/description} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"event_meta_item1","component":"Row","children":["event_meta_item1_label","event_meta_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"event_meta_row1","component":"Row","children":["event_meta_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToIntent","args":{"intentName":"ViewCalendarEvent","params":{"entityId":"{{ ${/data/calendar/events/0/entityId} }}"}}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#338C4B1C","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/calendar_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"action_text","component":"Text","content":"查看详情","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"eventCount":1,"events":[{"title":"项目例会","dtStart":"14:00","description":"周例会","entityId":"example-event-001"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个日程卡片，看看未来7天一共安排了几件事和最近一件的标题、开始时间、备注，点一下进日程详情。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.viewCalendarEvent",
      "description": "点击日程卡片 or 日程按钮，跳转到日程 App 查看该日程的详情",
      "call": "clickToIntent",
      "args": {
        "intentName": "ViewCalendarEvent",
        "params": {
          "entityId": "{{ ${/data/calendar/events/0/entityId} }}"
        }
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "calendar": {
        "eventCount": {
          "type": "integer",
          "description": "查询到的日程记录总数量。",
          "sampleValue": 1
        },
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
            "description": {
              "type": "string",
              "description": "日程的备注、摘要或补充叙述文本。",
              "sampleValue": "周例会"
            },
            "entityId": {
              "type": "string",
              "description": "系统日程的全局唯一实体ID。",
              "sampleValue": "example-event-001"
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
      "id": "event.viewCalendarEvent",
      "description": "点击日程卡片 or 日程按钮，跳转到日程 App 查看该日程的详情",
      "call": "clickToIntent",
      "args": {
        "intentName": "ViewCalendarEvent",
        "params": {
          "entityId": "{{ ${/data/calendar/events/0/entityId} }}"
        }
      }
    }
  ],
  "asset": [
    "asset.calendar_fill",
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
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/eventCount",
        "/events/0/title",
        "/events/0/dtStart",
        "/events/0/description",
        "/events/0/entityId"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.viewCalendarEvent",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "ViewCalendarEvent",
          "params": {
            "entityId": "{{ ${/data/calendar/events/0/entityId} }}"
          }
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.calendar_fill",
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
  "artifactId": "53521cad-a6ae-492e-8150-fdf6f5cd8d80",
  "createdAt": 1792045517365
}
```
```designcompactdsl
["root","Column",{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"itemMargin":2,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","content_flow","action"]]
["header","SingleLineTitle",{"title":"未来7天日程","fontSize":12,"width":"matchParent"}]
["content_flow","Column",{"width":"matchParent","layoutWeight":1,"itemMargin":0,"alignItems":"start","justifyContent":"start"},["summary","event_meta"]]
["summary","EmphasisText",{"mainText":"{{ '共 ' + ${/data/calendar/eventCount} + ' 件事' }}","secondaryText":{"path":"/data/calendar/events/0/title"},"fontSize":18,"width":"matchParent"}]
["event_meta","SecondaryBody",{"items":[{"label":"开始时间 ","value":{"path":"/data/calendar/events/0/dtStart"}},{"label":"备注 ","value":{"path":"/data/calendar/events/0/description"}}],"columns":2,"fontSize":14,"width":"matchParent"}]
["action","PillButton",{"label":"查看详情","icon":"resources/base/media/calendar_fill.svg","onClick":[{"call":"clickToIntent","args":{"intentName":"ViewCalendarEvent","params":{"entityId":"{{ ${/data/calendar/events/0/entityId} }}"}}}]}]
["/data/calendar/eventCount",1]
["/data/calendar/events/0/title","项目例会"]
["/data/calendar/events/0/dtStart","14:00"]
["/data/calendar/events/0/description","周例会"]
["/data/calendar/events/0/entityId","example-event-001"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个日程卡片，看看未来7天一共安排了几件事和最近一件的标题、开始时间、备注，点一下进日程详情。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 7
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/eventCount",
          "/events/0/title",
          "/events/0/dtStart",
          "/events/0/description",
          "/events/0/entityId"
        ]
      }
    ],
    "title": "近期日程清点",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.viewCalendarEvent",
        "action": {
          "call": "clickToIntent",
          "args": {
            "intentName": "ViewCalendarEvent",
            "params": {
              "entityId": "{{ ${/data/calendar/events/0/entityId} }}"
            }
          }
        }
      }
    ],
    "description": "日程总数+最近日程详情",
    "candidateAssetIds": [
      "asset.calendar_fill",
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
    "interactionId": "035",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个日程卡片，看看未来7天一共安排了几件事和最近一件的标题、开始时间、备注，点一下进日程详情。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个日程卡片，看看未来7天一共安排了几件事和最近一件的标题、开始时间、备注，点一下进日程详情。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/eventCount",
        "/events/0/title",
        "/events/0/dtStart",
        "/events/0/description",
        "/events/0/entityId"
      ]
    }
  ],
  "title": "近期日程清点",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.viewCalendarEvent",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "ViewCalendarEvent",
          "params": {
            "entityId": "{{ ${/data/calendar/events/0/entityId} }}"
          }
        }
      }
    }
  ],
  "description": "日程总数+最近日程详情",
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.clock_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"content\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"未来7天日程\",\"icon\":\"resources/base/media/clock_fill.svg\",\"fontSize\":12}]\n[\"content\",\"Group\",{\"variant\":\"supporting-items\"},[\"summary\",\"event_title\",\"event_meta\"]]\n[\"summary\",\"EmphasisText\",{\"mainText\":\"{{ '共 ' + ${/data/calendar/eventCount} + ' 件事' }}\",\"fontSize\":18}]\n[\"event_title\",\"EmphasisText\",{\"mainText\":{\"path\":\"/data/calendar/events/0/title\"},\"fontSize\":18}]\n[\"event_meta\",\"SecondaryBody\",{\"items\":[{\"label\":\"开始时间 \",\"value\":{\"path\":\"/data/calendar/events/0/dtStart\"}},{\"label\":\"备注 \",\"value\":{\"path\":\"/data/calendar/events/0/description\"}}],\"columns\":2,\"fontSize\":14}]\n[\"action\",\"PillButton\",{\"label\":\"查看详情\",\"icon\":\"resources/base/media/calendar_fill.svg\",\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"ViewCalendarEvent\",\"params\":{\"entityId\":\"{{ ${/data/calendar/events/0/entityId} }}\"}}}]}]\n[\"/data/calendar/eventCount\",1]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/dtStart\",\"14:00\"]\n[\"/data/calendar/events/0/description\",\"周例会\"]\n[\"/data/calendar/events/0/entityId\",\"example-event-001\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 156vp within 126vp; it overflows by 30vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=130vp+margin(0vp), gaps=6vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 156vp within 126vp; it overflows by 30vp. Occupancy: header=20vp+margin(0vp), __layout__root__body=130vp+margin(0vp), gaps=6vp.",
          "legacyMessage": "component root: vertical layout requires at least 156vp within 126vp; it overflows by 30vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=130vp+margin(0vp), gaps=6vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 156.0,
            "overflow": 30.0,
            "occupancy": "header=20vp+margin(0vp), __layout__root__body=130vp+margin(0vp), gaps=6vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__body: vertical layout requires at least 130vp within 100vp; it overflows by 30vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__content=86vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 130vp within 100vp; it overflows by 30vp. Occupancy: __layout__root__content=86vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 130vp within 100vp; it overflows by 30vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__content=86vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 100.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 130.0,
            "overflow": 30.0,
            "occupancy": "__layout__root__content=86vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__content: vertical layout requires at least 86vp within 56vp; it overflows by 30vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: content=86vp+margin(0vp), gaps=0vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__content: vertical layout requires at least 86vp within 56vp; it overflows by 30vp. Occupancy: content=86vp+margin(0vp), gaps=0vp.",
          "legacyMessage": "component __layout__root__content: vertical layout requires at least 86vp within 56vp; it overflows by 30vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: content=86vp+margin(0vp), gaps=0vp.",
          "expected": {
            "maximumHeight": 56.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 86.0,
            "overflow": 30.0,
            "occupancy": "content=86vp+margin(0vp), gaps=0vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"summary\",\"event_meta\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"未来7天日程\",\"icon\":\"resources/base/media/clock_fill.svg\",\"fontSize\":12}]\n[\"summary\",\"EmphasisText\",{\"mainText\":\"{{ '共 ' + ${/data/calendar/eventCount} + ' 件事 · ' + ${/data/calendar/events/0/title} }}\",\"fontSize\":18}]\n[\"event_meta\",\"SecondaryBody\",{\"items\":[{\"label\":\"开始时间 \",\"value\":{\"path\":\"/data/calendar/events/0/dtStart\"}},{\"label\":\"备注 \",\"value\":{\"path\":\"/data/calendar/events/0/description\"}}],\"columns\":2,\"fontSize\":14}]\n[\"action\",\"PillButton\",{\"label\":\"查看详情\",\"icon\":\"resources/base/media/calendar_fill.svg\",\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"ViewCalendarEvent\",\"params\":{\"entityId\":\"{{ ${/data/calendar/events/0/entityId} }}\"}}}]}]\n[\"/data/calendar/eventCount\",1]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/dtStart\",\"14:00\"]\n[\"/data/calendar/events/0/description\",\"周例会\"]\n[\"/data/calendar/events/0/entityId\",\"example-event-001\"]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 130vp within 126vp; it overflows by 4vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=104vp+margin(0vp), gaps=6vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 130vp within 126vp; it overflows by 4vp. Occupancy: header=20vp+margin(0vp), __layout__root__body=104vp+margin(0vp), gaps=6vp.",
          "legacyMessage": "component root: vertical layout requires at least 130vp within 126vp; it overflows by 4vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: header=20vp+margin(0vp), __layout__root__body=104vp+margin(0vp), gaps=6vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 130.0,
            "overflow": 4.0,
            "occupancy": "header=20vp+margin(0vp), __layout__root__body=104vp+margin(0vp), gaps=6vp",
            "removableTitleIcon": {
              "componentId": "header",
              "heightSaving": 8.0
            }
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__body: vertical layout requires at least 104vp within 100vp; it overflows by 4vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=60vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 104vp within 100vp; it overflows by 4vp. Occupancy: __layout__root__primary_support=60vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 104vp within 100vp; it overflows by 4vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=60vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 100.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 104.0,
            "overflow": 4.0,
            "occupancy": "__layout__root__primary_support=60vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__primary_support: vertical layout requires at least 60vp within 56vp; it overflows by 4vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: summary=24vp+margin(0vp), event_meta=34vp+margin(0vp), gaps=2vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__primary_support: vertical layout requires at least 60vp within 56vp; it overflows by 4vp. Occupancy: summary=24vp+margin(0vp), event_meta=34vp+margin(0vp), gaps=2vp.",
          "legacyMessage": "component __layout__root__primary_support: vertical layout requires at least 60vp within 56vp; it overflows by 4vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: summary=24vp+margin(0vp), event_meta=34vp+margin(0vp), gaps=2vp.",
          "expected": {
            "maximumHeight": 56.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 60.0,
            "overflow": 4.0,
            "occupancy": "summary=24vp+margin(0vp), event_meta=34vp+margin(0vp), gaps=2vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component summary_main: text width overflow; complete text '共 1 件事 · 项目例会' at original font 18 needs about 189vp in one line, but its allocated text area is 126vp. Keep every label, prefix, value and action; use legal lines at the same font or regroup into a wider region. A fixed single-line component needs same-font separate lines or a different legal composition, not clipping, smaller secondary text or weight."
    }
  ]
}
```
```repair-3
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"summary\",\"event_meta\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"未来7天日程\",\"fontSize\":12}]\n[\"summary\",\"EmphasisText\",{\"mainText\":\"{{ '共 ' + ${/data/calendar/eventCount} + ' 件事' }}\",\"secondaryText\":{\"path\":\"/data/calendar/events/0/title\"},\"fontSize\":18}]\n[\"event_meta\",\"SecondaryBody\",{\"items\":[{\"label\":\"开始时间 \",\"value\":{\"path\":\"/data/calendar/events/0/dtStart\"}},{\"label\":\"备注 \",\"value\":{\"path\":\"/data/calendar/events/0/description\"}}],\"columns\":2,\"fontSize\":14}]\n[\"action\",\"PillButton\",{\"label\":\"查看详情\",\"icon\":\"resources/base/media/calendar_fill.svg\",\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"ViewCalendarEvent\",\"params\":{\"entityId\":\"{{ ${/data/calendar/events/0/entityId} }}\"}}}]}]\n[\"/data/calendar/eventCount\",1]\n[\"/data/calendar/events/0/title\",\"项目例会\"]\n[\"/data/calendar/events/0/dtStart\",\"14:00\"]\n[\"/data/calendar/events/0/description\",\"周例会\"]\n[\"/data/calendar/events/0/entityId\",\"example-event-001\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"content_flow\",\"action\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":12,\"flexShrink\":0,\"justifyContent\":\"start\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"未来7天日程\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":0,\"width\":\"matchParent\",\"fontColor\":\"#998C4B1C\"}},{\"id\":\"content_flow\",\"component\":\"Column\",\"children\":[\"summary\",\"event_meta\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"layoutWeight\":1,\"alignItems\":\"start\",\"justifyContent\":\"start\"}},{\"id\":\"summary\",\"component\":\"Column\",\"children\":[\"summary_main\",\"summary_secondary\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"summary_main\",\"component\":\"Text\",\"content\":\"{{ '共 ' + ${/data/calendar/eventCount} + ' 件事' }}\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"summary_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/title} }}\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#998C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"event_meta\",\"component\":\"Column\",\"children\":[\"event_meta_row0\",\"event_meta_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"event_meta_item0_label\",\"component\":\"Text\",\"content\":\"开始时间 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"event_meta_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/dtStart} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"event_meta_item0\",\"component\":\"Row\",\"children\":[\"event_meta_item0_label\",\"event_meta_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"event_meta_row0\",\"component\":\"Row\",\"children\":[\"event_meta_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"event_meta_item1_label\",\"component\":\"Text\",\"content\":\"备注 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"event_meta_item1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/calendar/events/0/description} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"event_meta_item1\",\"component\":\"Row\",\"children\":[\"event_meta_item1_label\",\"event_meta_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"event_meta_row1\",\"component\":\"Row\",\"children\":[\"event_meta_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"action\",\"component\":\"Row\",\"children\":[\"action_icon\",\"action_text\"],\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"ViewCalendarEvent\",\"params\":{\"entityId\":\"{{ ${/data/calendar/events/0/entityId} }}\"}}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#338C4B1C\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"action_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/calendar_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"action_text\",\"component\":\"Text\",\"content\":\"查看详情\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"calendar\":{\"eventCount\":1,\"events\":[{\"title\":\"项目例会\",\"dtStart\":\"14:00\",\"description\":\"周例会\",\"entityId\":\"example-event-001\"}]}}}}}",
  "validationErrors": []
}
```
