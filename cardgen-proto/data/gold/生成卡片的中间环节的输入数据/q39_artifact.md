```cardspec
{
  "title": "今日锻炼",
  "description": "最近运动类型+时长+锻炼入口",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"最近运动","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/stopwatch_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["content"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"content","component":"Column","children":["type","duration"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start"}},{"id":"type","component":"Column","children":["type_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"type_main","component":"Text","content":"{{ ${/data/healthSport/exerciseTypeName} }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"duration","component":"Column","children":["duration_row0"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","flexShrink":1}},{"id":"duration_item0_label","component":"Text","content":"时长","styles":{"height":19,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":0,"lineHeight":1.3571428571428572,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"duration_item0_value","component":"Text","content":"{{ ${/data/healthSport/exerciseDurationText} }}","styles":{"height":19.0,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3571428571428572,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"duration_item0","component":"Row","children":["duration_item0_label","duration_item0_value"],"itemMargin":0,"styles":{"height":19.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"duration_row0","component":"Row","children":["duration_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":19.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action","component":"Column","children":["action"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Health","bundleName":"","abilityName":"","uri":"huaweischeme://healthapp/home/sport?sportType=2"}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/figure_run.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"action_text","component":"Text","content":"打开锻炼页","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"exerciseTypeName":"户外跑步","exerciseDurationText":"40分"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个运动卡片，看看最近一次练了什么、练了多久，点一下打开运动健康的锻炼页。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.health.sport",
      "description": "打开运动健康应用的锻炼Tab页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Health",
        "bundleName": "",
        "abilityName": "",
        "uri": "huaweischeme://healthapp/home/sport?sportType=2"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "healthSport": {
        "exerciseTypeName": {
          "type": "string",
          "description": "最近一次发生的单次专业运动训练类型的中文映射名称，如“羽毛球”、“自由训练”、“户外跑步”。若无记录则返回“暂无运动”。",
          "sampleValue": "户外跑步"
        },
        "exerciseDurationText": {
          "type": "string",
          "description": "可直接显示的单次专业运动实际持续时长文本，已包含“小时”或“分”等时间单位；展示时不得再次追加时间单位。例如“1小时40分”。",
          "sampleValue": "40分"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.figure_run",
      "src": "resources/base/media/figure_run.svg",
      "description": "样式：跑步人物图标，默认黑色，图形为人体奔跑动作侧视轮廓；适用：运动记录、跑步锻炼追踪、步数统计。"
    },
    {
      "id": "asset.stopwatch_fill",
      "src": "resources/base/media/stopwatch_fill.svg",
      "description": "样式：默认黑色的单色秒表实心图标，内部通过镂空表现表盘指针，支持通过 fillColor 与卡片配色统一；适用：计时功能、运动计时、倒计时。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetHealthAndSportSummary"
  ],
  "event": [
    {
      "id": "event.open.health.sport",
      "description": "打开运动健康应用的锻炼Tab页",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Health",
        "bundleName": "",
        "abilityName": "",
        "uri": "huaweischeme://healthapp/home/sport?sportType=2"
      }
    }
  ],
  "asset": [
    "asset.figure_run",
    "asset.stopwatch_fill"
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
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/exerciseTypeName",
        "/exerciseDurationText"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.health.sport",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Health",
          "bundleName": "",
          "abilityName": "",
          "uri": "huaweischeme://healthapp/home/sport?sportType=2"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.figure_run",
    "asset.stopwatch_fill"
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
  "artifactId": "116ebc78-0b88-4cf9-9b12-d676239c38c6",
  "createdAt": 1792045532859
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","content","action"]]
["header","SingleLineTitle",{"title":"最近运动","icon":"resources/base/media/stopwatch_fill.svg","fontSize":12}]
["content","Group",{"variant":"hero-support"},["type","duration"]]
["type","EmphasisText",{"mainText":{"path":"/data/healthSport/exerciseTypeName"},"fontSize":18}]
["duration","SecondaryBody",{"items":[{"label":"时长","value":{"path":"/data/healthSport/exerciseDurationText"}}],"fontSize":14}]
["action","PillButton",{"label":"打开锻炼页","icon":"resources/base/media/figure_run.svg","onClick":[{"call":"clickToDeeplink","args":{"intentName":"Health","bundleName":"","abilityName":"","uri":"huaweischeme://healthapp/home/sport?sportType=2"}}]}]
["/data/healthSport/exerciseTypeName","户外跑步"]
["/data/healthSport/exerciseDurationText","40分"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个运动卡片，看看最近一次练了什么、练了多久，点一下打开运动健康的锻炼页。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": 0
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/exerciseTypeName",
          "/exerciseDurationText"
        ]
      }
    ],
    "title": "今日锻炼",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.health.sport",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Health",
            "bundleName": "",
            "abilityName": "",
            "uri": "huaweischeme://healthapp/home/sport?sportType=2"
          }
        }
      }
    ],
    "description": "最近运动类型+时长+锻炼入口",
    "candidateAssetIds": [
      "asset.figure_run",
      "asset.stopwatch_fill"
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
    "interactionId": "039",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个运动卡片，看看最近一次练了什么、练了多久，点一下打开运动健康的锻炼页。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个运动卡片，看看最近一次练了什么、练了多久，点一下打开运动健康的锻炼页。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/exerciseTypeName",
        "/exerciseDurationText"
      ]
    }
  ],
  "title": "今日锻炼",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.health.sport",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Health",
          "bundleName": "",
          "abilityName": "",
          "uri": "huaweischeme://healthapp/home/sport?sportType=2"
        }
      }
    }
  ],
  "description": "最近运动类型+时长+锻炼入口",
  "candidateAssetIds": [
    "asset.figure_run",
    "asset.stopwatch_fill"
  ]
}
```
