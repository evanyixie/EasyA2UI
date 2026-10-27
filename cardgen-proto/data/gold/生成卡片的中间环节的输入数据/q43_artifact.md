```cardspec
{
  "title": "长沙关怀",
  "description": "天气预警+电话入口",
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
        "prefectureName": "长沙市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"长沙老家天气","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/bell_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["alert"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"alert","component":"Column","children":["alert_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"alert_main","component":"Text","content":"{{ ${/data/weather/current/alertLevel} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["weather_detail","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"weather_detail","component":"Column","children":["weather_detail_row0","weather_detail_row1"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"weather_detail_item0_label","component":"Text","content":"紫外线 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"weather_detail_item0_value","component":"Text","content":"{{ ${/data/weather/current/uvIndex} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_detail_item0","component":"Row","children":["weather_detail_item0_label","weather_detail_item0_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_detail_row0","component":"Row","children":["weather_detail_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"weather_detail_item1_label","component":"Text","content":"空气 ","styles":{"height":16,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3333333333333333,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"weather_detail_item1_value","component":"Text","content":"{{ ${/data/weather/current/airQuality} }}","styles":{"height":16.0,"fontSize":12,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3333333333333333,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"weather_detail_item1","component":"Row","children":["weather_detail_item1_label","weather_detail_item1_value"],"itemMargin":0,"styles":{"height":16.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"weather_detail_row1","component":"Row","children":["weather_detail_item1"],"itemMargin":0,"styles":{"width":"matchParent","height":16.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["call_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"call_action","component":"Stack","children":["call_action_icon"],"onClick":[{"call":"clickToApi","args":{"intentName":"CallPhone","params":{"phoneNumber":"1388888888"}}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#331F4799","alignContent":"center","clip":true}},{"id":"call_action_icon","component":"Image","src":"resources/base/media/phone_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"current":{"alertLevel":"大风蓝色预警","uvIndex":"中等","airQuality":"良"}}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，看看长沙老家天气预警、紫外线和空气，怕妈妈着凉，妈妈的号码是1388888888，点一下打开拨号界面并带上这个号码。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.call.phone",
      "description": "点击跳转至指定号码的拨号界面",
      "call": "clickToApi",
      "args": {
        "intentName": "CallPhone",
        "params": {
          "phoneNumber": "1388888888"
        }
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "weather": {
        "location": {
          "prefectureName": {
            "type": "string",
            "description": "城市名称",
            "sampleValue": "上海市"
          }
        },
        "current": {
          "alertLevel": {
            "type": "string",
            "description": "预警信息。当前气象预警信息，例如'暴雨橙色预警'、'高温黄色预警'、'台风蓝色预警'。无预警时为空字符串。",
            "sampleValue": "大风蓝色预警"
          },
          "uvIndex": {
            "type": "string",
            "description": "当前紫外线等级，例如“弱”“中等”“强”。",
            "sampleValue": "中等"
          },
          "airQuality": {
            "type": "string",
            "description": "当前空气质量等级，例如“优”“良”。",
            "sampleValue": "良"
          }
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.bell_fill",
      "src": "resources/base/media/bell_fill.svg",
      "description": "样式：默认黑色的单色实心铃铛图标，采用经典吊铃造型，底部带铃舌，原始尺寸为 24×24；适用：通知提醒、消息提示、备忘录提醒、闹钟响铃或开启状态，以及日历事项提醒。"
    },
    {
      "id": "asset.sun_max",
      "src": "resources/base/media/sun_max.svg",
      "description": "样式：默认黑色的单色线框太阳，中央大圆环，周围为八条较长放射线；适用：高亮度、强光、晴天或亮度增大。"
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
    "ViewWeather"
  ],
  "event": [
    {
      "id": "event.call.phone",
      "description": "点击跳转至指定号码的拨号界面",
      "call": "clickToApi",
      "args": {
        "intentName": "CallPhone",
        "params": {
          "phoneNumber": "1388888888"
        }
      }
    }
  ],
  "asset": [
    "asset.bell_fill",
    "asset.sun_max",
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
        "prefectureName": "长沙市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/location/prefectureName",
        "/current/alertLevel",
        "/current/uvIndex",
        "/current/airQuality"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.call.phone",
      "action": {
        "call": "clickToApi",
        "args": {
          "intentName": "CallPhone",
          "params": {
            "phoneNumber": "1388888888"
          }
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.bell_fill",
    "asset.sun_max",
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
  "artifactId": "82f8a2b8-b45e-48b3-8cbc-b39c4e352615",
  "createdAt": 1792045569049
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["title_area","alert","weather_detail","call_action"]]
["title_area","SingleLineTitle",{"title":"长沙老家天气","icon":"resources/base/media/bell_fill.svg","fontSize":12}]
["alert","EmphasisText",{"mainText":{"path":"/data/weather/current/alertLevel"},"fontSize":18}]
["weather_detail","SecondaryBody",{"items":[{"label":"紫外线 ","value":{"path":"/data/weather/current/uvIndex"}},{"label":"空气 ","value":{"path":"/data/weather/current/airQuality"}}],"fontSize":14}]
["call_action","CircleButton",{"icon":"resources/base/media/phone_fill.svg","accessibility":{"label":"打开拨号界面拨打妈妈号码"},"onClick":[{"call":"clickToApi","args":{"intentName":"CallPhone","params":{"phoneNumber":"1388888888"}}}]}]
["/data/weather/current/alertLevel","大风蓝色预警"]
["/data/weather/current/uvIndex","中等"]
["/data/weather/current/airQuality","良"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，看看长沙老家天气预警、紫外线和空气，怕妈妈着凉，妈妈的号码是1388888888，点一下打开拨号界面并带上这个号码。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "长沙市",
          "forecastDays": 1
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/location/prefectureName",
          "/current/alertLevel",
          "/current/uvIndex",
          "/current/airQuality"
        ]
      }
    ],
    "title": "长沙关怀",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.call.phone",
        "action": {
          "call": "clickToApi",
          "args": {
            "intentName": "CallPhone",
            "params": {
              "phoneNumber": "1388888888"
            }
          }
        }
      }
    ],
    "description": "天气预警+电话入口",
    "candidateAssetIds": [
      "asset.bell_fill",
      "asset.sun_max",
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
    "interactionId": "043",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，看看长沙老家天气预警、紫外线和空气，怕妈妈着凉，妈妈的号码是1388888888，点一下打开拨号界面并带上这个号码。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，看看长沙老家天气预警、紫外线和空气，怕妈妈着凉，妈妈的号码是1388888888，点一下打开拨号界面并带上这个号码。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "长沙市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/location/prefectureName",
        "/current/alertLevel",
        "/current/uvIndex",
        "/current/airQuality"
      ]
    }
  ],
  "title": "长沙关怀",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.call.phone",
      "action": {
        "call": "clickToApi",
        "args": {
          "intentName": "CallPhone",
          "params": {
            "phoneNumber": "1388888888"
          }
        }
      }
    }
  ],
  "description": "天气预警+电话入口",
  "candidateAssetIds": [
    "asset.bell_fill",
    "asset.sun_max",
    "asset.phone_fill"
  ]
}
```
