<!--
 * @Author        : fineemb
 * @Github        : https://github.com/fineemb
 * @Description   : 
 * @Date          : 2020-08-26 16:20:12
 * @LastEditors   : fineemb
 * @LastEditTime  : 2020-10-12 09:53:21
-->

# Lynk&Co

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)


![01](https://dm30webimages.lynkco.com.cn/LynkCoPortal/Files/Cars/01/36001/710/JIN/r/3.png)

The Lynk&Co integration offers integration with the Lynk&Co cloud service and provides presence detection as well as sensors such as  state and temperature.

Support 60+ sensors

Support remote control

This integration provides the following platforms:
  + Binary sensors - Seat belt status, Door open status, Tyre pre warning
  + Sensors - Key status,Engine status,Speed...
  + Device tracker - to track location of your car
  + Lock - Central lock

Currently only suitable for 01 Linux models

## Update

+ ### v1.0
  + init
  + Added remote control commands
  
## Install

Please use HACS to install

## Service

### `lynkco.start`

Start the vehicle

| Service data attribute | Optional | Description|
|---------|------|----|
|`entity_id`   | Required | Vehicle Device tracker entity|

### `lynkco.stop`

Stop the vehicle

| Service data attribute | Optional | Description|
|---------|------|----|
|`entity_id`   | Required | Vehicle Device tracker entity|

### `lynkco.lock`

Lock the vehicle

| Service data attribute | Optional | Description|
|---------|------|----|
|`entity_id`   | Required | Vehicle Device tracker entity|


### `lynkco.unlock`

Unlock the vehicle

| Service data attribute | Optional | Description|
|---------|------|----|
|`entity_id`   | Required | Vehicle Device tracker entity|
|`value`   | Required | Time to stay unlocked (1-3)minute|

### `lynkco.hlf`

Flashing lights and whistle

| Service data attribute | Optional | Description|
|---------|------|----|
|`entity_id`   | Required | Vehicle Device tracker entity|
|`value`   | Required | Flashing lights and whistle options( horn-light-flash,light-flash,horn-flash )|

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/guidelines/download-assets-sm-2.svg)](https://www.buymeacoffee.com/fineemb)
