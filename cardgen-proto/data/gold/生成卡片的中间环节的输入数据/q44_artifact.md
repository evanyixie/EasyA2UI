```cardspec
{
  "title": "低电量导航",
  "description": "电量+充电+导航+省电",
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
{"version":"v0.9","updateComponents":{"surfaceId":"surface_card","root":"root","components":[{"id":"root","component":"Column","children":["__layout__root__content","cta_saving","cta_navigate"],"itemMargin":8,"styles":{"width":"matchParent","height":"matchParent","borderRadius":20,"clip":true,"alignItems":"start","justifyContent":"start","padding":12,"linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}}},{"id":"__layout__root__content","component":"Column","children":["battery_summary"],"styles":{"width":"matchParent","alignItems":"start","justifyContent":"start","layoutWeight":1,"flexShrink":0},"itemMargin":0},{"id":"battery_summary","component":"Column","children":["battery_summary_row0","battery_summary_row1"],"itemMargin":2,"styles":{"width":"matchParent","alignItems":"start","justifyContent":"center","flexShrink":1}},{"id":"battery_summary_row0","component":"Row","children":["battery_summary_row0_label","battery_summary_row0_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"battery_summary_row0_label","component":"Text","content":"剩余电量","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"battery_summary_row0_value","component":"Text","content":"{{ ${/data/phoneBattery/batterySOC} + '%' }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"battery_summary_row1","component":"Row","children":["battery_summary_row1_label","battery_summary_row1_value"],"itemMargin":8,"styles":{"width":"matchParent","height":18,"alignItems":"bottom","justifyContent":"spaceBetween","flexShrink":0}},{"id":"battery_summary_row1_label","component":"Text","content":"充电状态","styles":{"height":18,"fontSize":12,"fontWeight":500,"maxLines":1,"flexShrink":0,"fontColor":"#991F4799","textOverflow":"clip"}},{"id":"battery_summary_row1_value","component":"Text","content":"{{ ${/data/phoneBattery/chargingStatusDesc} }}","styles":{"height":18,"fontSize":12,"fontWeight":500,"textAlign":"end","maxLines":1,"flexShrink":1,"constraintSize":{"minWidth":0},"layoutWeight":1,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"cta_saving","component":"Row","children":["cta_saving_icon","cta_saving_text"],"onClick":[{"call":"clickToIntent","args":{"intentName":"SetSettingSwitch","params":{"appBundleName":"com.huawei.hmos.settings","itemName":"battery_saving_mode","switchFlag":0}}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"cta_saving_icon","component":"Image","src":"resources/base/media/battery_leaf_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"cta_saving_text","component":"Text","content":"开启省电模式","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}},{"id":"cta_navigate","component":"Row","children":["cta_navigate_icon","cta_navigate_text"],"onClick":[{"call":"clickToIntent","args":{"intentName":"StartNavigate","params":{"dstLocation":{"location":"home","latitude":"","longitude":""}}}}],"itemMargin":8,"styles":{"height":36,"borderRadius":30,"padding":0,"flexShrink":0,"width":"matchParent","backgroundColor":"#331F4799","justifyContent":"center","alignItems":"center"}},{"id":"cta_navigate_icon","component":"Image","src":"resources/base/media/house_fill.svg","styles":{"width":20,"height":20,"objectFit":"contain","flexShrink":0,"fillColor":"#FF1F4799"}},{"id":"cta_navigate_text","component":"Text","content":"导航回家","styles":{"maxWidth":96,"height":17,"fontSize":14,"fontWeight":500,"textAlign":"center","maxLines":1,"flexShrink":0,"fontColor":"#FF1F4799","textOverflow":"clip"}}]}}
{"version":"v0.9","updateDataModel":{"surfaceId":"surface_card","path":"/","value":{"data":{"phoneBattery":{"batterySOC":68,"chargingStatusDesc":"未充电"}}}}}
```
```schema
{
  "schemaVersion": "widget-artifact-v2"
}
```
```taskspec
{
  "userQuery": "帮我做个卡片，查看剩余电量，点击打开省电模式，并且可以直接导航回家。",
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
    },
    {
      "id": "event.startNavigate",
      "description": "点击导航按钮，跳转到地图应用进行导航。大模型需根据用户说的目的地选择location的值，只支持回家和去公司的导航",
      "call": "clickToIntent",
      "args": {
        "intentName": "StartNavigate",
        "params": {
          "dstLocation": {
            "location": "home",
            "latitude": "",
            "longitude": ""
          }
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
      "id": "asset.location_north_up_right_fill",
      "src": "resources/base/media/location_north_up_right_fill.svg",
      "description": "样式：方向导航实心图标，默认黑色，图形为指向右上方的导航箭头；适用：地图导航、方向指引、路线规划。"
    },
    {
      "id": "asset.house_fill",
      "src": "resources/base/media/house_fill.svg",
      "description": "样式：默认黑色的单色房屋实心图标，内部通过镂空表现门洞，支持通过 fillColor 与卡片配色统一；适用：首页导航、智能家居入口、回家提醒。"
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
    },
    {
      "id": "event.startNavigate",
      "description": "点击导航按钮，跳转到地图应用进行导航。大模型需根据用户说的目的地选择location的值，只支持回家和去公司的导航",
      "call": "clickToIntent",
      "args": {
        "intentName": "StartNavigate",
        "params": {
          "dstLocation": {
            "location": "home",
            "latitude": "",
            "longitude": ""
          }
        }
      }
    }
  ],
  "asset": [
    "asset.battery_leaf_fill",
    "asset.location_north_up_right_fill",
    "asset.house_fill"
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
    },
    {
      "capabilityId": "event.startNavigate",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "StartNavigate",
          "params": {
            "dstLocation": {
              "location": "home",
              "latitude": "",
              "longitude": ""
            }
          }
        }
      }
    }
  ],
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.location_north_up_right_fill",
    "asset.house_fill"
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
  "artifactId": "7606da75-68d8-4e3a-b994-1db109b955c3",
  "createdAt": 1792045574557
}
```
```designcompactdsl
["root","Layout",{"layout":"S-content-dual-action","linearGradient":{"direction":"RightBottom","colors":[["#FFCBDDFE",0],["#FFF1F6FE",1]]}},["battery_summary","cta_saving","cta_navigate"]]
["battery_summary","TableText",{"items":[{"label":"剩余电量","value":"{{ ${/data/phoneBattery/batterySOC} + '%' }}"},{"label":"充电状态","value":{"path":"/data/phoneBattery/chargingStatusDesc"}}],"fontSize":12}]
["cta_saving","PillButton",{"label":"开启省电模式","icon":"resources/base/media/battery_leaf_fill.svg","onClick":[{"call":"clickToIntent","args":{"intentName":"SetSettingSwitch","params":{"appBundleName":"com.huawei.hmos.settings","itemName":"battery_saving_mode","switchFlag":0}}}]}]
["cta_navigate","PillButton",{"label":"导航回家","icon":"resources/base/media/house_fill.svg","onClick":[{"call":"clickToIntent","args":{"intentName":"StartNavigate","params":{"dstLocation":{"location":"home","latitude":"","longitude":""}}}}]}]
["/data/phoneBattery/batterySOC",68]
["/data/phoneBattery/chargingStatusDesc","未充电"]
```
```request
{
  "content": {
    "bundleName": "com.omega_w_0823.hmservice",
    "userQuery": "帮我做个卡片，查看剩余电量，点击打开省电模式，并且可以直接导航回家。",
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
    "title": "低电量导航",
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
      },
      {
        "capabilityId": "event.startNavigate",
        "action": {
          "call": "clickToIntent",
          "args": {
            "intentName": "StartNavigate",
            "params": {
              "dstLocation": {
                "location": "home",
                "latitude": "",
                "longitude": ""
              }
            }
          }
        }
      }
    ],
    "description": "电量+充电+导航+省电",
    "candidateAssetIds": [
      "asset.battery_leaf_fill",
      "asset.location_north_up_right_fill",
      "asset.house_fill"
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
    "interactionId": "044",
    "isNew": true,
    "sessionId": "taskspec-829.2"
  },
  "userAuth": {
    "user": {}
  },
  "utterance": {
    "original": "帮我做个卡片，查看剩余电量，点击打开省电模式，并且可以直接导航回家。",
    "type": "text"
  },
  "version": "1.0",
  "bundleName": "com.omega_w_0823.hmservice",
  "userQuery": "帮我做个卡片，查看剩余电量，点击打开省电模式，并且可以直接导航回家。",
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
  "title": "低电量导航",
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
    },
    {
      "capabilityId": "event.startNavigate",
      "action": {
        "call": "clickToIntent",
        "args": {
          "intentName": "StartNavigate",
          "params": {
            "dstLocation": {
              "location": "home",
              "latitude": "",
              "longitude": ""
            }
          }
        }
      }
    }
  ],
  "description": "电量+充电+导航+省电",
  "candidateAssetIds": [
    "asset.battery_leaf_fill",
    "asset.location_north_up_right_fill",
    "asset.house_fill"
  ]
}
```
```repair-1
{
  "modelGeneratedCompactDsl": "[\"root\",\"Layout\",{\"layout\":\"S-content-dual-action\",\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}},[\"battery_summary\",\"cta_saving\",\"cta_navigate\"]]\n[\"battery_summary\",\"TableText\",{\"items\":[{\"label\":\"剩余电量\",\"value\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\"},{\"label\":\"充电状态\",\"value\":{\"path\":\"/data/phoneBattery/chargingStatusDesc\"}}],\"fontSize\":12}]\n[\"cta_saving\",\"PillButton\",{\"label\":\"开启省电模式\",\"icon\":\"resources/base/media/battery_leaf_fill.svg\",\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"SetSettingSwitch\",\"params\":{\"appBundleName\":\"com.huawei.hmos.settings\",\"itemName\":\"battery_saving_mode\",\"switchFlag\":0}}}]}]\n[\"cta_navigate\",\"PillButton\",{\"label\":\"导航回家\",\"icon\":\"resources/base/media/house_fill.svg\",\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"StartNavigate\",\"params\":{\"dstLocation\":{\"location\":\"home\",\"latitude\":\"\",\"longitude\":\"\"}}}}]}]\n[\"/data/phoneBattery/batterySOC\",68]\n[\"/data/phoneBattery/chargingStatusDesc\",\"未充电\"]",
  "generatedDsl": "{\"version\":\"v0.9\",\"createSurface\":{\"surfaceId\":\"surface_card\",\"catalogId\":\"ohos.a2ui.extended.catalog.form\"}}\n{\"version\":\"v0.9\",\"updateComponents\":{\"surfaceId\":\"surface_card\",\"root\":\"root\",\"components\":[{\"id\":\"root\",\"component\":\"Column\",\"children\":[\"__layout__root__content\",\"cta_saving\",\"cta_navigate\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":\"matchParent\",\"borderRadius\":20,\"clip\":true,\"alignItems\":\"start\",\"justifyContent\":\"start\",\"padding\":12,\"linearGradient\":{\"direction\":\"RightBottom\",\"colors\":[[\"#FFCBDDFE\",0],[\"#FFF1F6FE\",1]]}}},{\"id\":\"__layout__root__content\",\"component\":\"Column\",\"children\":[\"battery_summary\"],\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"start\",\"layoutWeight\":1,\"flexShrink\":0},\"itemMargin\":0},{\"id\":\"battery_summary\",\"component\":\"Column\",\"children\":[\"battery_summary_row0\",\"battery_summary_row1\"],\"itemMargin\":2,\"styles\":{\"width\":\"matchParent\",\"alignItems\":\"start\",\"justifyContent\":\"center\",\"flexShrink\":1}},{\"id\":\"battery_summary_row0\",\"component\":\"Row\",\"children\":[\"battery_summary_row0_label\",\"battery_summary_row0_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":18,\"alignItems\":\"bottom\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"battery_summary_row0_label\",\"component\":\"Text\",\"content\":\"剩余电量\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"battery_summary_row0_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/batterySOC} + '%' }}\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"battery_summary_row1\",\"component\":\"Row\",\"children\":[\"battery_summary_row1_label\",\"battery_summary_row1_value\"],\"itemMargin\":8,\"styles\":{\"width\":\"matchParent\",\"height\":18,\"alignItems\":\"bottom\",\"justifyContent\":\"spaceBetween\",\"flexShrink\":0}},{\"id\":\"battery_summary_row1_label\",\"component\":\"Text\",\"content\":\"充电状态\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#991F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"battery_summary_row1_value\",\"component\":\"Text\",\"content\":\"{{ ${/data/phoneBattery/chargingStatusDesc} }}\",\"styles\":{\"height\":18,\"fontSize\":12,\"fontWeight\":500,\"textAlign\":\"end\",\"maxLines\":1,\"flexShrink\":1,\"constraintSize\":{\"minWidth\":0},\"layoutWeight\":1,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"cta_saving\",\"component\":\"Row\",\"children\":[\"cta_saving_icon\",\"cta_saving_text\"],\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"SetSettingSwitch\",\"params\":{\"appBundleName\":\"com.huawei.hmos.settings\",\"itemName\":\"battery_saving_mode\",\"switchFlag\":0}}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#331F4799\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"cta_saving_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/battery_leaf_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"cta_saving_text\",\"component\":\"Text\",\"content\":\"开启省电模式\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}},{\"id\":\"cta_navigate\",\"component\":\"Row\",\"children\":[\"cta_navigate_icon\",\"cta_navigate_text\"],\"onClick\":[{\"call\":\"clickToIntent\",\"args\":{\"intentName\":\"StartNavigate\",\"params\":{\"dstLocation\":{\"location\":\"home\",\"latitude\":\"\",\"longitude\":\"\"}}}}],\"itemMargin\":8,\"styles\":{\"height\":36,\"borderRadius\":30,\"padding\":0,\"flexShrink\":0,\"width\":\"matchParent\",\"backgroundColor\":\"#331F4799\",\"justifyContent\":\"center\",\"alignItems\":\"center\"}},{\"id\":\"cta_navigate_icon\",\"component\":\"Image\",\"src\":\"resources/base/media/house_fill.svg\",\"styles\":{\"width\":20,\"height\":20,\"objectFit\":\"contain\",\"flexShrink\":0,\"fillColor\":\"#FF1F4799\"}},{\"id\":\"cta_navigate_text\",\"component\":\"Text\",\"content\":\"导航回家\",\"styles\":{\"maxWidth\":96,\"height\":17,\"fontSize\":14,\"fontWeight\":500,\"textAlign\":\"center\",\"maxLines\":1,\"flexShrink\":0,\"fontColor\":\"#FF1F4799\",\"textOverflow\":\"clip\"}}]}}\n{\"version\":\"v0.9\",\"updateDataModel\":{\"surfaceId\":\"surface_card\",\"path\":\"/\",\"value\":{\"data\":{\"phoneBattery\":{\"batterySOC\":68,\"chargingStatusDesc\":\"未充电\"}}}}}",
  "validationErrors": []
}
```
