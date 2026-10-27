```cardspec
{
  "title": "双城天气",
  "description": "两地温度天气",
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
        "prefectureName": "上海市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather1"
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "成都市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather2"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["chengdu","shanghai"],"itemMargin":8,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":8,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"chengdu","component":"Column","children":["chengdu_text"],"itemMargin":0,"styles":{"padding":{"left":8,"right":8},"borderRadius":16,"alignItems":"start","justifyContent":"center","clip":true,"flexShrink":0,"width":"matchParent","height":63,"backgroundColor":"#CCFFFFFF","layoutWeight":1}},{"id":"chengdu_text","component":"Column","children":["chengdu_primary","chengdu_secondary"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"center","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"chengdu_primary","component":"Text","content":"{{ '成都 ' + ${/data/weather1/current/temperatureC} + '℃' }}","styles":{"height":22,"fontSize":16,"fontWeight":700,"maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"chengdu_secondary","component":"Text","content":"{{ ${/data/weather1/current/condition} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"textOverflow":"ellipsis","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#991F4799"}},{"id":"shanghai","component":"Column","children":["shanghai_text"],"itemMargin":0,"styles":{"padding":{"left":8,"right":8},"borderRadius":16,"alignItems":"start","justifyContent":"center","clip":true,"flexShrink":0,"width":"matchParent","height":63,"backgroundColor":"#CCFFFFFF","layoutWeight":1}},{"id":"shanghai_text","component":"Column","children":["shanghai_primary","shanghai_secondary"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"center","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"shanghai_primary","component":"Text","content":"{{ '上海 ' + ${/data/weather2/current/temperatureC} + '℃' }}","styles":{"height":22,"fontSize":16,"fontWeight":700,"maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"shanghai_secondary","component":"Text","content":"{{ ${/data/weather2/current/condition} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"textOverflow":"ellipsis","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#991F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather1":{"current":{"temperatureC":29,"condition":"多云"}},"weather2":{"current":{"temperatureC":29,"condition":"多云"}}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个天气卡片，看看成都和上海各多少度、什么天气，能直接在卡片上看到。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "weather1": {
        "current": {
          "temperatureC": {
            "type": "number",
            "description": "当前温度的纯数值，单位为摄氏度，返回值不包含单位。若直接用于文本展示，必须在数值后追加“℃”；优先使用 temperatureText。",
            "sampleValue": 29
          },
          "condition": {
            "type": "string",
            "description": "当前天气现象，例如“阴”“多云”“小雨”。",
            "sampleValue": "多云"
          }
        }
      },
      "weather2": {
        "current": {
          "temperatureC": {
            "type": "number",
            "description": "当前温度的纯数值，单位为摄氏度，返回值不包含单位。若直接用于文本展示，必须在数值后追加“℃”；优先使用 temperatureText。",
            "sampleValue": 29
          },
          "condition": {
            "type": "string",
            "description": "当前天气现象，例如“阴”“多云”“小雨”。",
            "sampleValue": "多云"
          }
        }
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
    "ViewWeather",
    "ViewWeather"
  ],
  "event": [],
  "asset": [
    "asset.icon_weather_thermometer",
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
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "上海市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather1",
      "candidateOutputFields": [
        "/current/temperatureC",
        "/current/condition"
      ]
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "成都市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather2",
      "candidateOutputFields": [
        "/current/temperatureC",
        "/current/condition"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.icon_weather_thermometer",
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
  "artifactId": "8ea35e41-8e6d-48f7-99cd-88a9112121cc",
  "createdAt": 1792045506610
}
```
```designcompactdsl
["root","Layout",{"layout":"S-dual-info","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["chengdu","shanghai"]]
["chengdu","InfoBlock",{"primaryText":"{{ '成都 ' + ${/data/weather1/current/temperatureC} + '℃' }}","secondaryText":{"path":"/data/weather1/current/condition"},"backgroundColor":"#CCFFFFFF"}]
["shanghai","InfoBlock",{"primaryText":"{{ '上海 ' + ${/data/weather2/current/temperatureC} + '℃' }}","secondaryText":{"path":"/data/weather2/current/condition"},"backgroundColor":"#CCFFFFFF"}]
["/data/weather1/current/temperatureC",29]
["/data/weather1/current/condition","多云"]
["/data/weather2/current/temperatureC",29]
["/data/weather2/current/condition","多云"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个天气卡片，看看成都和上海各多少度、什么天气，能直接在卡片上看到。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "上海市",
          "forecastDays": 1
        },
        "writeResultTo": "/data/weather1",
        "candidateOutputFields": [
          "/current/temperatureC",
          "/current/condition"
        ]
      },
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "成都市",
          "forecastDays": 1
        },
        "writeResultTo": "/data/weather2",
        "candidateOutputFields": [
          "/current/temperatureC",
          "/current/condition"
        ]
      }
    ],
    "title": "双城天气",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "两地温度天气",
    "candidateAssetIds": [
      "asset.icon_weather_thermometer",
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
    "interactionId": "034",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个天气卡片，看看成都和上海各多少度、什么天气，能直接在卡片上看到。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个天气卡片，看看成都和上海各多少度、什么天气，能直接在卡片上看到。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "上海市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather1",
      "candidateOutputFields": [
        "/current/temperatureC",
        "/current/condition"
      ]
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "成都市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather2",
      "candidateOutputFields": [
        "/current/temperatureC",
        "/current/condition"
      ]
    }
  ],
  "title": "双城天气",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "两地温度天气",
  "candidateAssetIds": [
    "asset.icon_weather_thermometer",
    "asset.local_fill"
  ]
}
```
