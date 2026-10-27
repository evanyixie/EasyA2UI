```cardspec
{
  "title": "明早出门",
  "description": "天气体感+首个日程",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "深圳市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather"
    },
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"深圳天气","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/icon_weather_thermometer.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["weather"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"weather","component":"Column","children":["weather_main","weather_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"weather_main","component":"Text","content":"{{ ${/data/weather/current/temperatureC} + '℃' }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"weather_secondary","component":"Text","content":"{{ ${/data/weather/current/condition} + ' · 体感 ' + ${/data/weather/current/feelsLikeC} + '℃' }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#991F4799","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["schedule","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"schedule","component":"Column","children":["schedule_row0","schedule_row1"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"schedule_item0_value","component":"Text","content":"{{ '首项日程 ' + ${/data/calendar/events/0/dtStart} }}","styles":{"height":32.0,"fontSize":12,"fontWeight":400,"maxLines":2,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"schedule_item0","component":"Row","children":["schedule_item0_value"],"itemMargin":0,"styles":{"height":32.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"schedule_row0","component":"Row","children":["schedule_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":32.0,"alignItems":"top","flexShrink":0}},{"id":"schedule_item1_label","component":"Text","content":"地点 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"schedule_item1_value","component":"Text","content":"{{ ${/data/calendar/events/0/eventLocation} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"schedule_item1","component":"Row","children":["schedule_item1_label","schedule_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"schedule_row1","component":"Row","children":["schedule_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["detail_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"detail_action","component":"Stack","children":["detail_action_icon"],"onClick":[{"call":"clickToIntent","args":{"intentName":"ViewCalendarEvent","params":{"entityId":"{{ ${/data/calendar/events/0/entityId} }}"}}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#331F4799","alignContent":"center","clip":true}},{"id":"detail_action_icon","component":"Image","src":"resources/base/media/calendar_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"current":{"condition":"多云","temperatureC":29,"feelsLikeC":31}},"calendar":{"events":[{"dtStart":"14:00","eventLocation":"会议室","entityId":"example-event-001"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，看看深圳天气和体感，再看看上午第一件日程几点开始、具体位置是哪里，点一下能查看日程详情。",
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
      "weather": {
        "current": {
          "condition": {
            "type": "string",
            "description": "当前天气现象，例如“阴”“多云”“小雨”。",
            "sampleValue": "多云"
          },
          "temperatureC": {
            "type": "number",
            "description": "当前温度的纯数值，单位为摄氏度，返回值不包含单位。若直接用于文本展示，必须在数值后追加“℃”；优先使用 temperatureText。",
            "sampleValue": 29
          },
          "feelsLikeC": {
            "type": "number",
            "description": "当前体感温度的纯数值，单位为摄氏度，返回值不包含单位。若直接用于文本展示，必须在数值后追加“℃”。",
            "sampleValue": 31
          }
        }
      },
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
      "id": "asset.icon_weather_thermometer",
      "src": "resources/base/media/icon_weather_thermometer.svg",
      "description": "样式：黑色的温度计图标，底部为实心感揾泡，管身内测带三段刻度；适用：天气温度、温度指标、温差变化或冷热趋势。"
    },
    {
      "id": "asset.calendar_fill",
      "src": "resources/base/media/calendar_fill.svg",
      "description": "样式：日历实心图标，默认黑色，图形为带格线的日历本造型；适用：日程管理、日历事件查看、当日安排。"
    },
    {
      "id": "asset.local_fill",
      "src": "resources/base/media/local_fill.svg",
      "description": "样式：默认黑色的单色实心地图定位针，中央为圆形留白；适用：当前位置、地点、地图标记、位置服务。"
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
    "ViewWeather",
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
    "asset.icon_weather_thermometer",
    "asset.calendar_fill",
    "asset.local_fill",
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
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "深圳市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/current/condition",
        "/current/temperatureC",
        "/current/feelsLikeC"
      ]
    },
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/dtStart",
        "/events/0/eventLocation",
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
    "asset.icon_weather_thermometer",
    "asset.calendar_fill",
    "asset.local_fill",
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
  "artifactId": "e087b42c-7a72-44a3-a158-81bf03a594d5",
  "createdAt": 1792045487737
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["title_area","weather","schedule","detail_action"]]
["title_area","SingleLineTitle",{"title":"深圳天气","icon":"resources/base/media/icon_weather_thermometer.svg","fontSize":12}]
["weather","EmphasisText",{"mainText":"{{ ${/data/weather/current/temperatureC} + '℃' }}","secondaryText":"{{ ${/data/weather/current/condition} + ' · 体感 ' + ${/data/weather/current/feelsLikeC} + '℃' }}","fontSize":18}]
["schedule","SecondaryBody",{"items":[{"label":"首项日程 ","value":{"path":"/data/calendar/events/0/dtStart"}},{"label":"地点 ","value":{"path":"/data/calendar/events/0/eventLocation"}}],"columns":1,"fontSize":12}]
["detail_action","CircleButton",{"icon":"resources/base/media/calendar_fill.svg","accessibility":{"label":"查看日程详情"},"onClick":[{"call":"clickToIntent","args":{"intentName":"ViewCalendarEvent","params":{"entityId":"{{ ${/data/calendar/events/0/entityId} }}"}}}]}]
["/data/weather/current/condition","多云"]
["/data/weather/current/temperatureC",29]
["/data/weather/current/feelsLikeC",31]
["/data/calendar/events/0/dtStart","14:00"]
["/data/calendar/events/0/eventLocation","会议室"]
["/data/calendar/events/0/entityId","example-event-001"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，看看深圳天气和体感，再看看上午第一件日程几点开始、具体位置是哪里，点一下能查看日程详情。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "深圳市",
          "forecastDays": 1
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/current/condition",
          "/current/temperatureC",
          "/current/feelsLikeC"
        ]
      },
      {
        "capabilityId": "GetCalendarEvents",
        "arguments": {
          "futureDays": 1
        },
        "writeResultTo": "/data/calendar",
        "candidateOutputFields": [
          "/events/0/dtStart",
          "/events/0/eventLocation",
          "/events/0/entityId"
        ]
      }
    ],
    "title": "明早出门",
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
    "description": "天气体感+首个日程",
    "candidateAssetIds": [
      "asset.icon_weather_thermometer",
      "asset.calendar_fill",
      "asset.local_fill",
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
    "interactionId": "029",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，看看深圳天气和体感，再看看上午第一件日程几点开始、具体位置是哪里，点一下能查看日程详情。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，看看深圳天气和体感，再看看上午第一件日程几点开始、具体位置是哪里，点一下能查看日程详情。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "深圳市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/current/condition",
        "/current/temperatureC",
        "/current/feelsLikeC"
      ]
    },
    {
      "capabilityId": "GetCalendarEvents",
      "arguments": {
        "futureDays": 1
      },
      "writeResultTo": "/data/calendar",
      "candidateOutputFields": [
        "/events/0/dtStart",
        "/events/0/eventLocation",
        "/events/0/entityId"
      ]
    }
  ],
  "title": "明早出门",
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
  "description": "天气体感+首个日程",
  "candidateAssetIds": [
    "asset.icon_weather_thermometer",
    "asset.calendar_fill",
    "asset.local_fill",
    "asset.clock_fill"
  ]
}
```
