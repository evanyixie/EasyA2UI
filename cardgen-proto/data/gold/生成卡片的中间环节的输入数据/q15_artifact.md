```cardspec
{
  "title": "心率复盘",
  "description": "高低心率和更新",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"跑步心率复盘","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#99563D99"}},{"id":"header_icon","component":"Image","src":"resources/base/media/heart_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF563D99"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__support"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["max_rate"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"max_rate","component":"Column","children":["max_rate_main","max_rate_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"max_rate_main","component":"Text","content":"最高心率","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"max_rate_secondary","component":"Text","content":"{{ ${/data/healthSport/exerciseHeartRateMax} + '次/分钟' }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#99563D99","textOverflow":"clip"}},{"id":"__layout__root__support","component":"Column","children":["min_rate"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"end","layoutWeight":1},"itemMargin":0},{"id":"min_rate","component":"Column","children":["min_rate_main","min_rate_secondary"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"min_rate_main","component":"Text","content":"最低心率","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF563D99","textOverflow":"clip"}},{"id":"min_rate_secondary","component":"Text","content":"{{ ${/data/healthSport/exerciseHeartRateMin} + '次/分钟' }}","styles":{"height":16,"fontSize":12,"fontWeight":400,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#99563D99","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"healthSport":{"exerciseHeartRateMax":168,"exerciseHeartRateMin":96}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "跑步结束后想复盘心率，帮我做个卡片，重点看最高心率和最低心率。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [],
  "dataModelSchema": {
    "data": {
      "healthSport": {
        "exerciseHeartRateMax": {
          "type": "integer",
          "description": "专业运动期间最大心率的纯整数，单位为次/分钟，返回值不包含单位。若直接用于文本展示，必须在数值后追加“次/分钟”。",
          "sampleValue": 168
        },
        "exerciseHeartRateMin": {
          "type": "integer",
          "description": "专业运动期间最低心率的纯整数，单位为次/分钟，返回值不包含单位。若直接用于文本展示，必须在数值后追加“次/分钟”。",
          "sampleValue": 96
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
      "id": "asset.heart_fill",
      "src": "resources/base/media/heart_fill.svg",
      "description": "样式：默认黑色的单色实心爱心图标；适用：喜欢、收藏、关爱、心脏健康或心率栏目入口。"
    },
    {
      "id": "asset.clock",
      "src": "resources/base/media/clock.svg",
      "description": "样式：时钟线框图标，默认黑色，图形为圆形表盘加指针的线性轮廓；适用：时间显示、定时功能、倒计时。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetHealthAndSportSummary"
  ],
  "event": [],
  "asset": [
    "asset.figure_run",
    "asset.heart_fill",
    "asset.clock"
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
        "/exerciseHeartRateMax",
        "/exerciseHeartRateMin"
      ]
    }
  ],
  "candidateEventCandidates": [],
  "candidateAssetIds": [
    "asset.figure_run",
    "asset.heart_fill",
    "asset.clock"
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
  "artifactId": "56ceb8e8-8bed-4c51-a922-bc50ad132d3a",
  "createdAt": 1792045412691
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-dual-content","linearGradient":{"direction":"RightBottom","colors":[["#FFDBCCFF",0],["#FFF6F2FF",1]]}},["header","max_rate","min_rate"]]
["header","SingleLineTitle",{"title":"跑步心率复盘","icon":"resources/base/media/heart_fill.svg","fontSize":12}]
["max_rate","EmphasisText",{"mainText":"最高心率","secondaryText":"{{ ${/data/healthSport/exerciseHeartRateMax} + '次/分钟' }}","fontSize":18}]
["min_rate","EmphasisText",{"mainText":"最低心率","secondaryText":"{{ ${/data/healthSport/exerciseHeartRateMin} + '次/分钟' }}","fontSize":18}]
["/data/healthSport/exerciseHeartRateMax",168]
["/data/healthSport/exerciseHeartRateMin",96]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "跑步结束后想复盘心率，帮我做个卡片，重点看最高心率和最低心率。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetHealthAndSportSummary",
        "arguments": {
          "targetDayOffset": 0
        },
        "writeResultTo": "/data/healthSport",
        "candidateOutputFields": [
          "/exerciseHeartRateMax",
          "/exerciseHeartRateMin"
        ]
      }
    ],
    "title": "心率复盘",
    "size": "2x2",
    "candidateEventCandidates": [],
    "description": "高低心率和更新",
    "candidateAssetIds": [
      "asset.figure_run",
      "asset.heart_fill",
      "asset.clock"
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
    "interactionId": "015",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "跑步结束后想复盘心率，帮我做个卡片，重点看最高心率和最低心率。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "跑步结束后想复盘心率，帮我做个卡片，重点看最高心率和最低心率。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetHealthAndSportSummary",
      "arguments": {
        "targetDayOffset": 0
      },
      "writeResultTo": "/data/healthSport",
      "candidateOutputFields": [
        "/exerciseHeartRateMax",
        "/exerciseHeartRateMin"
      ]
    }
  ],
  "title": "心率复盘",
  "size": "2x2",
  "candidateEventCandidates": [],
  "description": "高低心率和更新",
  "candidateAssetIds": [
    "asset.figure_run",
    "asset.heart_fill",
    "asset.clock"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFDBCCFF\",0],[\"#FFF6F2FF\",1]]}},[\"header\",\"rate_group\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"跑步心率复盘\",\"icon\":\"resources/base/media/heart_fill.svg\",\"fontSize\":12}]\n[\"rate_group\",\"Group\",{\"variant\":\"supporting-items\"},[\"max_rate\",\"min_rate\"]]\n[\"max_rate\",\"EmphasisText\",{\"mainText\":\"最高心率\",\"secondaryText\":\"{{ ${/data/healthSport/exerciseHeartRateMax} + '次/分钟' }}\",\"fontSize\":18}]\n[\"min_rate\",\"EmphasisText\",{\"mainText\":\"最低心率\",\"secondaryText\":\"{{ ${/data/healthSport/exerciseHeartRateMin} + '次/分钟' }}\",\"fontSize\":18}]\n[\"/data/healthSport/exerciseHeartRateMax\",168]\n[\"/data/healthSport/exerciseHeartRateMin\",96]",
  "generatedDsl": "",
  "validationErrors": [
    {
      "stage": "validation",
      "code": "COMPACT_DSL_VALIDATION_FAILED",
      "message": "语义布局不符合合同：节点 root：子组件数量应为 [3]；要求的 children 角色为 [title, primary, support]。请选择已登记的 Layout、Region 或 Group 变体，不要修改展开后的几何。"
    }
  ]
}
```
```repair-2
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-dual-content\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFDBCCFF\",0],[\"#FFF6F2FF\",1]]}},[\"header\",\"max_rate\",\"min_rate\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"跑步心率复盘\",\"icon\":\"resources/base/media/heart_fill.svg\",\"fontSize\":12}]\n[\"max_rate\",\"EmphasisText\",{\"mainText\":\"最高心率\",\"secondaryText\":\"{{ ${/data/healthSport/exerciseHeartRateMax} + '次/分钟' }}\",\"fontSize\":18}]\n[\"min_rate\",\"EmphasisText\",{\"mainText\":\"最低心率\",\"secondaryText\":\"{{ ${/data/healthSport/exerciseHeartRateMin} + '次/分钟' }}\",\"fontSize\":18}]\n[\"/data/healthSport/exerciseHeartRateMax\",168]\n[\"/data/healthSport/exerciseHeartRateMin\",96]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFDBCCFF\",0],[\"#FFF6F2FF\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"跑步心率复盘\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#99563D99\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/heart_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF563D99\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__primary\",\"__layout__root__support\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__primary\",\"component\":\"Column\",\"children\":[\"max_rate\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"max_rate\",\"component\":\"Column\",\"children\":[\"max_rate_main\",\"max_rate_secondary\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"max_rate_main\",\"component\":\"Text\",\"content\":\"最高心率\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF563D99\",\"textOverflow\":\"clip\"}},{\"id\":\"max_rate_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/healthSport/exerciseHeartRateMax} + '次/分钟' }}\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#99563D99\",\"textOverflow\":\"clip\"}},{\"id\":\"__layout__root__support\",\"component\":\"Column\",\"children\":[\"min_rate\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"end\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"min_rate\",\"component\":\"Column\",\"children\":[\"min_rate_main\",\"min_rate_secondary\"],\"itemMargin\":2,\"styles\":{\"alignItems\":\"start\",\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"width\":\"matchParent\"}},{\"id\":\"min_rate_main\",\"component\":\"Text\",\"content\":\"最低心率\",\"styles\":{\"height\":24,\"fontSize\":18,\"fontWeight\":700,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#FF563D99\",\"textOverflow\":\"clip\"}},{\"id\":\"min_rate_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/healthSport/exerciseHeartRateMin} + '次/分钟' }}\",\"styles\":{\"height\":16,\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1.3333333333333333,\"maxLines\":1,\"flexShrink\":1,\"width\":\"matchParent\",\"fontColor\":\"#99563D99\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"healthSport\":{\"exerciseHeartRateMax\":168,\"exerciseHeartRateMin\":96}}}}}",
  "validationErrors": []
}
```
