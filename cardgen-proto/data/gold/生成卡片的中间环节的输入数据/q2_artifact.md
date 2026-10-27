```cardspec
{
  "title": "明日天气",
  "description": "日期星期和天气",
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
        "prefectureName": "重庆市",
        "forecastDays": 2
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"重庆明日天气","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/calendar_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["condition"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"condition","component":"Column","children":["condition_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"condition_main","component":"Text","content":"{{ ${/data/weather/daily/1/condition} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["day_info"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"day_info","component":"Column","children":["day_info_row0","day_info_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"day_info_item0_label","component":"Text","content":"日期 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"day_info_item0_value","component":"Text","content":"{{ ${/data/weather/daily/1/date} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"day_info_item0","component":"Row","children":["day_info_item0_label","day_info_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"day_info_row0","component":"Row","children":["day_info_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"day_info_item1_label","component":"Text","content":"星期 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"day_info_item1_value","component":"Text","content":"{{ ${/data/weather/daily/1/weekday} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"day_info_item1","component":"Row","children":["day_info_item1_label","day_info_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"day_info_row1","component":"Row","children":["day_info_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"daily":[null,{"date":"2026-08-06","weekday":"星期四","condition":"多云"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "明天在重庆安排户外活动，帮我做个卡片，看明天的日期、星期和天气。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "weather": {
        "daily": [
          {},
          {
            "date": {
              "type": "string",
              "description": "预报日期，来源于 day_time。",
              "sampleValue": "2026-08-06"
            },
            "weekday": {
              "type": "string",
              "description": "星期文本，例如“星期日”。",
              "sampleValue": "星期四"
            },
            "condition": {
              "type": "string",
              "description": "白天天气现象，来源于weather_icon。",
              "sampleValue": "多云"
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
      "id": "asset.sun_max",
      "src": "resources/base/media/sun_max.svg",
      "description": "样式：默认黑色的单色线框太阳，中央大圆环，周围为八条较长放射线；适用：高亮度、强光、晴天或亮度增大。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "ViewWeather"
  ],
  "event": [],
  "asset": [
    "asset.calendar_fill",
    "asset.sun_max"
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
        "prefectureName": "重庆市",
        "forecastDays": 2
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/1/date",
        "/daily/1/weekday",
        "/daily/1/condition"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.sun_max"
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
  "artifactId": "6547c5d5-5577-4c15-870a-e1e79e107956",
  "createdAt": 1792045359052
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","condition","day_info"]]
["header","SingleLineTitle",{"title":"重庆明日天气","icon":"resources/base/media/calendar_fill.svg","fontSize":12}]
["condition","EmphasisText",{"mainText":{"path":"/data/weather/daily/1/condition"},"fontSize":18}]
["day_info","SecondaryBody",{"items":[{"label":"日期 ","value":{"path":"/data/weather/daily/1/date"}},{"label":"星期 ","value":{"path":"/data/weather/daily/1/weekday"}}],"fontSize":14}]
["/data/weather/daily/1/date","2026-08-06"]
["/data/weather/daily/1/weekday","星期四"]
["/data/weather/daily/1/condition","多云"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "明天在重庆安排户外活动，帮我做个卡片，看明天的日期、星期和天气。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "重庆市",
          "forecastDays": 2
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/daily/1/date",
          "/daily/1/weekday",
          "/daily/1/condition"
        ]
      }
    ],
    "title": "明日天气",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "日期星期和天气",
    "candidateAssetIds": [
      "asset.calendar_fill",
      "asset.sun_max"
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
    "interactionId": "002",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "明天在重庆安排户外活动，帮我做个卡片，看明天的日期、星期和天气。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "明天在重庆安排户外活动，帮我做个卡片，看明天的日期、星期和天气。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "重庆市",
        "forecastDays": 2
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/1/date",
        "/daily/1/weekday",
        "/daily/1/condition"
      ]
    }
  ],
  "title": "明日天气",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "日期星期和天气",
  "candidateAssetIds": [
    "asset.calendar_fill",
    "asset.sun_max"
  ]
}
```
