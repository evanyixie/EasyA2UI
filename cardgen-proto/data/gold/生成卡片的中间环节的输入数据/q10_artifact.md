```cardspec
{
  "title": "周末露营",
  "description": "天气和空气质量",
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
        "prefectureName": "杭州市",
        "forecastDays": 3
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["tomorrow","dayafter"],"itemMargin":8,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":8,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"tomorrow","component":"Column","children":["tomorrow_text"],"itemMargin":0,"styles":{"padding":{"left":8,"right":8},"borderRadius":16,"alignItems":"start","justifyContent":"center","clip":true,"flexShrink":0,"width":"matchParent","height":63,"backgroundColor":"#CCFFFFFF","layoutWeight":1}},{"id":"tomorrow_text","component":"Column","children":["tomorrow_primary","tomorrow_secondary"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"center","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"tomorrow_primary","component":"Text","content":"{{ '明天 ' + ${/data/weather/daily/1/condition} }}","styles":{"height":22,"fontSize":16,"fontWeight":700,"maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"tomorrow_secondary","component":"Text","content":"{{ '空气质量 ' + ${/data/weather/daily/1/airQuality} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"textOverflow":"ellipsis","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#991F4799"}},{"id":"dayafter","component":"Column","children":["dayafter_text"],"itemMargin":0,"styles":{"padding":{"left":8,"right":8},"borderRadius":16,"alignItems":"start","justifyContent":"center","clip":true,"flexShrink":0,"width":"matchParent","height":63,"backgroundColor":"#CCFFFFFF","layoutWeight":1}},{"id":"dayafter_text","component":"Column","children":["dayafter_primary","dayafter_secondary"],"itemMargin":0,"styles":{"alignItems":"start","justifyContent":"center","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"dayafter_primary","component":"Text","content":"{{ '后天 ' + ${/data/weather/daily/2/condition} }}","styles":{"height":22,"fontSize":16,"fontWeight":700,"maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"dayafter_secondary","component":"Text","content":"{{ '空气质量 ' + ${/data/weather/daily/2/airQuality} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"textOverflow":"ellipsis","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent","fontColor":"#991F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"daily":[null,{"condition":"多云","airQuality":"良"},{"condition":"多云","airQuality":"良"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "周末准备去杭州露营，帮我做个卡片，分别看杭州明天和后天的天气、空气质量。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "weather": {
        "daily": [
          {},
          {
            "condition": {
              "type": "string",
              "description": "白天天气现象，来源于weather_icon。",
              "sampleValue": "多云"
            },
            "airQuality": {
              "type": "string",
              "description": "当天空气质量等级。",
              "sampleValue": "良"
            }
          },
          {
            "condition": {
              "type": "string",
              "description": "白天天气现象，来源于weather_icon。",
              "sampleValue": "多云"
            },
            "airQuality": {
              "type": "string",
              "description": "当天空气质量等级。",
              "sampleValue": "良"
            }
          }
        ]
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.sun_max",
      "src": "resources/base/media/sun_max.svg",
      "description": "样式：默认黑色的单色线框太阳，中央大圆环，周围为八条较长放射线；适用：高亮度、强光、晴天或亮度增大。"
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
    "ViewWeather"
  ],
  "event": [],
  "asset": [
    "asset.sun_max",
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
        "prefectureName": "杭州市",
        "forecastDays": 3
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/1/condition",
        "/daily/1/airQuality",
        "/daily/2/condition",
        "/daily/2/airQuality"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.sun_max",
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
  "artifactId": "0a723cd7-6f1b-46e8-a16e-dc54d5b4fad9",
  "createdAt": 1792045389210
}
```
```designcompactdsl
["root","Layout",{"layout":"S-dual-info","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["tomorrow","dayafter"]]
["tomorrow","InfoBlock",{"primaryText":"{{ '明天 ' + ${/data/weather/daily/1/condition} }}","secondaryText":"{{ '空气质量 ' + ${/data/weather/daily/1/airQuality} }}","backgroundColor":"#CCFFFFFF"}]
["dayafter","InfoBlock",{"primaryText":"{{ '后天 ' + ${/data/weather/daily/2/condition} }}","secondaryText":"{{ '空气质量 ' + ${/data/weather/daily/2/airQuality} }}","backgroundColor":"#CCFFFFFF"}]
["/data/weather/daily/1/condition","多云"]
["/data/weather/daily/1/airQuality","良"]
["/data/weather/daily/2/condition","多云"]
["/data/weather/daily/2/airQuality","良"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "周末准备去杭州露营，帮我做个卡片，分别看杭州明天和后天的天气、空气质量。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "杭州市",
          "forecastDays": 3
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/daily/1/condition",
          "/daily/1/airQuality",
          "/daily/2/condition",
          "/daily/2/airQuality"
        ]
      }
    ],
    "title": "周末露营",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "天气和空气质量",
    "candidateAssetIds": [
      "asset.sun_max",
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
    "interactionId": "010",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "周末准备去杭州露营，帮我做个卡片，分别看杭州明天和后天的天气、空气质量。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "周末准备去杭州露营，帮我做个卡片，分别看杭州明天和后天的天气、空气质量。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "杭州市",
        "forecastDays": 3
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/1/condition",
        "/daily/1/airQuality",
        "/daily/2/condition",
        "/daily/2/airQuality"
      ]
    }
  ],
  "title": "周末露营",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "天气和空气质量",
  "candidateAssetIds": [
    "asset.sun_max",
    "asset.local_fill"
  ]
}
```
