import time
import requests
import json
import math
import random
import logging
import azure.cognitiveservices.speech as speechsdk
from wechatpy import WeChatClient
import threading
import os 
from os import listdir

class gptSessionManage(object):
    '''
    会话管理器，保存发送和接受的消息，构造消息模板，实现上下文理解。
    '''
    def __init__(self,save_history):
        '''
        初始化
        '''
        self.messages = [{"role": "system", "content": "我是乐于助人的小助手，可以叫我Tory的小助手."}]
        self.sizeLim = save_history
        self.last_q_time = time.time()
    
    def add_send_message(self,msg):
        '''
        会话管理, 拼接回复模板
        '''
        # 清理超过10分钟的会话
        if time.time()-self.last_q_time>600:
            self.end_message()
        # 判断会话长度是否超过限制
        if len(self.messages)>self.sizeLim:
            self.messages.pop(1)
            self.messages.pop(1)
        self.messages.append({"role": "user", "content": f"{msg}"})
        # 记录时间节点
        self.last_q_time = time.time()

    def add_res_message(self,msg):
        '''
        添加openai回复消息内容
        '''
        self.messages.append({"role": "assistant", "content": f"{msg}"})
    
    def end_message(self):
        '''
        初始化会话
        '''
        self.messages = [{"role": "system", "content": "我是乐于助人的小助手，可以叫我Tory的小助手."}]
        
class gptMessageManage(object):
    '''
    消息管理器，接受用户消息，回复用户消息
    '''
    def __init__(self,wechat_client,configs):
        self.client = wechat_client
        self.configs = configs
        # 基础设置
        self.tokens = configs['openai']['api_keys']
        self.model = configs['openai']['model']
        self.temperature = configs['openai']['temperature']
        self.max_tokens = configs['openai']['max_tokens']#每条消息最大字符
        self.rsize = configs['openai']['rsize']# 设置每条消息的回复长度，超过长度将被分割
        # 记录信息的列表和字典
        self.msgs_list = dict()# msgID作为key，三次重复发送的msg放置在一个列表，结合append和pop构造队列，以实现轮流处理重复请求
        self.msgs_time_dict = dict()# 记录每个msgID最新的请求时间
        self.msgs_status_dict = dict()# 记录每个msgID的状态：pending,haveResponse
        self.msgs_returns_dict = dict()# 记录每个msgID的返回值
        self.msgs_msgdata_dict = dict()# 记录每个发送者的会话管理器gptSessionManage
        self.msgs_msg_cut_dict = dict()# 记录每个msgID超过回复长度限制的分割列表
        
        self.user_msg_timeSpan_dict = dict() # 记录每个发送消息者的时间消息时间间隔
        self.user_msg_timePoint_dict = dict() # 记录每个发送消息者的上次时间点
        
        self.media_id_list = [] #用于记录上传到微信素材的media_id
        
        self.last_clean_time = time.time()
        
        
    def get_response(self,msgs,curtime,msg_content):
        '''
        获取每条msg，回复消息
        '''
        self.msgs_time_dict[str(msgs.id)] = curtime
        # 判断是否返回分割列表里面的内容
        if msg_content=='继续' and len(self.msgs_msg_cut_dict.get(str(msgs.source),[]))>0:
            if len(self.msgs_msg_cut_dict[str(msgs.source)])>1:
                return self.msgs_msg_cut_dict[str(msgs.source)].pop(0)+'\n 还有剩余结果，请回复【继续】查看！'
            else:
                return self.msgs_msg_cut_dict[str(msgs.source)].pop(0)
        
        # 获取消息属性
        users_obj = self.msgs_msgdata_dict.get(str(msgs.source),'')
        # 判断是否新用户
        if users_obj=='':
            self.msgs_msgdata_dict[str(msgs.source)] = gptSessionManage(self.configs['openai']['save_history'])
        # 判断消息状态
        msg_status = self.msgs_status_dict.get(str(msgs.id),'')
        # 为新消息
        if msg_status=='':
            # 按照消息的ID创建消息列表
            self.msgs_list[str(msgs.id)]=[]
            self.msgs_list[str(msgs.id)].append(msgs)
            # 将当前时间设定为消息的最新时间
            
            # 修改消息的状态为pending
            self.msgs_status_dict[str(msgs.id)] = 'pending'
            # 加入消息到消息管理器中
            self.msgs_msgdata_dict[str(msgs.source)].add_send_message(msg_content)
            
            # 获取用户消息的时间间隔，防止用户发送消息过于频繁：
            user_sendTimeSpan = self.user_msg_timeSpan_dict.get(str(msgs.source),[])
            user_sendTimePoint = self.user_msg_timePoint_dict.get(str(msgs.source),curtime-15)
            if len(user_sendTimeSpan)<3:
                self.user_msg_timePoint_dict[str(msgs.source)] = curtime
                user_sendTimeSpan.append(curtime-user_sendTimePoint)
                self.user_msg_timeSpan_dict[str(msgs.source)] = user_sendTimeSpan
            else:
                user_curTimeUse = curtime-user_sendTimePoint
                user_avger_time = (user_sendTimeSpan[-2]+user_sendTimeSpan[-1]+user_curTimeUse)/3
                if user_avger_time<5:
                    return '发送消息频率过快，请等候10s以上重试！(PS:服务器资源有限，针对消息发送频率进行了限制，还请谅解~)'
                else:
                    self.user_msg_timePoint_dict[str(msgs.source)] = curtime
                    self.user_msg_timeSpan_dict[str(msgs.source)] = [user_sendTimeSpan[-2],user_sendTimeSpan[-1],user_curTimeUse]
            
            # 等候消息返回
            res = self.rec_get_returns_first(msgs)
        # 为二次请求消息
        else:
            res = self.rec_get_returns_pending(msgs)


        print('记录时间：',self.msgs_time_dict.get(str(msgs.id),''),'当前时间',curtime)
        # 判断当前请求是否是最新的请求，是：返回消息，否：返回空
        if curtime == self.msgs_time_dict.get(str(msgs.id),''):
            print('这是结果',self.msgs_returns_dict[str(msgs.id)])
            retunsMsg = self.msgs_returns_dict.get(str(msgs.id),'tt')
            # 清理缓存
            t = threading.Thread(target=self.del_cache)
            t.start()
            # 是否返回的语音消息的media_id
            if isinstance(retunsMsg, list):
                print('返回语音的列表：',retunsMsg)
                return retunsMsg
            # 判断长度是否过长，否则将消息分割
            if len(retunsMsg)>self.rsize:
                ssss = math.ceil(len(retunsMsg)/self.rsize)
                cutmsgs = []
                for i in range(ssss):
                    if i==ssss-1:
                        cutmsgs.append(retunsMsg[i*self.rsize:])
                    else:
                        cutmsgs.append(retunsMsg[i*self.rsize:i*self.rsize+self.rsize])
                self.msgs_msg_cut_dict[str(msgs.source)] = cutmsgs    
                return self.msgs_msg_cut_dict[str(msgs.source)].pop(0)+'\n 还有剩余结果，请回复【继续】查看！'
            return retunsMsg
        else:
            print('当前的对话没有回复',curtime,msg_content)
            # self.del_cache()
            time.sleep(10)
            return ''
    
    def rec_get_returns_pending(self,msgs):
        '''
        pending状态的消息等候
        '''
        while self.msgs_status_dict.get(str(msgs.id),'') == 'pending':
            time.sleep(0.1)
        return 'success'
            
    
    def rec_get_returns_first(self,msgs):
        '''
        首次消息开始处理
        '''
        while len(self.msgs_list[str(msgs.id)])>0:
            mymsg = self.msgs_list[str(msgs.id)].pop(0)
            if msgs.type == 'text' or self.configs['azure']['trans_to_voice']==False:
                self.msgs_returns_dict[str(mymsg.id)]=self.send_request(mymsg)
            else:
                self.msgs_returns_dict[str(mymsg.id)]=self.send_request_voice(mymsg)
        self.msgs_status_dict[str(mymsg.id)] = 'haveResponse'
        return 'success'
            
    def get_header(self):
        '''
        随机获取token，可以设置多个token，避免单个token超过请求限制。
        '''
        return random.choice(self.tokens)
    def send_request(self,msgs):
        '''text消息处理'''
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.get_header(),
            }
            print('发送的消息：',self.msgs_msgdata_dict[str(msgs.source)].messages)

            json_data = {
                'model': self.model,
                'messages': self.msgs_msgdata_dict[str(msgs.source)].messages,
                'max_tokens':self.max_tokens,
                'temperature':self.temperature,
            }

            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,timeout=13.2)
            response_parse = json.loads(response.text)
            print(response_parse)
            if 'error' in response_parse:
                print(response_parse)
                return '出错了，请稍后再试！'
            else:
                self.msgs_msgdata_dict[str(msgs.source)].add_res_message(response_parse['choices'][0]['message']['content'])
                return response_parse['choices'][0]['message']['content']
        except Exception as e:
            print(e)
            # return '请求超时，请稍后再试！\n【近期官方接口响应变慢，若持续出现请求超时，还请换个时间再来😅~】'
            return '请求超时，请稍后再试！'
        
    def send_request_voice(self,msgs):
        '''voice消息处理'''
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.get_header(),
            }
            print('发送的消息：',self.msgs_msgdata_dict[str(msgs.source)].messages)

            json_data = {
                'model': self.model,
                'messages': self.msgs_msgdata_dict[str(msgs.source)].messages,
                'max_tokens':self.configs['azure']['max_token'],
                'temperature':self.temperature,
            }

            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,timeout=9)
            response_parse = json.loads(response.text)
            print(response_parse)
            if 'error' in response_parse:
                print(response_parse)
                return '出错了，请稍后再试！'
            else:
                rtext = response_parse['choices'][0]['message']['content']
                if self.get_voice_from_azure(rtext,str(msgs.source),str(msgs.id)):
                    media_id = self.upload_wechat_voice(str(msgs.source),str(msgs.id))
                    # print('media_id:',str(media_id))
                    if media_id:
                        self.msgs_msgdata_dict[str(msgs.source)].add_res_message(rtext)
                        return [str(media_id)]
                    else:
                        return rtext
                else:
                    self.msgs_msgdata_dict[str(msgs.source)].add_res_message(rtext)
                    return rtext
        except Exception as e:
            print(e)
            return '请求超时，请稍后再试！'
    
    def get_voice_from_azure(self,texts,msgsource,msgid):
        '''
        从AZURE获取文本转语音的结果
        '''
        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.configs['azure']['subscription'], region=self.configs['azure']['region'])
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
            if self.have_chinese(texts):
                # speech_config.speech_synthesis_voice_name ="zh-CN-YunxiNeural"
                speech_config.speech_synthesis_voice_name =self.configs['azure']['zh_model']
            else:
                # speech_config.speech_synthesis_voice_name ="en-US-GuyNeural"
                speech_config.speech_synthesis_voice_name =self.configs['azure']['en_model']
            audio_config = speechsdk.audio.AudioOutputConfig(filename=f"voice/{msgsource[-5:]+msgid[-5:]}.mp3")
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            rr = speech_synthesizer.speak_text(f"{texts}")
            if rr.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return False
    
    def upload_wechat_voice(self,msgsource,msgid):
        '''上传语音素材到微信'''
        try:
            with open(f"voice/{msgsource[-5:]+msgid[-5:]}.mp3","rb") as f:
                res = self.client.material.add('voice',f)
                media_id = res['media_id']
                self.media_id_list.append(media_id)
            return media_id
        except Exception as e:
            print(e)
            return 
    
    def have_chinese(self,strs):
        '''判断是否有中文'''
        for _char in strs[:8]:
            if '\u4e00' <= _char <= '\u9fa5':
                return True
        return False
    
    def del_uploaded_wechat_voice(self,mediaId):
        '''删除上传的语音素材'''
        try:
            self.client.material.delete(mediaId)
            return 1
        except Exception as e:
            print(e)
            return 1
        
        
    def del_cache(self):
        '''
        清除缓存
        '''
        time.sleep(5)
        if time.time() - self.last_clean_time>300:
            currenttt = int(time.time())
            delkey_lis = []
            for key, value in self.msgs_time_dict.items():
                if currenttt-value>30:
                    delkey_lis.append(key)
            for key in delkey_lis:
                self.msgs_time_dict.pop(key,'')
                self.msgs_status_dict.pop(key,'')
                self.msgs_returns_dict.pop(key,'')
                self.msgs_list.pop(key,'')
            self.last_clean_time = time.time()
            my_path = 'voice/'
            
            for file_name in listdir(my_path):
                try:
                    os.remove(my_path + file_name)
                except Exception:
                    print('删除失败')
            # 删除media_id：
            for mid in self.media_id_list:
                self.del_uploaded_wechat_voice(mid)
            self.media_id_list = []
        return 
        
        