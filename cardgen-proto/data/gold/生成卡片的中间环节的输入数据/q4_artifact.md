```cardspec
{
  "title": "天气预警",
  "description": "预警",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__content"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"长沙天气预警","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/bell_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__content","component":"Column","children":["alert"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"alert","component":"Column","children":["alert_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"alert_main","component":"Text","content":"{{ ${/data/weather/current/alertLevel} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"weather":{"current":{"alertLevel":"大风蓝色预警"}}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个天气预警卡片，重点看长沙当前天气预警。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "weather": {
        "current": {
          "alertLevel": {
            "type": "string",
            "description": "预警信息。当前气象预警信息，例如'暴雨橙色预警'、'高温黄色预警'、'台风蓝色预警'。无预警时为空字符串。",
            "sampleValue": "大风蓝色预警"
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
      "id": "asset.clock",
      "src": "resources/base/media/clock.svg",
      "description": "样式：时钟线框图标，默认黑色，图形为圆形表盘加指针的线性轮廓；适用：时间显示、定时功能、倒计时。"
    },
    {
      "id": "asset.typhoon_fill",
      "src": "resources/base/media/typhoon_fill.svg",
      "description": "样式：台风黑色图标，图形为台风漩涡造型；适用：台风预警、台风路径。"
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
    "asset.bell_fill",
    "asset.clock",
    "asset.typhoon_fill"
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
        "/current/alertLevel"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.bell_fill",
    "asset.clock",
    "asset.typhoon_fill"
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
  "artifactId": "82f9d2d4-06dd-4495-9e57-208e570cdb2d",
  "createdAt": 1792045365764
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","alert"]]
["header","SingleLineTitle",{"title":"长沙天气预警","icon":"resources/base/media/bell_fill.svg","fontSize":12}]
["alert","EmphasisText",{"mainText":{"path":"/data/weather/current/alertLevel"},"fontSize":18}]
["/data/weather/current/alertLevel","大风蓝色预警"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个天气预警卡片，重点看长沙当前天气预警。",
    "candidateDataBindings": [
      {
        "capabilityId": "ViewWeather",
        "arguments": {
          "prefectureName": "长沙市",
          "forecastDays": 1
        },
        "writeResultTo": "/data/weather",
        "candidateOutputFields": [
          "/current/alertLevel"
        ]
      }
    ],
    "title": "天气预警",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "预警",
    "candidateAssetIds": [
      "asset.bell_fill",
      "asset.clock",
      "asset.typhoon_fill"
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
    "interactionId": "004",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个天气预警卡片，重点看长沙当前天气预警。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个天气预警卡片，重点看长沙当前天气预警。",
  "candidateDataBindings": [
    {
      "capabilityId": "ViewWeather",
      "arguments": {
        "prefectureName": "长沙市",
        "forecastDays": 1
      },
      "writeResultTo": "/data/weather",
      "candidateOutputFields": [
        "/current/alertLevel"
      ]
    }
  ],
  "title": "天气预警",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "预警",
  "candidateAssetIds": [
    "asset.bell_fill",
    "asset.clock",
    "asset.typhoon_fill"
  ]
}
```
