import yaml
import time

class whiteIP(object):
    def __init__(self,wechatObj):
        self.data_ip = self.get_white_ip()
        self.wechatObj = wechatObj
    
    def get_white_ip(self):
        with open('config/wechatIP.yml', 'r') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        return data
    
    def is_white_ip(self,ip):
        self.update_white_ip()
        return ip in self.data_ip['whitelist']
    
    def update_white_ip(self):
        curtime = int(time.time())
        if curtime - int(self.data_ip['update_time']) >14400:
            self.data_ip['update_time'] = curtime
            self.data_ip['whitelist'] = self.get_wechatwhitelist()
            self.save_white_ip()
            
    def get_wechatwhitelist(self):
        try:
            ips = set(self.wechatObj.misc.get_wechat_ips())
        except Exception:
            print('获取IP失败')
            ips = self.data_ip['whitelist']
        return ips

    def save_white_ip(self):
        with open('config/wechatIP.yml', 'w') as f:
            yaml.dump(self.data_ip, f)