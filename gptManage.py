import time
import requests
import json
import math
import random
import logging



class gptSessionManage(object):
    '''
    会话管理器，保存发送和接受的消息，构造消息模板，实现上下文理解。
    '''
    def __init__(self):
        '''
        初始化
        '''
        self.messages = [{"role": "system", "content": "你是一个乐于助人的助手."}]
        self.sizeLim = 21
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
        self.messages = [{"role": "system", "content": "你是一个乐于助人的助手."}]
        
class gptMessageManage(object):
    '''
    消息管理器，接受用户消息，回复用户消息
    '''
    def __init__(self,tokens,max_tokens,model,temperature,rsize):
        # 基础设置
        self.tokens = tokens
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens#每条消息最大字符
        self.rsize = rsize# 设置每条消息的回复长度，超过长度将被分割

        self.msgs_list = dict()# msgID作为key，三次重复发送的msg放置在一个列表，结合append和pop构造队列，以实现轮流处理重复请求
        self.msgs_time_dict = dict()# 记录每个msgID最新的请求时间
        self.msgs_status_dict = dict()# 记录每个msgID的状态：pending,haveResponse
        self.msgs_returns_dict = dict()# 记录每个msgID的返回值
        self.msgs_msgdata_dict = dict()# 记录每个发送者的会话管理器gptSessionManage
        self.msgs_msg_cut_dict = dict()# 记录每个msgID超过回复长度限制的分割列表
        
    def get_response(self,msgs,curtime):
        '''
        获取每条msg，回复消息
        '''
        # 判断是否返回分割列表里面的内容
        if msgs.content=='继续' and len(self.msgs_msg_cut_dict.get(str(msgs.source),[]))>0:
            if len(self.msgs_msg_cut_dict[str(msgs.source)])>1:
                return self.msgs_msg_cut_dict[str(msgs.source)].pop(0)+'\n 还有剩余结果，请回复【继续】查看！'
            else:
                return self.msgs_msg_cut_dict[str(msgs.source)].pop(0)
        # 获取消息属性
        msg_status = self.msgs_status_dict.get(str(msgs.id),'')
        users_obj = self.msgs_msgdata_dict.get(str(msgs.source),'')
        # 判断是否新用户
        if users_obj=='':
            self.msgs_msgdata_dict[str(msgs.source)] = gptSessionManage()
        # 判断消息状态
        if msg_status=='':
            self.msgs_list[str(msgs.id)]=[]
            self.msgs_list[str(msgs.id)].append(msgs)
            self.msgs_time_dict[str(msgs.id)] = curtime
            self.msgs_status_dict[str(msgs.id)] = 'pending'
            self.msgs_msgdata_dict[str(msgs.source)].add_send_message(msgs.content)
            res = self.rec_get_returns_first(msgs)
        elif msg_status=='pending':
            self.msgs_time_dict[str(msgs.id)] = curtime
            res = self.rec_get_returns_pending(msgs)
        else:
            self.msgs_time_dict[str(msgs.id)] = curtime
            print(1)

        # print('记录时间：',self.msgs_time_dict.get(str(msgs.id),''),'当前时间',curtime)
        # 判断当前请求是否是最新的请求，是：返回消息，否：返回空
        if curtime == self.msgs_time_dict.get(str(msgs.id),''):
            # print('这是结果',self.msgs_returns_dict[str(msgs.id)])
            retunsMsg = self.msgs_returns_dict.get(str(msgs.id),'')
            self.msgs_status_dict[str(msgs.id)] = 'end'
            # print('self.msgs_returns_dict',self.msgs_returns_dict)
            # print('self.msgs_status_dict',self.msgs_status_dict)
            # print('self.msgs_time_dict',self.msgs_time_dict)
            # 清理缓存
            self.del_cache()
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
            # print('当前的对话没有回复',curtime,msgs.content)
            self.del_cache()
            return ''
    
    def rec_get_returns_pending(self,msgs):
        '''
        pending状态的消息等候
        '''
        while self.msgs_status_dict.get(str(msgs.id),'') == 'pending':
            time.sleep(1)
        return 'success'
            
    
    def rec_get_returns_first(self,msgs):
        '''
        首次消息开始处理
        '''
        while len(self.msgs_list[str(msgs.id)])>0:
            mymsg = self.msgs_list[str(msgs.id)].pop(0)
            self.msgs_returns_dict[str(mymsg.id)]=self.send_request(mymsg)
        return 'success'
            
    def get_header(self):
        '''
        随机获取token，可以设置多个token，避免单个token超过请求限制。
        '''
        return random.choice(self.tokens)
    def send_request(self,msgs):
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.get_header(),
            }
            print('发送的消息：',self.msgs_msgdata_dict[str(msgs.source)].messages)

            json_data = {
                'model': 'gpt-3.5-turbo',
                'messages': self.msgs_msgdata_dict[str(msgs.source)].messages,
                'max_tokens':self.max_tokens,
                'temperature':self.temperature,
            }

            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data,timeout=14)
            response_parse = json.loads(response.text)
            print(response_parse)
            if 'error' in response_parse:
                print(response_parse)
                self.msgs_status_dict[str(msgs.id)] = 'haveResponse'
                return '出错了，请稍后再试！'
            else:
                self.msgs_msgdata_dict[str(msgs.source)].add_res_message(response_parse['choices'][0]['message']['content'])
                self.msgs_status_dict[str(msgs.id)] = 'haveResponse'
                return response_parse['choices'][0]['message']['content']
        except Exception as e:
            print(e)
            self.msgs_status_dict[str(msgs.id)] = 'haveResponse'
            return '请求超时，请稍后再试！'
        
    def del_cache(self):
        '''
        清除缓存
        '''
        currenttt = int(time.time())
        delkey_lis = []
        for key, value in self.msgs_time_dict.items():
            if currenttt-value>60:
                delkey_lis.append(key)
        for key in delkey_lis:
            self.msgs_time_dict.pop(key,'')
            self.msgs_status_dict.pop(key,'')
            self.msgs_returns_dict.pop(key,'')
            self.msgs_list.pop(key,'')
        return 

            
        
        
        