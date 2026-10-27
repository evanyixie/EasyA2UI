```cardspec
{
  "title": "太阳岛天气",
  "description": "地区和健康指数",
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
        "prefectureName": "哈尔滨市",
        "districtName": "松北区",
        "forecastDays": 5
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__content"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"{{ '太阳岛 · ' + ${/data/weather/location/districtName} }}","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/calendar_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__content","component":"Column","children":["metrics"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"metrics","component":"Column","children":["metrics_row0","metrics_row1","metrics_row2"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"metrics_row0","component":"Row","children":["metrics_row0_label","metrics_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"metrics_row0_label","component":"Text","content":"空气质量","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"metrics_row0_value","component":"Text","content":"{{ ${/data/weather/daily/4/airQuality} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"metrics_row1","component":"Row","children":["metrics_row1_label","metrics_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"metrics_row1_label","component":"Text","content":"紫外线","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"metrics_row1_value","component":"Text","content":"{{ ${/data/weather/daily/4/uvIndex} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"metrics_row2","component":"Row","children":["metrics_row2_label","metrics_row2_value"],"itemMargin":8,"styles":{"width":"matchParent","height":16,"alignItems":"top","justifyContent":"spaceBetween","flexShrink":0}},{"id":"metrics_row2_label","component":"Text","content":"感冒指数","styles":{"height":16,"fontSize":10,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"metrics_row2_value","component":"Text","content":"{{ ${/data/weather/daily/4/coldLevel} }}","styles":{"height":16,"fontSize":10,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"location":{"districtName":"青浦区"},"daily":[null,null,null,null,{"airQuality":"良","uvIndex":"中等","coldLevel":"低"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "4天后要带孩子去哈尔滨太阳岛，帮我做个健康指数卡片，确认预报地区，看当天空气质量、紫外线和感冒指数。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "weather": {
        "location": {
          "districtName": {
            "type": "string",
            "description": "区或县名称",
            "sampleValue": "青浦区"
          }
        },
        "daily": [
          {},
          {},
          {},
          {},
          {
            "airQuality": {
              "type": "string",
              "description": "当天空气质量等级。",
              "sampleValue": "良"
            },
            "uvIndex": {
              "type": "string",
              "description": "当天紫外线等级。",
              "sampleValue": "中等"
            },
            "coldLevel": {
              "type": "string",
              "description": "感冒指数。",
              "sampleValue": "低"
            }
          }
        ]
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.cold",
      "src": "resources/base/media/cold.svg",
      "description": "样式：默认黑色的单色线框圆形人脸，口鼻处佩戴口罩；适用：佩戴口罩、防护、呼吸道健康或传染风险提示。"
    },
    {
      "id": "asset.sun_max",
      "src": "resources/base/media/sun_max.svg",
      "description": "样式：默认黑色的单色线框太阳，中央大圆环，周围为八条较长放射线；适用：高亮度、强光、晴天或亮度增大。"
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
    "asset.cold",
    "asset.sun_max",
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
        "prefectureName": "哈尔滨市",
        "districtName": "松北区",
        "forecastDays": 5
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/location/districtName",
        "/daily/4/airQuality",
        "/daily/4/uvIndex",
        "/daily/4/coldLevel"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.cold",
    "asset.sun_max",
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
  "artifactId": "a8456249-efc0-411f-bcb7-713ee40aa25a",
  "createdAt": 1792045623483
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","metrics"]]
["header","SingleLineTitle",{"title":"{{ '太阳岛 · ' + ${/data/weather/location/districtName} }}","icon":"resources/base/media/calendar_fill.svg","fontSize":12}]
["metrics","TableText",{"items":[{"label":"空气质量","value":{"path":"/data/weather/daily/4/airQuality"}},{"label":"紫外线","value":{"path":"/data/weather/daily/4/uvIndex"}},{"label":"感冒指数","value":{"path":"/data/weather/daily/4/coldLevel"}}],"fontSize":10}]
["/data/weather/location/districtName","青浦区"]
["/data/weather/daily/4/airQuality","良"]
["/data/weather/daily/4/uvIndex","中等"]
["/data/weather/daily/4/coldLevel","低"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "4天后要带孩子去哈尔滨太阳岛，帮我做个健康指数卡片，确认预报地区，看当天空气质量、紫外线和感冒指数。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "哈尔滨市",
          "districtName": "松北区",
          "forecastDays": 5
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/location/districtName",
          "/daily/4/airQuality",
          "/daily/4/uvIndex",
          "/daily/4/coldLevel"
        ]
      }
    ],
    "title": "太阳岛天气",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "地区和健康指数",
    "candidateAssetIds": [
      "asset.cold",
      "asset.sun_max",
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
    "interactionId": "051",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "4天后要带孩子去哈尔滨太阳岛，帮我做个健康指数卡片，确认预报地区，看当天空气质量、紫外线和感冒指数。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "4天后要带孩子去哈尔滨太阳岛，帮我做个健康指数卡片，确认预报地区，看当天空气质量、紫外线和感冒指数。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "哈尔滨市",
        "districtName": "松北区",
        "forecastDays": 5
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/location/districtName",
        "/daily/4/airQuality",
        "/daily/4/uvIndex",
        "/daily/4/coldLevel"
      ]
    }
  ],
  "title": "太阳岛天气",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "地区和健康指数",
  "candidateAssetIds": [
    "asset.cold",
    "asset.sun_max",
    "asset.calendar_fill"
  ]
}
```
