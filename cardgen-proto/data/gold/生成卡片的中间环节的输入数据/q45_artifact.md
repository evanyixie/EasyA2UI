```cardspec
{
  "title": "深圳天气电量",
  "description": "天气温度+手机电量温度",
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
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"深圳 · 手机","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/phone_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["weather"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"weather","component":"Column","children":["weather_main","weather_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"weather_main","component":"Text","content":"{{ ${/data/weather/current/condition} + ' ' + ${/data/weather/current/temperatureC} + '℃' }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"weather_secondary","component":"Text","content":"天气","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#991F4799","textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["battery"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"battery","component":"Column","children":["battery_row0","battery_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"battery_item0_label","component":"Text","content":"手机电量 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"battery_item0_value","component":"Text","content":"{{ ${/data/phoneBattery/batterySOC} + '%' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"battery_item0","component":"Row","children":["battery_item0_label","battery_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"battery_row0","component":"Row","children":["battery_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"battery_item1_label","component":"Text","content":"电池温度 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"battery_item1_value","component":"Text","content":"{{ ${/data/phoneBattery/batteryTemperatureText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"battery_item1","component":"Row","children":["battery_item1_label","battery_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"battery_row1","component":"Row","children":["battery_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"current":{"condition":"多云","temperatureC":29}},"phoneBattery":{"batterySOC":68,"batteryTemperatureText":"29.0 ℃"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，上面要有深圳现在天气现象、多少度和手机电量怎么样，还有当前的电池温度",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
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
          }
        }
      },
      "phoneBattery": {
        "batterySOC": {
          "type": "integer",
          "description": "当前手机设备剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”。若直接用于文本展示，必须在数值后追加“%”；优先使用 batterySOCText。",
          "sampleValue": 68
        },
        "batteryTemperatureText": {
          "type": "string",
          "description": "可直接显示的当前设备电池实时温度文本，已包含“℃”单位；展示时不得再次追加温度单位。",
          "sampleValue": "29.0 ℃"
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
      "id": "asset.battery_leaf_fill",
      "src": "resources/base/media/battery_leaf_fill.svg",
      "description": "样式：默认黑色的单色实心横向电池图标，电池内部为叶片留白；适用：电池相关场景，包括电量、省电模式、节能电池、绿色用电状态，也可作为电池健康或电池温度信息的辅助图标，相关数据可结合 GetPhoneBatteryInfo 展示。图标本身不表示具体电量、健康等级或温度高低。"
    },
    {
      "id": "asset.heat_generation",
      "src": "resources/base/media/heat_generation.svg",
      "description": "样式：默认黑色的单色线框温度计，底部为圆形感温泡，内部带弧形刻度；适用：温度、升温、制热或体感温度。"
    },
    {
      "id": "asset.phone_fill",
      "src": "resources/base/media/phone_fill.svg",
      "description": "样式：电话实心图标，默认黑色，图形为经典听筒造型；适用：拨打电话、通话功能入口。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "ViewWeather",
    "GetPhoneBatteryInfo"
  ],
  "event": [],
  "asset": [
    "asset.icon_weather_thermometer",
    "asset.battery_leaf_fill",
    "asset.heat_generation",
    "asset.phone_fill"
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
        "/current/temperatureC"
      ]
    },
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC",
        "/batteryTemperatureText"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.icon_weather_thermometer",
    "asset.battery_leaf_fill",
    "asset.heat_generation",
    "asset.phone_fill"
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
  "artifactId": "1d34b9a3-dfaa-40c2-a769-98b9d138af80",
  "createdAt": 1792045578334
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","weather","battery"]]
["header","SingleLineTitle",{"title":"深圳 · 手机","icon":"resources/base/media/phone_fill.svg","fontSize":12}]
["weather","EmphasisText",{"mainText":"{{ ${/data/weather/current/condition} + ' ' + ${/data/weather/current/temperatureC} + '℃' }}","secondaryText":"天气","fontSize":18}]
["battery","SecondaryBody",{"items":[{"label":"手机电量 ","value":"{{ ${/data/phoneBattery/batterySOC} + '%' }}"},{"label":"电池温度 ","value":{"path":"/data/phoneBattery/batteryTemperatureText"}}],"columns":1,"fontSize":12}]
["/data/weather/current/condition","多云"]
["/data/weather/current/temperatureC",29]
["/data/phoneBattery/batterySOC",68]
["/data/phoneBattery/batteryTemperatureText","29.0 ℃"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，上面要有深圳现在天气现象、多少度和手机电量怎么样，还有当前的电池温度",
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
          "/current/temperatureC"
        ]
      },
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/batterySOC",
          "/batteryTemperatureText"
        ]
      }
    ],
    "title": "深圳天气电量",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "天气温度+手机电量温度",
    "candidateAssetIds": [
      "asset.icon_weather_thermometer",
      "asset.battery_leaf_fill",
      "asset.heat_generation",
      "asset.phone_fill"
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
    "interactionId": "045",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，上面要有深圳现在天气现象、多少度和手机电量怎么样，还有当前的电池温度",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，上面要有深圳现在天气现象、多少度和手机电量怎么样，还有当前的电池温度",
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
        "/current/temperatureC"
      ]
    },
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC",
        "/batteryTemperatureText"
      ]
    }
  ],
  "title": "深圳天气电量",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "天气温度+手机电量温度",
  "candidateAssetIds": [
    "asset.icon_weather_thermometer",
    "asset.battery_leaf_fill",
    "asset.heat_generation",
    "asset.phone_fill"
  ]
}
```
