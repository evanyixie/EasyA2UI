```cardspec
{
  "title": "广州出行",
  "description": "降雨概率和温度",
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
        "prefectureName": "广州市",
        "forecastDays": 2
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"明天广州","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/drop_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["rain"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"rain","component":"Row","children":["rain_value","rain_unit"],"itemMargin":2,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"rain_value","component":"Text","content":"{{ ${/data/weather/daily/1/rainProbabilityPercent} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"rain_unit","component":"Text","content":"%","styles":{"height":13.25,"fontSize":12,"fontWeight":500,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","padding":{"top":0,"right":0,"bottom":1.25,"left":0},"textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["temp"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"temp","component":"Column","children":["temp_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"temp_item0_label","component":"Text","content":"温度范围","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"temp_item0_value","component":"Text","content":"{{ ${/data/weather/daily/1/temperatureRangeText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"temp_item0","component":"Row","children":["temp_item0_label","temp_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"temp_row0","component":"Row","children":["temp_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"daily":[null,{"rainProbabilityPercent":20,"temperatureRangeText":"25℃ / 32℃"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "明天要在广州出门办事，帮我做个降雨卡片，看明天下雨概率，再看温度范围。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "weather": {
        "daily": [
          {},
          {
            "temperatureRangeText": {
              "type": "string",
              "description": "可直接显示的最低温与最高温范围文本，每个温度值均已包含“℃”单位；展示时不得再次追加温度单位。例如“25℃ / 32℃”。",
              "sampleValue": "25℃ / 32℃"
            },
            "rainProbabilityPercent": {
              "type": "number",
              "description": "白天降雨概率的百分数数值，返回值不包含单位，例如 20 表示 20%；文本展示必须追加一个“%”，进度组件直接使用数值。",
              "sampleValue": 20
            }
          }
        ]
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.icon_weather_thermometer_medium",
      "src": "resources/base/media/icon_weather_thermometer_medium.svg",
      "description": "样式：黑色的温度计图标，内部温度柱处于中档，管身右侧带三组刻度；适用：中等温度、舒适温度区间、当前气温或温度等级。"
    },
    {
      "id": "asset.drop_1",
      "src": "resources/base/media/drop_1.svg",
      "description": "样式：双水滴实心图标，默认黑色，图形为左侧较大水滴与右侧较小水滴错位叠放，顶部尖收、底部圆润；适用：湿度数据展示、饮水提醒、天气降雨信息。"
    },
    {
      "id": "asset.calendar_fill",
      "src": "resources/base/media/calendar_fill.svg",
      "description": "样式：日历实心图标，默认黑色，图形为带格线的日历本造型；适用：日程管理、日历事件查看、当日安排。"
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
    "asset.icon_weather_thermometer_medium",
    "asset.drop_1",
    "asset.calendar_fill"
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
        "prefectureName": "广州市",
        "forecastDays": 2
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/1/temperatureRangeText",
        "/daily/1/rainProbabilityPercent"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.icon_weather_thermometer_medium",
    "asset.drop_1",
    "asset.calendar_fill"
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
  "artifactId": "ca2c3105-b3ee-41e1-8b9a-f9cd71a504e0",
  "createdAt": 1792045368584
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","rain","temp"]]
["header","SingleLineTitle",{"title":"明天广州","icon":"resources/base/media/drop_1.svg","fontSize":12}]
["rain","EmphasizedData",{"value":{"path":"/data/weather/daily/1/rainProbabilityPercent"},"unit":"%","fontSize":30}]
["temp","SecondaryBody",{"items":[{"label":"温度范围","value":{"path":"/data/weather/daily/1/temperatureRangeText"}}],"fontSize":14}]
["/data/weather/daily/1/rainProbabilityPercent",20]
["/data/weather/daily/1/temperatureRangeText","25℃ / 32℃"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "明天要在广州出门办事，帮我做个降雨卡片，看明天下雨概率，再看温度范围。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "广州市",
          "forecastDays": 2
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/daily/1/temperatureRangeText",
          "/daily/1/rainProbabilityPercent"
        ]
      }
    ],
    "title": "广州出行",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "降雨概率和温度",
    "candidateAssetIds": [
      "asset.icon_weather_thermometer_medium",
      "asset.drop_1",
      "asset.calendar_fill"
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
    "interactionId": "005",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "明天要在广州出门办事，帮我做个降雨卡片，看明天下雨概率，再看温度范围。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "明天要在广州出门办事，帮我做个降雨卡片，看明天下雨概率，再看温度范围。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "广州市",
        "forecastDays": 2
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/1/temperatureRangeText",
        "/daily/1/rainProbabilityPercent"
      ]
    }
  ],
  "title": "广州出行",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "降雨概率和温度",
  "candidateAssetIds": [
    "asset.icon_weather_thermometer_medium",
    "asset.drop_1",
    "asset.calendar_fill"
  ]
}
```
