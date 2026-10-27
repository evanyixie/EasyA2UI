```cardspec
{
  "title": "北京出差",
  "description": "出发倒数和天气",
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
        "targetDate": "2026-08-30"
      },
      "writeResultTo": "/data/countdown"
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "北京市",
        "forecastDays": 3
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"北京出差","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#998C4B1C"}},{"id":"header_icon","component":"Image","src":"resources/base/media/airplane_departure.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF8C4B1C"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["countdown"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"countdown","component":"Row","children":["countdown_value","countdown_unit"],"itemMargin":2,"styles":{"justifyContent":"start","alignItems":"bottom","flexShrink":0,"width":"matchParent"}},{"id":"countdown_value","component":"Text","content":"{{ ${/data/countdown/countdownDays} }}","styles":{"height":30,"fontSize":30,"fontWeight":700,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"countdown_unit","component":"Text","content":"天","styles":{"height":13.75,"fontSize":12,"fontWeight":500,"lineHeight":1,"maxLines":1,"flexShrink":0,"fontColor":"#998C4B1C","padding":{"top":0,"right":0,"bottom":1.75,"left":0},"textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["weather_info"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"weather_info","component":"Column","children":["weather_info_row0","weather_info_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"weather_info_item0_label","component":"Text","content":"天气 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"weather_info_item0_value","component":"Text","content":"{{ ${/data/weather/daily/2/condition} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_info_item0","component":"Row","children":["weather_info_item0_label","weather_info_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_info_row0","component":"Row","children":["weather_info_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"weather_info_item1_label","component":"Text","content":"温度 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF8C4B1C","textOverflow":"clip"}},{"id":"weather_info_item1_value","component":"Text","content":"{{ ${/data/weather/daily/2/temperatureRangeText} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#998C4B1C","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_info_item1","component":"Row","children":["weather_info_item1_label","weather_info_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_info_row1","component":"Row","children":["weather_info_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"countdown":{"countdownDays":30},"weather":{"daily":[null,null,{"condition":"多云","temperatureRangeText":"25℃ / 32℃"}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "2天后要去北京出差，帮我做个卡片，看还有几天出发和北京当天的天气、温度范围。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
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
        "daily": [
          {},
          {},
          {
            "condition": {
              "type": "string",
              "description": "白天天气现象，来源于weather_icon。",
              "sampleValue": "多云"
            },
            "temperatureRangeText": {
              "type": "string",
              "description": "可直接显示的最低温与最高温范围文本，每个温度值均已包含“℃”单位；展示时不得再次追加温度单位。例如“25℃ / 32℃”。",
              "sampleValue": "25℃ / 32℃"
            }
          }
        ]
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.airplane_departure",
      "src": "resources/base/media/airplane_departure.svg",
      "description": "样式：飞机起飞图标，默认黑色，图形为飞机从跑道起飞的侧视图；适用：出行计划、航班出发信息、旅行日程。"
    },
    {
      "id": "asset.sun_max",
      "src": "resources/base/media/sun_max.svg",
      "description": "样式：默认黑色的单色线框太阳，中央大圆环，周围为八条较长放射线；适用：高亮度、强光、晴天或亮度增大。"
    },
    {
      "id": "asset.icon_timing",
      "src": "resources/base/media/icon_timing.svg",
      "description": "样式：默认白色的单色秒表实心图标，内部通过镂空表现表盘指针，支持通过 fillColor 与卡片配色统一；适用：计时、使用时长、倒计时或时限。"
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
    "GetCountdownDays",
    "ViewWeather"
  ],
  "event": [],
  "asset": [
    "asset.airplane_departure",
    "asset.sun_max",
    "asset.icon_timing",
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
      "capabilityId": "GetCountdownDays",
      "arguments": {
        "targetDate": "2026-08-30"
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
        "forecastDays": 3
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/2/condition",
        "/daily/2/temperatureRangeText"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.airplane_departure",
    "asset.sun_max",
    "asset.icon_timing",
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
  "artifactId": "5be7b262-d917-4dc1-91ca-5777fc60e6e6",
  "createdAt": 1792045380929
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFFFE0CC",0],["#FFFFF7F2",1]]}},["header","countdown","weather_info"]]
["header","SingleLineTitle",{"title":"北京出差","icon":"resources/base/media/airplane_departure.svg","fontSize":12}]
["countdown","EmphasizedData",{"value":{"path":"/data/countdown/countdownDays"},"unit":"天","fontSize":30}]
["weather_info","SecondaryBody",{"items":[{"label":"天气 ","value":{"path":"/data/weather/daily/2/condition"}},{"label":"温度 ","value":{"path":"/data/weather/daily/2/temperatureRangeText"}}],"separator":" | ","fontSize":14}]
["/data/countdown/countdownDays",30]
["/data/weather/daily/2/condition","多云"]
["/data/weather/daily/2/temperatureRangeText","25℃ / 32℃"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "2天后要去北京出差，帮我做个卡片，看还有几天出发和北京当天的天气、温度范围。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCountdownDays",
        "arguments": {
          "targetDate": "2026-08-30"
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
          "forecastDays": 3
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/daily/2/condition",
          "/daily/2/temperatureRangeText"
        ]
      }
    ],
    "title": "北京出差",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "出发倒数和天气",
    "candidateAssetIds": [
      "asset.airplane_departure",
      "asset.sun_max",
      "asset.icon_timing",
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
    "interactionId": "008",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "2天后要去北京出差，帮我做个卡片，看还有几天出发和北京当天的天气、温度范围。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "2天后要去北京出差，帮我做个卡片，看还有几天出发和北京当天的天气、温度范围。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCountdownDays",
      "arguments": {
        "targetDate": "2026-08-30"
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
        "forecastDays": 3
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/2/condition",
        "/daily/2/temperatureRangeText"
      ]
    }
  ],
  "title": "北京出差",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "出发倒数和天气",
  "candidateAssetIds": [
    "asset.airplane_departure",
    "asset.sun_max",
    "asset.icon_timing",
    "asset.calendar_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}},[\"header\",\"countdown\",\"weather_info\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"北京出差\",\"icon\":\"resources/base/media/airplane_departure.svg\",\"fontSize\":12}]\n[\"countdown\",\"EmphasizedData\",{\"value\":{\"path\":\"/data/countdown/countdownDays\"},\"unit\":\"天\",\"fontSize\":30}]\n[\"weather_info\",\"SecondaryBody\",{\"items\":[{\"label\":\"天气 \",\"value\":{\"path\":\"/data/weather/daily/2/condition\"}},{\"label\":\"温度 \",\"value\":{\"path\":\"/data/weather/daily/2/temperatureRangeText\"}}],\"separator\":\" | \",\"fontSize\":14}]\n[\"/data/countdown/countdownDays\",30]\n[\"/data/weather/daily/2/condition\",\"多云\"]\n[\"/data/weather/daily/2/temperatureRangeText\",\"25℃ / 32℃\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFFFE0CC\",0],[\"#FFFFF7F2\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"北京出差\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#998C4B1C\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/airplane_departure.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF8C4B1C\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__primary\",\"__layout__root__support\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__primary\",\"component\":\"Column\",\"children\":[\"countdown\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"countdown\",\"component\":\"Row\",\"children\":[\"countdown_value\",\"countdown_unit\"],\"itemMargin\":2,\"styles\":{\"justifyContent\":\"start\",\"alignItems\":\"bottom\",\"flexShrink\":0,\"width\":\"matchParent\"}},{\"id\":\"countdown_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/countdown/countdownDays} }}\",\"styles\":{\"height\":30,\"fontSize\":30,\"fontWeight\":700,\"lineHeight\":1,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"countdown_unit\",\"component\":\"Text\",\"content\":\"天\",\"styles\":{\"height\":13.75,\"fontSize\":12,\"fontWeight\":500,\"lineHeight\":1,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#998C4B1C\",\"padding\":{\"top\":0,\"right\":0,\"bottom\":1.75,\"left\":0},\"textOverflow\":\"clip\"}},{\"id\":\"__layout__root__support\",\"component\":\"Column\",\"children\":[\"weather_info\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"end\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"weather_info\",\"component\":\"Column\",\"children\":[\"weather_info_row0\",\"weather_info_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"weather_info_item0_label\",\"component\":\"Text\",\"content\":\"天气 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/weather/daily/2/condition} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item0\",\"component\":\"Row\",\"children\":[\"weather_info_item0_label\",\"weather_info_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"weather_info_row0\",\"component\":\"Row\",\"children\":[\"weather_info_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"weather_info_item1_label\",\"component\":\"Text\",\"content\":\"温度 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF8C4B1C\",\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/weather/daily/2/temperatureRangeText} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#998C4B1C\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item1\",\"component\":\"Row\",\"children\":[\"weather_info_item1_label\",\"weather_info_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"weather_info_row1\",\"component\":\"Row\",\"children\":[\"weather_info_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"countdown\":{\"countdownDays\":30},\"weather\":{\"daily\":[null,null,{\"condition\":\"多云\",\"temperatureRangeText\":\"25℃ / 32℃\"}]}}}}}",
  "validationErrors": []
}
```
