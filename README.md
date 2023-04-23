**简介：**

未认证微信公众号接入chatgpt，新增语音聊天(英语对话)，基于Flask，实现个人微信公众号【无认证】接入ChatGPT

**--更新说明：**

  V1.1.0：(2023.04.13)
  
  -新增流式响应(stream),一定程度缓解请求超时的问题,需要安装python包：sseclient-py==1.7.2;
      
   *开启流式响应之后，会先建立连接(myrequest)，然后再利用(SSEClient)一个一个字符的获取生成的文本，最后将所获取的文本列表拼接成回复文本。建立连接的时间还是会受到max_tokens的影响，所以不建议max_tokens设置太大。能缓解请求超时的关键在于，建立连接的时间消耗小于一次性返回的时间消耗，所以只要在给定的时间内，成功建立连接，基本就能返回内容，返回内容的长度会受到连接时间的影响。*
      
  -请求失败或超时之后删除用户最近发送的消息，避免下次回复出错。
 

  V1.0.1：
  
  -新增ip检测(防止doss攻击)是否开启选项;
  
  -注意：如果wechat-ip_detection和azure-trans_to_voice中任意一项为true，appid和secret都需要填写。
  
  V1.0：
  
  -新增语音聊天功能，接入微软云文本转语音服务(免费接入)，实现语音对话(中英文)；
  
  -内置英语学习模板, 回复模板消息即可进行英语主题对话；
  
  -新增微信后台白名单IP检测，防止doss攻击等；
  
  -新增用户消息频率限制，防止恶意刷消息；
  
  -自动清理临时语音文件；
  
  -自动清理微信后台上传临时语音素材；
  
  -优化性能、修复BUG。

**背景：**

最近看到ChatGPT提供了API接口，手上刚好有台服务器和一个公众号，所以想着写一个聊天机器人🤖玩一玩。不过只有一个没有认证的个人公众号(资源有限😭)，这个公众号的限制就是：

1.只能被动回复用户消息，用户发送一条消息到公众号，服务器只能针对这个请求回复一条消息，不能再额外回复消息(客服消息)；

2.每次必须在15s以内回复消息，公众号平台在发送请求到服务器后，如果5s内没收到回复，会再次发送请求等候5秒，如果还是没有收到请求，最后还会发送一次请求，所以服务器必须在15s以内完整消息的处理。

具体处理方式查看代码。新手项目，有不足之处还请包含并欢迎指正，谢谢~

**需求：**

一台服务器（需要能访问openai接口的，可能需要海外的~）

如果需要开启文本转语音服务，需要注册Azure的文本转语音，该服务注册和使用免费，具体参考网址：[AZURE](https://azure.microsoft.com/en-us/products/cognitive-services/text-to-speech/)

微信公众号：个人类型即可

**演示：**

公众号：Tory的实验室，关注发送消息即可体验。

公众号推文介绍:

  1.入门使用介绍：[ChatGPT已接入](https://mp.weixin.qq.com/s/KOIkDTAEnIW_0uwM3iS-0g)

  2.语音服务使用介绍：[语音服务已接入](https://mp.weixin.qq.com/s/cEaqzOFzXGNFm7yd4zWwBw)


![image-20230305121520474](https://github.com/ToryPan/ChatGPT_WeChat/blob/main/pic/image-20230305121520474.png)

**使用方法：**

设置config里面的config.yml参数：

```yml
# 微信相关设置
wechat:
  token: "****"
  # 是否获取微信公众平台的ip白名单(用于防止doss检测)
  ip_detection: false
  # 如果上面的选项为true，下面两项内容必填；如要开启后面文本转语音服务，下面两项内容必填
  appid: "****"
  secret: "****"

# openai相关设置
openai:
  #填写openai的api_keys时，要注意前面要加上：Bearer, 可以填写多个,因为单个账号有速率的限制
  api_keys:
   - "Bearer sk-****"
   # - "Bearer sk-****"
   # - "Bearer sk-****"
  # 单条消息的长度，这个参数对回复速度有非常大的影响，请不要填太大~
  max_tokens: 120
  # 模型
  model: "gpt-3.5-turbo-0301"
  # temperature，越大随机性越强
  temperature: 0.8
  # 有时候文本长度超过150，用该参数限制长度避免超过微信能发送的最长消息
  rsize: 500
  # 对话的保存历史
  save_history: 21
  
# azure文本转语音设置
azure:
  # 是否开启文本转语音服务
  trans_to_voice: false
  # 如上面的选项为false，下面的内容不用填写
  # 新定义文本长度，开启后增加处理时间，避免文本太长，处理时间过久，超过15s
  max_token: 80
  # 是否开启流式响应
  stream_response: true
  # 密钥
  subscription: "****"
  region: "koreacentral"
  # 中文语音模型
  zh_model: "zh-CN-XiaoyanNeural"
  # 英文语音模型
  en_model: "en-US-AriaNeural"
```

启动flask

```sh
export FLASK_APP=myflask

flask run --host=0.0.0.0 --port=80
# 或者
nohup flask run --host=0.0.0.0 --port=80 >> /home/jupyter/flask/log/wechat.log 2>&1 &
```

**注意：**

1.填写openai的api_keys时，注意前面要加上：Bearer。可以填写多个api_keys,因为单个账号有速率的限制;

2.max_tokens对回复速度有非常大的影响，请不要填太大。

