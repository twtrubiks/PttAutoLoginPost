# PttAutoLoginPost

PTT自動登入發文(Python) for Windows and Linux

* [Demo Video](https://youtu.be/FkdR6C-a9Nw) - Linux

update -2017/5/1

此範例使用  Python 3.4.3

如要使用 python 2.7.3 可參考 [20a029ab14f55e81b](https://github.com/twtrubiks/PttAutoLoginPost/tree/20a029ab14f55e81b790c90698c8cd0d0b03ad3d)

## 特色

* 自動登入PTT發文，再登出PTT

## 使用方法

請將下列程式碼修改為自己的PTT ID 以及 Password

```python
user = 'Your PTT ID'
password = 'Your PTT Password'
```

## 執行範例

```cmd
python PttAuto.py
```

預設為在 PTT Test板 發文

標題 : 發文文字測試

內文 : 這是一篇測試,哇哈哈

``` python
post('test', u'發文文字測試', u'這是一篇測試,哇哈哈')
```

## 執行過程

![alt tag](http://i.imgur.com/kGx379D.jpg)

## 執行環境

Ubuntu 12.04

Python 3.4.3

## Donation

文章都是我自己研究內化後原創，如果有幫助到您，也想鼓勵我的話，歡迎請我喝一杯咖啡:laughing:

![alt tag](https://i.imgur.com/LRct9xa.png)

[贊助者付款](https://payment.opay.tw/Broadcaster/Donate/9E47FDEF85ABE383A0F5FC6A218606F8)

## License

MIT license
