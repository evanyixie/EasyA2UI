```cardspec
{
  "title": "低电量省电",
  "description": "电量+一键省电",
  "suggestSize": "2x2",
  "imageDomainWhitelist": [
    "hag-ability-test.obs.cn-north-1.myhuaweicloud.com",
    "lfcontentcenterdev.hwcloudtest.cn",
    "hagres-drcn.dbankcdn.com"
  ],
  "dataBindings": [
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["header","__layout__root__body"],"itemMargin":6,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"header","component":"Row","children":["header_title","header_icon"],"itemMargin":0,"styles":{"width":"matchParent","height":20,"flexShrink":0,"justifyContent":"spaceBetween","alignItems":"center"}},{"id":"header_title","component":"Text","content":"手机电量","styles":{"fontSize":12,"fontWeight":400,"lineHeight":1,"textAlign":"start","maxLines":1,"flexShrink":1,"width":"wrapContent","layoutWeight":1,"constraintSize":{"minWidth":0},"fontColor":"#991F4799"}},{"id":"header_icon","component":"Image","src":"resources/base/media/battery_leaf_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"__layout__root__body","component":"Column","children":["__layout__root__content","__layout__root__action"],"itemMargin":8,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1}},{"id":"__layout__root__content","component":"Column","children":["battery"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1},"itemMargin":0},{"id":"battery","component":"Row","children":["battery_ring_stack","battery_labels"],"itemMargin":8,"styles":{"width":"matchParent","height":52,"alignItems":"center","justifyContent":"center","flexShrink":0}},{"id":"battery_ring_stack","component":"Stack","children":["battery_ring","battery_icon"],"styles":{"width":52,"height":52,"alignContent":"center","flexShrink":0}},{"id":"battery_ring","component":"Progress","value":"{{ ${/data/phoneBattery/batterySOC} }}","total":100,"styles":{"width":52,"height":52,"strokeWidth":6,"flexShrink":0,"type":"ring","color":"#FF1F4799","backgroundColor":"#331F4799"}},{"id":"battery_icon","component":"Image","src":"resources/base/media/battery_leaf_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#991F4799"}},{"id":"battery_labels","component":"Column","children":["battery_label","battery_display","battery_secondary"],"itemMargin":0,"styles":{"height":52,"alignItems":"start","justifyContent":"center","flexShrink":1,"layoutWeight":1}},{"id":"battery_label","component":"Text","content":"剩余电量","styles":{"width":"matchParent","height":18,"fontSize":14,"fontWeight":700,"maxLines":1,"textOverflow":"clip","fontColor":"#FF1F4799"}},{"id":"battery_display","component":"Text","content":"{{ ${/data/phoneBattery/batterySOC} + '%' }}","styles":{"width":"matchParent","height":16,"fontSize":10,"fontWeight":400,"maxLines":1,"textOverflow":"clip","fontColor":"#991F4799"}},{"id":"battery_secondary","component":"Text","content":"{{ ${/data/phoneBattery/chargingStatusDesc} }}","styles":{"width":"matchParent","height":16,"fontSize":10,"fontWeight":400,"maxLines":1,"textOverflow":"clip","fontColor":"#991F4799"}},{"id":"__layout__root__action","component":"Column","children":["action"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","height":36,"flexShrink":0},"itemMargin":0},{"id":"action","component":"Row","children":["action_icon","action_text"],"onClick":[{"call":"clickToIntent","args":{"intentName":"SetSettingSwitch","params":{"appBundleName":"com.huawei.hmos.settings","itemName":"battery_saving_mode","switchFlag":0}}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"action_icon","component":"Image","src":"resources/base/media/bolt_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"action_text","component":"Text","content":"开启省电模式","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"batterySOC":68,"chargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个电量卡片，使用进度环查看剩余电量和充电状态，点击进入省电模式。",
  "size": "2x2",
  "appVersion": "11.9.9.342",
  "eventCandidates": [
    {
      "id": "event.setPowerSavingMode",
      "description": "点击一键开启/关闭省电模式。大模型根据用户表达确定是开启还是关闭，然后传对应的switchFlag值",
      "call": "clickToIntent",
      "args": {
        "intentName": "SetSettingSwitch",
        "params": {
          "appBundleName": "com.huawei.hmos.settings",
          "itemName": "battery_saving_mode",
          "switchFlag": 0
        }
      }
    }
  ],
  "dataModelSchema": {
    "data": {
      "phoneBattery": {
        "batterySOC": {
          "type": "integer",
          "description": "当前手机设备剩余电量的纯整数百分比，取值范围为 0 到 100，返回值不包含“%”。若直接用于文本展示，必须在数值后追加“%”；优先使用 batterySOCText。",
          "sampleValue": 68
        },
        "chargingStatusDesc": {
          "type": "string",
          "description": "当前设备电池的充电状态文本描述。",
          "sampleValue": "未充电"
        }
      }
    }
  },
  "assetCandidates": [
    {
      "id": "asset.battery_leaf_fill",
      "src": "resources/base/media/battery_leaf_fill.svg",
      "description": "样式：默认黑色的单色实心横向电池图标，电池内部为叶片留白；适用：电池相关场景，包括电量、省电模式、节能电池、绿色用电状态，也可作为电池健康或电池温度信息的辅助图标，相关数据可结合 GetPhoneBatteryInfo 展示。图标本身不表示具体电量、健康等级或温度高低。"
    },
    {
      "id": "asset.bolt_fill",
      "src": "resources/base/media/bolt_fill.svg",
      "description": "样式：默认黑色的单色实心竖向闪电图标；适用：正在充电、快充、电能或闪电状态。"
    }
  ]
}
```
```effectivecapabilities
{
  "data": [
    "GetPhoneBatteryInfo"
  ],
  "event": [
    {
      "id": "event.setPowerSavingMode",
      "description": "点击一键开启/关闭省电模式。大模型根据用户表达确定是开启还是关闭，然后传对应的switchFlag值",
      "call": "clickToIntent",
      "args": {
        "intentName": "SetSettingSwitch",
        "params": {
          "appBundleName": "com.huawei.hmos.settings",
          "itemName": "battery_saving_mode",
          "switchFlag": 0
        }
      }
    }
  ],
  "asset": [
    "asset.battery_leaf_fill",
    "asset.bolt_fill"
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
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC",
        "/chargingStatusDesc"
      ]
    }
  ],
  "candidateEventCandidates": [
    {
      "capabilityId": "event.setPowerSavingMode",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "SetSettingSwitch",
          "params": {
            "appBundleName": "com.huawei.hmos.settings",
            "itemName": "battery_saving_mode",
            "switchFlag": 0
          }
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.bolt_fill"
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
  "artifactId": "8a25b554-a9b1-4127-979f-2de780fa62f6",
  "createdAt": 1792045500150
}
```
```designcompactdsl
["root","Layout",{"layout":"S-title-content-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["header","battery","action"]]
["header","SingleLineTitle",{"title":"手机电量","icon":"resources/base/media/battery_leaf_fill.svg","fontSize":12}]
["battery","ProgressCircleSingle",{"value":{"path":"/data/phoneBattery/batterySOC"},"total":100,"icon":"resources/base/media/battery_leaf_fill.svg","displayValue":"{{ ${/data/phoneBattery/batterySOC} + '%' }}","label":"剩余电量","secondaryLabel":{"path":"/data/phoneBattery/chargingStatusDesc"},"color":"#FF1F4799","backgroundColor":"#331F4799"}]
["action","PillButton",{"label":"开启省电模式","icon":"resources/base/media/bolt_fill.svg","onClick":[{"call":"clickToIntent","args":{"intentName":"SetSettingSwitch","params":{"appBundleName":"com.huawei.hmos.settings","itemName":"battery_saving_mode","switchFlag":0}}}]}]
["/data/phoneBattery/batterySOC",68]
["/data/phoneBattery/chargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个电量卡片，使用进度环查看剩余电量和充电状态，点击进入省电模式。",
    "candidateDataBindings": [
      {
        "capabilityId": "GetPhoneBatteryInfo",
        "arguments": {},
        "writeResultTo": "/data/phoneBattery",
        "candidateOutputFields": [
          "/batterySOC",
          "/chargingStatusDesc"
        ]
      }
    ],
    "title": "低电量省电",
    "size": "2x2",
    "candidateEventCandidates": [
      {
        "capabilityId": "event.setPowerSavingMode",
        "action": {
          "call": "clickToIntent",
          "args": {
            "intentName": "SetSettingSwitch",
            "params": {
              "appBundleName": "com.huawei.hmos.settings",
              "itemName": "battery_saving_mode",
              "switchFlag": 0
            }
          }
        }
      }
    ],
    "description": "电量+一键省电",
    "candidateAssetIds": [
      "asset.battery_leaf_fill",
      "asset.bolt_fill"
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
    "interactionId": "032",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个电量卡片，查看剩余电量和充电状态，点击进入省电模式。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个电量卡片，查看剩余电量和充电状态，点击进入省电模式。",
  "candidateDataBindings": [
    {
      "capabilityId": "GetPhoneBatteryInfo",
      "arguments": {},
      "writeResultTo": "/data/phoneBattery",
      "candidateOutputFields": [
        "/batterySOC",
        "/chargingStatusDesc"
      ]
    }
  ],
  "title": "低电量省电",
  "size": "2x2",
  "candidateEventCandidates": [
    {
      "capabilityId": "event.setPowerSavingMode",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "SetSettingSwitch",
          "params": {
            "appBundleName": "com.huawei.hmos.settings",
            "itemName": "battery_saving_mode",
            "switchFlag": 0
          }
        }
      }
    }
  ],
  "description": "电量+一键省电",
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.bolt_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-title-content-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"header\",\"battery\",\"action\"]]\n[\"header\",\"SingleLineTitle\",{\"title\":\"手机电量\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"fontSize\":12}]\n[\"battery\",\"ProgressCircleSingle\",{\"value\":{\"path\":\"/data/phoneBattery/batterySOC\"},\"total\":100,\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"displayValue\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\",\"label\":\"剩余电量\",\"secondaryLabel\":{\"path\":\"/data/phoneBattery/chargingStatusDesc\"},\"color\":\"#FF1F4799\",\"backgroundColor\":\"#331F4799\"}]\n[\"action\",\"PillButton\",{\"label\":\"开启省电模式\",\"icon\":\"resources/base/media/bolt_fill.svg\",\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"SetSettingSwitch\",\"params\":{\"appBundleName\":\"com.huawei.hmos.settings\",\"itemName\":\"battery_saving_mode\",\"switchFlag\":0}}}]}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/phoneBattery/chargingStatusDesc\",\"未充电\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"header\",\"__layout__root__body\"],\"itemMargin\":6,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"header\",\"component\":\"Row\",\"children\":[\"header_title\",\"header_icon\"],\"itemMargin\":0,\"styles\":{\"width\":\"matchParent\",\"height\":20,\"flexShrink\":0,\"justifyContent\":\"spaceBetween\",\"alignItems\":\"center\"}},{\"id\":\"header_title\",\"component\":\"Text\",\"content\":\"手机电量\",\"styles\":{\"fontSize\":12,\"fontWeight\":400,\"lineHeight\":1,\"textAlign\":\"start\",\"maxLines\":1,\"flexShrink\":1,\"width\":\"wrapContent\",\"layoutWeight\":1,\"constraintSize\":{\"minWidth\":0},\"fontColor\":\"#991F4799\"}},{\"id\":\"header_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/battery_leaf_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"__layout__root__body\",\"component\":\"Column\",\"children\":[\"__layout__root__content\",\"__layout__root__action\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"battery\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1},\"itemMargin\":0},{\"id\":\"battery\",\"component\":\"Row\",\"children\":[\"battery_ring_stack\",\"battery_labels\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":52,\"alignItems\":\"center\",\"justifyContent\":\"center\",\"flexShrink\":0}},{\"id\":\"battery_ring_stack\",\"component\":\"Stack\",\"children\":[\"battery_ring\",\"battery_icon\"],\"styles\":{\"width\":52,\"height\":52,\"alignContent\":\"center\",\"flexShrink\":0}},{\"id\":\"battery_ring\",\"component\":\"Progress\",\"value\":\"{{ ${/data/phoneBattery/batterySOC} }}\",\"total\":100,\"styles\":{\"width\":52,\"height\":52,\"strokeWidth\":6,\"flexShrink\":0,\"type\":\"ring\",\"color\":\"#FF1F4799\",\"backgroundColor\":\"#331F4799\"}},{\"id\":\"battery_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/battery_leaf_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#991F4799\"}},{\"id\":\"battery_labels\",\"component\":\"Column\",\"children\":[\"battery_label\",\"battery_display\",\"battery_secondary\"],\"itemMargin\":0,\"styles\":{\"height\":52,\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1,\"layoutWeight\":1}},{\"id\":\"battery_label\",\"component\":\"Text\",\"content\":\"剩余电量\",\"styles\":{\"width\":\"matchParent\",\"height\":18,\"fontSize\":14,\"fontWeight\":700,\"maxLines\":1,\"textOverflow\":\"clip\",\"fontColor\":\"#FF1F4799\"}},{\"id\":\"battery_display\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\",\"styles\":{\"width\":\"matchParent\",\"height\":16,\"fontSize\":10,\"fontWeight\":400,\"maxLines\":1,\"textOverflow\":\"clip\",\"fontColor\":\"#991F4799\"}},{\"id\":\"battery_secondary\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/chargingStatusDesc} }}\",\"styles\":{\"width\":\"matchParent\",\"height\":16,\"fontSize\":10,\"fontWeight\":400,\"maxLines\":1,\"textOverflow\":\"clip\",\"fontColor\":\"#991F4799\"}},{\"id\":\"__layout__root__action\",\"component\":\"Column\",\"children\":[\"action\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"height\":36,\"flexShrink\":0},\"itemMargin\":0},{\"id\":\"action\",\"component\":\"Row\",\"children\":[\"action_icon\",\"action_text\"],\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"SetSettingSwitch\",\"params\":{\"appBundleName\":\"com.huawei.hmos.settings\",\"itemName\":\"battery_saving_mode\",\"switchFlag\":0}}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#331F4799\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"action_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/bolt_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"action_text\",\"component\":\"Text\",\"content\":\"开启省电模式\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"batterySOC\":68,\"chargingStatusDesc\":\"未充电\"}}}}}",
  "validationErrors": []
}
```
