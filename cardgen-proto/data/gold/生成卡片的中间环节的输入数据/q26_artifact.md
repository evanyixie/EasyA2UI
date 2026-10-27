```cardspec
{
  "title": "西安出行",
  "description": "倒数天气和详情",
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
        "targetDate": "2026-09-01"
      },
      "writeResultTo": "/data/countdown"
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "西安市",
        "districtName": "雁塔区",
        "forecastDays": 5
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"西安出差","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/airplane_departure.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["countdown"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"countdown","component":"Column","children":["countdown_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"countdown_main","component":"Text","content":"{{ '距出发 ' + ${/data/countdown/countdownDays} + ' 天' }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["weather_info","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"weather_info","component":"Column","children":["weather_info_row0","weather_info_row1","weather_info_row2"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"weather_info_item0_label","component":"Text","content":"天气 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"weather_info_item0_value","component":"Text","content":"{{ ${/data/weather/daily/4/condition} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_info_item0","component":"Row","children":["weather_info_item0_label","weather_info_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_info_row0","component":"Row","children":["weather_info_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"weather_info_item1_value","component":"Text","content":"{{ '温度 ' + ${/data/weather/daily/4/temperatureRangeText} }}","styles":{"height":32.0,"fontSize":12,"fontWeight":400,"maxLines":2,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_info_item1","component":"Row","children":["weather_info_item1_value"],"itemMargin":0,"styles":{"height":32.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_info_row1","component":"Row","children":["weather_info_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":32.0,"alignItems":"top","flexShrink":0}},{"id":"weather_info_item2_label","component":"Text","content":"降雨 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"weather_info_item2_value","component":"Text","content":"{{ ${/data/weather/daily/4/rainProbabilityPercent} + '%' }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_info_item2","component":"Row","children":["weather_info_item2_label","weather_info_item2_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_info_row2","component":"Row","children":["weather_info_item2"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["alarm_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"alarm_action","component":"Stack","children":["alarm_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#331F4799","alignContent":"center","clip":true}},{"id":"alarm_action_icon","component":"Image","src":"resources/base/media/alarm_fill_1.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"countdown":{"countdownDays":30},"weather":{"daily":[null,null,null,null,{"condition":"多云","temperatureRangeText":"25℃ / 32℃","rainProbabilityPercent":20}]}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "4天后要去西安市雁塔区出差，帮我做个卡片，看还有几天出发和当天的天气、温度范围、下雨概率，点一下打开闹钟应用设置出发提醒。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.clock.alarm",
      "description": "打开闹钟应用首页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Clock",
        "bundleName": "com.huawei.hmos.clock",
        "abilityName": "com.huawei.hmos.clock.phone",
        "uri": ""
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
        "daily": [
          {},
          {},
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
      "id": "asset.drop_1",
      "src": "resources/base/media/drop_1.svg",
      "description": "样式：双水滴实心图标，默认黑色，图形为左侧较大水滴与右侧较小水滴错位叠放，顶部尖收、底部圆润；适用：湿度数据展示、饮水提醒、天气降雨信息。"
    },
    {
      "id": "asset.alarm_fill_1",
      "src": "resources/base/media/alarm_fill_1.svg",
      "description": "样式：默认黑色的单色闹钟实心图标，内部通过镂空表现表盘指针，支持通过 fillColor 与卡片配色统一；适用：闹钟设置、定时提醒、日程提醒。"
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
      "id": "event.open.clock.alarm",
      "description": "打开闹钟应用首页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Clock",
        "bundleName": "com.huawei.hmos.clock",
        "abilityName": "com.huawei.hmos.clock.phone",
        "uri": ""
      }
    }
  ],
  "asset": [
    "asset.airplane_departure",
    "asset.sun_max",
    "asset.drop_1",
    "asset.alarm_fill_1"
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
        "targetDate": "2026-09-01"
      },
      "writeResultTo": "/data/countdown",
      "candidateOutputFields": [
        "/countdownDays"
      ]
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "西安市",
        "districtName": "雁塔区",
        "forecastDays": 5
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/4/condition",
        "/daily/4/temperatureRangeText",
        "/daily/4/rainProbabilityPercent"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.clock.alarm",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Clock",
          "bundleName": "com.huawei.hmos.clock",
          "abilityName": "com.huawei.hmos.clock.phone",
          "uri": ""
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.airplane_departure",
    "asset.sun_max",
    "asset.drop_1",
    "asset.alarm_fill_1"
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
  "artifactId": "74f09e33-7bde-404b-a595-f40a4be2fb47",
  "createdAt": 1792045475080
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["title_area","countdown","weather_info","alarm_action"]]
["title_area","SingleLineTitle",{"title":"西安出差","icon":"resources/base/media/airplane_departure.svg","fontSize":12}]
["countdown","EmphasisText",{"mainText":"{{ '距出发 ' + ${/data/countdown/countdownDays} + ' 天' }}","fontSize":18}]
["weather_info","SecondaryBody",{"items":[{"label":"天气 ","value":{"path":"/data/weather/daily/4/condition"}},{"label":"温度 ","value":{"path":"/data/weather/daily/4/temperatureRangeText"}},{"label":"降雨 ","value":"{{ ${/data/weather/daily/4/rainProbabilityPercent} + '%' }}"}],"columns":1,"fontSize":12}]
["alarm_action","CircleButton",{"icon":"resources/base/media/alarm_fill_1.svg","accessibility":{"label":"打开闹钟应用设置出发提醒"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Clock","bundleName":"com.huawei.hmos.clock","abilityName":"com.huawei.hmos.clock.phone","uri":""}}]}]
["/data/countdown/countdownDays",30]
["/data/weather/daily/4/condition","多云"]
["/data/weather/daily/4/temperatureRangeText","25℃ / 32℃"]
["/data/weather/daily/4/rainProbabilityPercent",20]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "4天后要去西安市雁塔区出差，帮我做个卡片，看还有几天出发和当天的天气、温度范围、下雨概率，点一下打开闹钟应用设置出发提醒。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetCountdownDays",
        "arguments": {
          "targetDate": "2026-09-01"
        },
        "writeResultTo": "/data/countdown",
        "candidateOutputFields": [
          "/countdownDays"
        ]
      },
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "西安市",
          "districtName": "雁塔区",
          "forecastDays": 5
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/daily/4/condition",
          "/daily/4/temperatureRangeText",
          "/daily/4/rainProbabilityPercent"
        ]
      }
    ],
    "title": "西安出行",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.clock.alarm",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Clock",
            "bundleName": "com.huawei.hmos.clock",
            "abilityName": "com.huawei.hmos.clock.phone",
            "uri": ""
          }
        }
      }
    ],
    "description": "倒数天气和详情",
    "candidateAssetIds": [
      "asset.airplane_departure",
      "asset.sun_max",
      "asset.drop_1",
      "asset.alarm_fill_1"
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
    "interactionId": "026",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "4天后要去西安市雁塔区出差，帮我做个卡片，看还有几天出发和当天的天气、温度范围、下雨概率，点一下打开闹钟应用设置出发提醒。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "4天后要去西安市雁塔区出差，帮我做个卡片，看还有几天出发和当天的天气、温度范围、下雨概率，点一下打开闹钟应用设置出发提醒。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetCountdownDays",
      "arguments": {
        "targetDate": "2026-09-01"
      },
      "writeResultTo": "/data/countdown",
      "candidateOutputFields": [
        "/countdownDays"
      ]
    },
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "西安市",
        "districtName": "雁塔区",
        "forecastDays": 5
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/daily/4/condition",
        "/daily/4/temperatureRangeText",
        "/daily/4/rainProbabilityPercent"
      ]
    }
  ],
  "title": "西安出行",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.clock.alarm",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Clock",
          "bundleName": "com.huawei.hmos.clock",
          "abilityName": "com.huawei.hmos.clock.phone",
          "uri": ""
        }
      }
    }
  ],
  "description": "倒数天气和详情",
  "candidateAssetIds": [
    "asset.airplane_departure",
    "asset.sun_max",
    "asset.drop_1",
    "asset.alarm_fill_1"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-primary-secondary-action\",\"variant\":\"dense\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"title_area\",\"countdown\",\"weather_info\",\"alarm_action\"]]\n[\"title_area\",\"SingleLineTitle\",{\"title\":\"西安出差\",\"icon\":\"resources/base/media/airplane_departure.svg\",\"fontSize\":12}]\n[\"countdown\",\"EmphasisText\",{\"mainText\":\"{{ '距出发 ' + ${/data/countdown/countdownDays} + ' 天' }}\",\"secondaryText\":\"西安市雁塔区\",\"fontSize\":18}]\n[\"weather_info\",\"SecondaryBody\",{\"items\":[{\"label\":\"天气 \",\"value\":{\"path\":\"/data/weather/daily/4/condition\"}},{\"label\":\"温度 \",\"value\":{\"path\":\"/data/weather/daily/4/temperatureRangeText\"}},{\"label\":\"降雨 \",\"value\":\"{{ ${/data/weather/daily/4/rainProbabilityPercent} + '%' }}\"}],\"columns\":1,\"fontSize\":12}]\n[\"alarm_action\",\"PillButton\",{\"label\":\"设置出发提醒\",\"icon\":\"resources/base/media/alarm_fill_1.svg\",\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Clock\",\"bundleName\":\"com.huawei.hmos.clock\",\"abilityName\":\"com.huawei.hmos.clock.phone\",\"uri\":\"\"}}]}]\n[\"/data/countdown/countdownDays\",30]\n[\"/data/weather/daily/4/condition\",\"多云\"]\n[\"/data/weather/daily/4/temperatureRangeText\",\"25℃ / 32℃\"]\n[\"/data/weather/daily/4/rainProbabilityPercent\",20]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component root: vertical layout requires at least 164vp within 126vp; it overflows by 38vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: title_area=20vp+margin(0vp), __layout__root__body=140vp+margin(0vp), gaps=4vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component root: vertical layout requires at least 164vp within 126vp; it overflows by 38vp. Occupancy: title_area=20vp+margin(0vp), __layout__root__body=140vp+margin(0vp), gaps=4vp.",
          "legacyMessage": "component root: vertical layout requires at least 164vp within 126vp; it overflows by 38vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: title_area=20vp+margin(0vp), __layout__root__body=140vp+margin(0vp), gaps=4vp.",
          "expected": {
            "maximumHeight": 126.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 164.0,
            "overflow": 38.0,
            "occupancy": "title_area=20vp+margin(0vp), __layout__root__body=140vp+margin(0vp), gaps=4vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__body: vertical layout requires at least 140vp within 102vp; it overflows by 38vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=96vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__body: vertical layout requires at least 140vp within 102vp; it overflows by 38vp. Occupancy: __layout__root__primary_support=96vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "legacyMessage": "component __layout__root__body: vertical layout requires at least 140vp within 102vp; it overflows by 38vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: __layout__root__primary_support=96vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp.",
          "expected": {
            "maximumHeight": 102.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 140.0,
            "overflow": 38.0,
            "occupancy": "__layout__root__primary_support=96vp+margin(0vp), __layout__root__action=36vp+margin(0vp), gaps=8vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    },
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "component __layout__root__primary_support: vertical layout requires at least 96vp within 58vp; it overflows by 38vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: countdown=42vp+margin(0vp), weather_info=52vp+margin(0vp), gaps=2vp.",
      "compactDiagnostics": [
        {
          "code": "COMPACT_LAYOUT_HEIGHT_OVERFLOW",
          "validationClass": "semantic",
          "category": "layout",
          "severity": "error",
          "message": "component __layout__root__primary_support: vertical layout requires at least 96vp within 58vp; it overflows by 38vp. Occupancy: countdown=42vp+margin(0vp), weather_info=52vp+margin(0vp), gaps=2vp.",
          "legacyMessage": "component __layout__root__primary_support: vertical layout requires at least 96vp within 58vp; it overflows by 38vp. Regroup facts or choose a layout with enough body space; preserve required text, actions, font sizes and fixed design heights. Weight, clipping, flex shrink and distributed alignment cannot eliminate content height. Occupancy: countdown=42vp+margin(0vp), weather_info=52vp+margin(0vp), gaps=2vp.",
          "expected": {
            "maximumHeight": 58.0,
            "heightTolerance": 2.0,
            "preserveFixedDesignSizes": true,
            "preserveRequiredTextAndActions": true,
            "overflowConstraint": "不能依靠权重、裁剪、flex shrink 或分布式对齐消除内容高度超限。"
          },
          "actual": {
            "minimumRequiredHeight": 96.0,
            "overflow": 38.0,
            "occupancy": "countdown=42vp+margin(0vp), weather_info=52vp+margin(0vp), gaps=2vp"
          },
          "evidenceSource": "expanded",
          "componentId": "root",
          "sourceLine": 1,
          "fixHint": "根据占用明细重新组合完整信息或选择合法布局，保留必要事实、动作、字号和固定设计高度；不能靠裁剪、收缩或调整权重消除负预算。"
        }
      ]
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-anchor\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"title_area\",\"countdown\",\"weather_info\",\"alarm_action\"]]\n[\"title_area\",\"SingleLineTitle\",{\"title\":\"西安出差\",\"icon\":\"resources/base/media/airplane_departure.svg\",\"fontSize\":12}]\n[\"countdown\",\"EmphasisText\",{\"mainText\":\"{{ '距出发 ' + ${/data/countdown/countdownDays} + ' 天' }}\",\"fontSize\":18}]\n[\"weather_info\",\"SecondaryBody\",{\"items\":[{\"label\":\"天气 \",\"value\":{\"path\":\"/data/weather/daily/4/condition\"}},{\"label\":\"温度 \",\"value\":{\"path\":\"/data/weather/daily/4/temperatureRangeText\"}},{\"label\":\"降雨 \",\"value\":\"{{ ${/data/weather/daily/4/rainProbabilityPercent} + '%' }}\"}],\"columns\":1,\"fontSize\":12}]\n[\"alarm_action\",\"CircleButton\",{\"icon\":\"resources/base/media/alarm_fill_1.svg\",\"accessibility\":{\"label\":\"打开闹钟应用设置出发提醒\"},\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Clock\",\"bundleName\":\"com.huawei.hmos.clock\",\"abilityName\":\"com.huawei.hmos.clock.phone\",\"uri\":\"\"}}]}]\n[\"/data/countdown/countdownDays\",30]\n[\"/data/weather/daily/4/condition\",\"多云\"]\n[\"/data/weather/daily/4/temperatureRangeText\",\"25℃ / 32℃\"]\n[\"/data/weather/daily/4/rainProbabilityPercent\",20]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"title_area\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"title_area\",\"component\":\"Row\",\"children\":[\"title_area_title\",\"title_area_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"title_area_title\",\"component\":\"Text\",\"content\":\"西安出差\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"title_area_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/airplane_departure.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__primary\",\"__layout__root__bottom\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__primary\",\"component\":\"Column\",\"children\":[\"countdown\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"countdown\",\"component\":\"Column\",\"children\":[\"countdown_main\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"countdown_main\",\"component\":\"Text\",\"content\":\"{{ '距出发 ' + ${/data/countdown/countdownDays} + ' 天' }}\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"__layout__root__bottom\",\"component\":\"Row\",\"children\":[\"weather_info\",\"__layout__root__action_slot\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":40,\"flexShrink\":0,\"alignItems\":\"bottom\",\"justifyContent\":\"spaceBetween\"}},{\"id\":\"weather_info\",\"component\":\"Column\",\"children\":[\"weather_info_row0\",\"weather_info_row1\",\"weather_info_row2\"],\"itemMargin\":2,\"styles\":{\"width\":78,\"alignItems\":\"start\",\"flexShrink\":1}},{\"id\":\"weather_info_item0_label\",\"component\":\"Text\",\"content\":\"天气 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/weather/daily/4/condition} }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item0\",\"component\":\"Row\",\"children\":[\"weather_info_item0_label\",\"weather_info_item0_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"weather_info_row0\",\"component\":\"Row\",\"children\":[\"weather_info_item0\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"weather_info_item1_value\",\"component\":\"Text\",\"content\":\"{{ '温度 ' + ${/data/weather/daily/4/temperatureRangeText} }}\",\"styles\":{\"height\":32.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":2,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item1\",\"component\":\"Row\",\"children\":[\"weather_info_item1_value\"],\"itemMargin\":0,\"styles\":{\"height\":32.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"weather_info_row1\",\"component\":\"Row\",\"children\":[\"weather_info_item1\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":32.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"weather_info_item2_label\",\"component\":\"Text\",\"content\":\"降雨 \",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":0,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item2_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/weather/daily/4/rainProbabilityPercent} + '%' }}\",\"styles\":{\"height\":16.0,\"fontSize\":12,\"fontWeight\":400,\"maxLines\":1,\"flexShrink\":1,\"lineHeight\":1.3333333333333333,\"fontColor\":\"#991F4799\",\"layoutWeight\":1,\"textOverflow\":\"clip\"}},{\"id\":\"weather_info_item2\",\"component\":\"Row\",\"children\":[\"weather_info_item2_label\",\"weather_info_item2_value\"],\"itemMargin\":0,\"styles\":{\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1}},{\"id\":\"weather_info_row2\",\"component\":\"Row\",\"children\":[\"weather_info_item2\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":16.0,\"alignItems\":\"top\",\"flexShrink\":0}},{\"id\":\"__layout__root__action_slot\",\"component\":\"Stack\",\"children\":[\"alarm_action\"],\"styles\":{\"width\":40,\"height\":40,\"alignContent\":\"center\"}},{\"id\":\"alarm_action\",\"component\":\"Stack\",\"children\":[\"alarm_action_icon\"],\"onClick\":[{\"call\":\"clickToDeeplink\",\"args\":{\"intentName\":\"Clock\",\"bundleName\":\"com.huawei.hmos.clock\",\"abilityName\":\"com.huawei.hmos.clock.phone\",\"uri\":\"\"}}],\"styles\":{\"width\":40,\"height\":40,\"borderRadius\":20,\"padding\":0,\"flexShrink\":0,\"backgroundColor\":\"#331F4799\",\"alignContent\":\"center\",\"clip\":true}},{\"id\":\"alarm_action_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/alarm_fill_1.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"countdown\":{\"countdownDays\":30},\"weather\":{\"daily\":[null,null,null,null,{\"condition\":\"多云\",\"temperatureRangeText\":\"25℃ / 32℃\",\"rainProbabilityPercent\":20}]}}}}}",
  "validationErrors": []
}
```
