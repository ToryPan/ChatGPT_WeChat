**简介：**

未认证微信公众号接入chatgpt，基于Flask，实现个人微信公众号【无认证】接入ChatGPT【GPT-3.5-Turbo】

**--更新说明：**
  
  V1.0：
  
  -新增语音聊天功能，接入微软云文本转语音服务(免费接入)，实现语音对话(中英文)；
  
  -内置英语学习模板, 回复模板消息即可进行英语主题对话；
  
  -新增微信后台白名单IP检测，防止doss等；
  
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

如果需要开启文本转语音服务，需要注册Azure的文本转语音，该服务注册和使用免费，具体参考网址：<https://azure.microsoft.com/en-us/products/cognitive-services/text-to-speech/>

微信公众号：个人类型即可

**演示：**

公众号：Tory的实验室，关注发送消息即可体验。

![image-20230305121520474](https://github.com/ToryPan/ChatGPT_WeChat/blob/main/pic/image-20230305121520474.png)

**使用方法：**

设置config里面的config.yml参数：

```yml
# 微信相关设置
wechat:
  appid: "****"
  secret: "****"
  token: "****"

# openai相关设置
openai:
  api_keys:
   - "Bearer sk-****"
   - "Bearer sk-****"
   - "Bearer sk-****"
  # 单条消息的长度
  max_tokens: 150
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
  # 新定义文本长度，开启后增加处理时间，避免文本太长，处理时间过久，超过15s
  max_token: 80
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


