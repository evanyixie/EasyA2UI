```cardspec
{
  "title": "发布排期",
  "description": "会议时间和导航",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"版本发布排期会","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/icon_meeting.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["meeting"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"meeting","component":"Column","children":["meeting_main","meeting_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"meeting_main","component":"Text","content":"{{ ${/data/calendar/events/0/dtStart} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"meeting_secondary","component":"Text","content":"{{ ${/data/calendar/events/0/eventLocation} }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#998C4B1C","textOverflow":"clip"}},{"id":"__layout__root__action","component":"Column","children":["navigate"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"navigate","component":"Row","children":["navigate_icon","navigate_text"],"onClick":[{"call":"clickToIntent","args":{"intentName":"StartNavigate","params":{"dstLocation":{"location":"company","latitude":"","longitude":""}}}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#338C4B1C","justifyContent":"center","alignItems":"center"}},{"id":"navigate_icon","component":"Image","src":"resources/base/media/location_north_up_right_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"navigate_text","component":"Text","content":"导航去公司","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"calendar":{"events":[{"dtStart":"15:00","eventLocation":"总部大楼"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "下一场日程是下午三点的版本发布排期会，帮我做个卡片，看会议开始时间和地点，点击导航去公司。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.startNavigate",
      "description": "点击导航按钮，跳转到地图应用进行导航。大模型需根据用户说的目的地选择location的值，只支持回家和去公司的导航",
      "call": "clickToIntent",
      "args": {
        "intentName": "StartNavigate",
        "params": {
          "dstLocation": {
            "location": "company",
            "latitude": "",
            "longitude": ""
          }
        }
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
      "id": "asset.location_north_up_right_fill",
      "src": "resources/base/media/location_north_up_right_fill.svg",
      "description": "样式：方向导航实心图标，默认黑色，图形为指向右上方的导航箭头；适用：地图导航、方向指引、路线规划。"
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
  "event": [
    {
      "id": "event.startNavigate",
      "description": "点击导航按钮，跳转到地图应用进行导航。大模型需根据用户说的目的地选择location的值，只支持回家和去公司的导航",
      "call": "clickToIntent",
      "args": {
        "intentName": "StartNavigate",
        "params": {
          "dstLocation": {
            "location": "company",
            "latitude": "",
            "longitude": ""
          }
        }
      }
    }
  ],
  "asset": [
    "asset.icon_meeting",
    "asset.location_north_up_right_fill",
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
        "/events/0/dtStart",
        "/events/0/eventLocation"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.startNavigate",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "StartNavigate",
          "params": {
            "dstLocation": {
              "location": "company",
              "latitude": "",
              "longitude": ""
            }
          }
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.location_north_up_right_fill",
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
  "artifactId": "3a5eb855-f815-492b-8f47-1528b6ac1e86",
  "createdAt": 1792045423378
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","meeting","navigate"]]
["header","SingleLineTitle",{"title":"版本发布排期会","icon":"resources/base/media/icon_meeting.svg","fontSize":12}]
["meeting","EmphasisText",{"mainText":{"path":"/data/calendar/events/0/dtStart"},"secondaryText":{"path":"/data/calendar/events/0/eventLocation"},"fontSize":18}]
["navigate","PillButton",{"label":"导航去公司","icon":"resources/base/media/location_north_up_right_fill.svg","onClick":[{"call":"clickToIntent","args":{"intentName":"StartNavigate","params":{"dstLocation":{"location":"company","latitude":"","longitude":""}}}}]}]
["/data/calendar/events/0/dtStart","15:00"]
["/data/calendar/events/0/eventLocation","总部大楼"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "下一场日程是下午三点的版本发布排期会，帮我做个卡片，看会议开始时间和地点，点击导航去公司。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 7
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/dtStart",
          "/events/0/eventLocation"
        ]
      }
    ],
    "title": "发布排期",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.startNavigate",
        "action": {
          "call": "clickToIntent",
          "args": {
            "intentName": "StartNavigate",
            "params": {
              "dstLocation": {
                "location": "company",
                "latitude": "",
                "longitude": ""
              }
            }
          }
        }
      }
    ],
    "description": "会议时间和导航",
    "candidateAssetIds": [
      "asset.icon_meeting",
      "asset.location_north_up_right_fill",
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
    "time": "20260828000000000"
  },
  "pagination": {
    "limit": 5,
    "start": ""
  },
  "session": {
    "interactionId": "018",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "下一场日程是下午三点的版本发布排期会，帮我做个卡片，看会议开始时间和地点，点击导航去公司。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "下一场日程是下午三点的版本发布排期会，帮我做个卡片，看会议开始时间和地点，点击导航去公司。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 7
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/dtStart",
        "/events/0/eventLocation"
      ]
    }
  ],
  "title": "发布排期",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.startNavigate",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "StartNavigate",
          "params": {
            "dstLocation": {
              "location": "company",
              "latitude": "",
              "longitude": ""
            }
          }
        }
      }
    }
  ],
  "description": "会议时间和导航",
  "candidateAssetIds": [
    "asset.icon_meeting",
    "asset.location_north_up_right_fill",
    "asset.clock_fill",
    "asset.local_fill"
  ]
}
```
