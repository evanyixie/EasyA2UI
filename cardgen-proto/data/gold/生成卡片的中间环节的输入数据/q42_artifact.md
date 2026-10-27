```cardspec
{
  "title": "出差倒计时",
  "description": "倒计时+目的地天气",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetCountdownDays",
      "arguments": {
        "targetDate": "2026-11-15"
      },
      "writeResultTo": "/data/countdown"
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "北京市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"北京出差","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/airplane_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["countdown"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"countdown","component":"Row","children":["countdown_value","countdown_unit"],"itemMargin":2,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"countdown_value","component":"Text","content":"{{ ${/data/countdown/countdownDays} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"countdown_unit","component":"Text","content":"天","styles":{"height":13.75,"fontSize":12,"fontWeight":500,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#998C4B1C","padding":{"top":0,"right":0,"bottom":1.75,"left":0},"textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["weather","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"weather","component":"Column","children":["weather_row0"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"weather_item0_value","component":"Text","content":"{{ '北京天气 ' + (${/data/weather/current/condition} + ' ' + ${/data/weather/current/temperatureC} + '℃') }}","styles":{"height":32.0,"fontSize":12,"fontWeight":400,"maxLines":2,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_item0","component":"Row","children":["weather_item0_value"],"itemMargin":0,"styles":{"height":32.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_row0","component":"Row","children":["weather_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":32.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["weather_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"weather_action","component":"Stack","children":["weather_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Weather_CityCode","bundleName":"","abilityName":"","uri":"{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#338C4B1C","alignContent":"center","clip":true}},{"id":"weather_action_icon","component":"Image","src":"resources/base/media/icon_weather_thermometer.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"countdown":{"countdownDays":86},"weather":{"current":{"condition":"多云","temperatureC":29},"location":{"cityCode":"60814"}}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，86天后要去北京出差一周，展示还有几天出发、北京的天气，点一下能看北京天气详情。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.weather",
      "description": "打开手机天气应用某城市页，uri为固定值勿更改。cityCode来自于数据能力中ViewWeather出参cityCode字段，进行动态拼接，表示跳转到指定城市天气页。",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Weather_CityCode",
        "bundleName": "",
        "abilityName": "",
        "uri": "{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "countdown": {
        "countdownDays": {
          "type": "integer",
          "description": "距离目标日期的自然日天数纯整数，返回值不包含“天”。正数表示未来，0 表示今天，负数表示已经过去；若直接用于文本展示，必须在数值后追加“天”。",
          "sampleValue": 30
        }
      },
      "weather": {
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
        },
        "location": {
          "cityCode": {
            "type": "string",
            "description": "城市代码，如60814代表青浦区",
            "sampleValue": "60814"
          }
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.airplane_fill_1",
      "src": "resources/base/media/airplane_fill_1.svg",
      "description": "样式：默认黑色的单色实心飞机俯视图，机头朝右上方倾斜；适用：航空旅行、航班概览、飞行状态。"
    },
    {
      "id": "asset.icon_weather_thermometer",
      "src": "resources/base/media/icon_weather_thermometer.svg",
      "description": "样式：黑色的温度计图标，底部为实心感揾泡，管身内测带三段刻度；适用：天气温度、温度指标、温差变化或冷热趋势。"
    },
    {
      "id": "asset.icon_timing",
      "src": "resources/base/media/icon_timing.svg",
      "description": "样式：默认白色的单色秒表实心图标，内部通过镂空表现表盘指针，支持通过 fillColor 与卡片配色统一；适用：计时、使用时长、倒计时或时限。"
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
    "GetCountdownDays",
    "ViewWeather"
  ],
  "event": [
    {
      "id": "event.open.weather",
      "description": "打开手机天气应用某城市页，uri为固定值勿更改。cityCode来自于数据能力中ViewWeather出参cityCode字段，进行动态拼接，表示跳转到指定城市天气页。",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Weather_CityCode",
        "bundleName": "",
        "abilityName": "",
        "uri": "{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"
      }
    }
  ],
  "asset": [
    "asset.airplane_fill_1",
    "asset.icon_weather_thermometer",
    "asset.icon_timing",
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
      "capabilityId": "GetCountdownDays",
      "arguments": {
        "targetDate": "2026-11-15"
      },
      "writeResultTo": "/data/countdown",
      "candidateOutputFields": [
        "/countdownDays"
      ]
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "北京市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/current/temperatureC",
        "/current/condition",
        "/location/cityCode"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.weather",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Weather_CityCode",
          "bundleName": "",
          "abilityName": "",
          "uri": "{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.airplane_fill_1",
    "asset.icon_weather_thermometer",
    "asset.icon_timing",
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
  "artifactId": "94229c97-6503-4ff6-8270-a9760162c211",
  "createdAt": 1792045565531
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","countdown","weather","weather_action"]]
["header","SingleLineTitle",{"title":"北京出差","icon":"resources/base/media/airplane_fill_1.svg","fontSize":12}]
["countdown","EmphasizedData",{"value":{"path":"/data/countdown/countdownDays"},"unit":"天","fontSize":30}]
["weather","SecondaryBody",{"items":[{"label":"北京天气 ","value":"{{ ${/data/weather/current/condition} + ' ' + ${/data/weather/current/temperatureC} + '℃' }}"}]}]
["weather_action","CircleButton",{"icon":"resources/base/media/icon_weather_thermometer.svg","accessibility":{"label":"查看北京天气详情"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Weather_CityCode","bundleName":"","abilityName":"","uri":"{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"}}]}]
["/data/countdown/countdownDays",86]
["/data/weather/current/condition","多云"]
["/data/weather/current/temperatureC",29]
["/data/weather/location/cityCode","60814"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，86天后要去北京出差一周，展示还有几天出发、北京的天气，点一下能看北京天气详情。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCountdownDays",
        "arguments": {
          "targetDate": "2026-11-15"
        },
        "writeResultTo": "/data/countdown",
        "candidateOutputFields": [
          "/countdownDays"
        ]
      },
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "北京市",
          "forecastDays": 1
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/current/temperatureC",
          "/current/condition",
          "/location/cityCode"
        ]
      }
    ],
    "title": "出差倒计时",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.weather",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Weather_CityCode",
            "bundleName": "",
            "abilityName": "",
            "uri": "{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"
          }
        }
      }
    ],
    "description": "倒计时+目的地天气",
    "candidateAssetIds": [
      "asset.airplane_fill_1",
      "asset.icon_weather_thermometer",
      "asset.icon_timing",
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
    "interactionId": "042",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，86天后要去北京出差一周，展示还有几天出发、北京的天气，点一下能看北京天气详情。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，86天后要去北京出差一周，展示还有几天出发、北京的天气，点一下能看北京天气详情。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCountdownDays",
      "arguments": {
        "targetDate": "2026-11-15"
      },
      "writeResultTo": "/data/countdown",
      "candidateOutputFields": [
        "/countdownDays"
      ]
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "北京市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/current/temperatureC",
        "/current/condition",
        "/location/cityCode"
      ]
    }
  ],
  "title": "出差倒计时",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.weather",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Weather_CityCode",
          "bundleName": "",
          "abilityName": "",
          "uri": "{{ 'hww://www.huawei.com/totemweather?enterType=share&cityCode=' + ${/data/weather/location/cityCode} }}"
        }
      }
    }
  ],
  "description": "倒计时+目的地天气",
  "candidateAssetIds": [
    "asset.airplane_fill_1",
    "asset.icon_weather_thermometer",
    "asset.icon_timing",
    "asset.local_fill"
  ]
}
```
