```cardspec
{
  "title": "耳机听歌入口",
  "description": "耳机连接+收藏歌单",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone"
    }
  ]
}
```
```genui
{"version":"v0.9","createSurface":{"surfaceId":"surface_card","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["title_area","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"title_area","component":"Row","children":["title_area_title","title_area_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"title_area_title","component":"Text","content":"耳机","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"title_area_icon","component":"Image","src":"resources/base/media/icon_earphone.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__primary","__layout__root__bottom"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__primary","component":"Column","children":["connection"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"connection","component":"Column","children":["connection_main"],"itemMargin":2,"styles":{"alignItems":"start","flexShrink":1,"constraintSize":{"minWidth":0},"width":"matchParent"}},{"id":"connection_main","component":"Text","content":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}","styles":{"height":24,"fontSize":18,"fontWeight":700,"lineHeight":1.3333333333333333,"maxLines":1,"flexShrink":1,"width":"matchParent","fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"__layout__root__bottom","component":"Row","children":["name","__layout__root__action_slot"],"itemMargin":8,"styles":{"width":"matchParent","height":40,"flexShrink":0,"alignItems":"bottom","justifyContent":"spaceBetween"}},{"id":"name","component":"Column","children":["name_row0"],"itemMargin":2,"styles":{"width":78,"alignItems":"start","flexShrink":1}},{"id":"name_item0_value","component":"Text","content":"{{ ${/data/earphone/earphoneName} }}","styles":{"height":19.0,"fontSize":14,"fontWeight":400,"maxLines":1,"flexShrink":1,"lineHeight":1.3571428571428572,"fontColor":"#991F4799","layoutWeight":1,"textOverflow":"clip"}},{"id":"name_item0","component":"Row","children":["name_item0_value"],"itemMargin":0,"styles":{"height":19.0,"alignItems":"top","flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1}},{"id":"name_row0","component":"Row","children":["name_item0"],"itemMargin":0,"styles":{"width":"matchParent","height":19.0,"alignItems":"top","flexShrink":0}},{"id":"__layout__root__action_slot","component":"Stack","children":["favorite_action"],"styles":{"width":40,"height":40,"alignContent":"center"}},{"id":"favorite_action","component":"Stack","children":["favorite_action_icon"],"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"}}],"styles":{"width":40,"height":40,"borderRadius":20,"padding":0,"flexShrink":0,"backgroundColor":"#331F4799","alignContent":"center","clip":true}},{"id":"favorite_action_icon","component":"Image","src":"resources/base/media/music_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"earphone":{"isConnected":true,"earphoneName":"示例耳机"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个耳机卡片，看看耳机连上没、叫什么名字，能直接打开收藏的歌单。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.open.music.favorite",
      "description": "打开音乐app的收藏歌单/心动歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "earphone": {
        "isConnected": {
          "type": "boolean",
          "description": "当前是否有蓝牙耳机处于连接活跃状态。",
          "sampleValue": true
        },
        "earphoneName": {
          "type": "string",
          "description": "耳机的设备广播名称，如果未连接则返回'未连接耳机'。如: 'FreeBuds Pro 3'。",
          "sampleValue": "示例耳机"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.icon_earphone",
      "src": "resources/base/media/icon_earphone.svg",
      "description": "样式：默认黑色的单色左右分体式开放耳机，局部通过镂空表现高光与分隔，支持通过 fillColor 与卡片配色统一；适用：无线耳机本体、耳机连接、左右耳设备状态。"
    },
    {
      "id": "asset.music_fill",
      "src": "resources/base/media/music_fill.svg",
      "description": "样式：音乐音符实心图标，默认黑色，图形为双音符连接造型；适用：音乐播放卡片、音频功能入口、歌单展示。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetEarphoneInfo"
  ],
  "event": [
    {
      "id": "event.open.music.favorite",
      "description": "打开音乐app的收藏歌单/心动歌单，uri为固定值勿更改",
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Music",
        "bundleName": "",
        "abilityName": "",
        "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
      }
    }
  ],
  "asset": [
    "asset.icon_earphone",
    "asset.music_fill"
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
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/isConnected",
        "/earphoneName"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.music.favorite",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Music",
          "bundleName": "",
          "abilityName": "",
          "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.icon_earphone",
    "asset.music_fill"
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
  "artifactId": "91e12041-cb83-4c05-b669-c346b352c229",
  "createdAt": 1792045495301
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-anchor","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["title_area","connection","name","favorite_action"]]
["title_area","SingleLineTitle",{"title":"耳机","icon":"resources/base/media/icon_earphone.svg","fontSize":12}]
["connection","EmphasisText",{"mainText":"{{ ${/data/earphone/isConnected} ? '已连接' : '未连接' }}","fontSize":18}]
["name","SecondaryBody",{"items":[{"value":{"path":"/data/earphone/earphoneName"}}],"fontSize":14}]
["favorite_action","CircleButton",{"icon":"resources/base/media/music_fill.svg","accessibility":{"label":"打开收藏歌单"},"onClick":[{"call":"clickToDeeplink","args":{"intentName":"Music","bundleName":"","abilityName":"","uri":"hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"}}]}]
["/data/earphone/isConnected",true]
["/data/earphone/earphoneName","示例耳机"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个耳机卡片，看看耳机连上没、叫什么名字，能直接打开收藏的歌单。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetEarphoneInfo",
        "arguments": {},
        "writeResultTo": "/data/earphone",
        "candidateOutputFields": [
          "/isConnected",
          "/earphoneName"
        ]
      }
    ],
    "title": "耳机听歌入口",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.open.music.favorite",
        "action": {
          "call": "clickToDeeplink",
          "args": {
            "intentName": "Music",
            "bundleName": "",
            "abilityName": "",
            "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
          }
        }
      }
    ],
    "description": "耳机连接+收藏歌单",
    "candidateAssetIds": [
      "asset.icon_earphone",
      "asset.music_fill"
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
    "interactionId": "031",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个耳机卡片，看看耳机连上没、叫什么名字，能直接打开收藏的歌单。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个耳机卡片，看看耳机连上没、叫什么名字，能直接打开收藏的歌单。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetEarphoneInfo",
      "arguments": {},
      "writeResultTo": "/data/earphone",
      "candidateOutputFields": [
        "/isConnected",
        "/earphoneName"
      ]
    }
  ],
  "title": "耳机听歌入口",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.open.music.favorite",
      "action": {
        "call": "clickToDeeplink",
        "args": {
          "intentName": "Music",
          "bundleName": "",
          "abilityName": "",
          "uri": "hwmusic://com.huawei.hmsapp.music/showMusicList?code=favoriteSong&type=412"
        }
      }
    }
  ],
  "description": "耳机连接+收藏歌单",
  "candidateAssetIds": [
    "asset.icon_earphone",
    "asset.music_fill"
  ]
}
```
