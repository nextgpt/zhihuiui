import logging
import sys
import urllib.parse
import json
import requests
import os

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL
from open_webui.config import PersistentConfig, OAUTH_PROVIDERS

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("OAUTH", logging.INFO))

class WecomOAuthProvider:
    """企业微信 OAuth 登录提供商"""
    
    @staticmethod
    def register():
        """注册企业微信 OAuth 提供商"""
        try:
            # 从环境变量获取配置
            wecom_corpid = os.environ.get("WECOM_CORPID")
            wecom_agentid = os.environ.get("WECOM_AGENTID")
            wecom_corpsecret = os.environ.get("WECOM_CORPSECRET")
            wecom_redirect_uri = os.environ.get("WECOM_REDIRECT_URI")
            
            log.info(f"正在注册企业微信 OAuth 提供商...")
            log.info(f"企业微信配置: CORPID={wecom_corpid}, AGENTID={wecom_agentid}, REDIRECT_URI={wecom_redirect_uri}")
            
            if not wecom_corpid:
                log.warning("缺少企业微信 CORPID 配置，无法注册企业微信 OAuth")
                return
                
            if not wecom_agentid:
                log.warning("缺少企业微信 AGENTID 配置，无法注册企业微信 OAuth")
                return
                
            if not wecom_corpsecret:
                log.warning("缺少企业微信 CORPSECRET 配置，无法注册企业微信 OAuth")
                return
                
            if not wecom_redirect_uri:
                log.warning("缺少企业微信 REDIRECT_URI 配置，无法注册企业微信 OAuth")
                return
            
            log.info(f"开始注册企业微信 OAuth 提供商: {wecom_corpid}")
            
            # 构建固定的授权URL，直接嵌入参数
            full_authorize_url = f"https://open.work.weixin.qq.com/wwopen/sso/qrConnect?appid={wecom_corpid}&agentid={wecom_agentid}&redirect_uri={urllib.parse.quote(wecom_redirect_uri)}"
            log.info(f"授权URL: {full_authorize_url}")
            
            # 临时简化OAuth注册配置
            def simple_wecom_oauth_register(client):
                log.info("开始注册企业微信OAuth客户端...")
                try:
                    client.register(
                        name="wecom",
                        client_id=wecom_corpid,
                        client_secret=wecom_corpsecret,
                        authorize_url="https://open.work.weixin.qq.com/wwopen/sso/qrConnect",
                        access_token_url="https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                        api_base_url="https://qyapi.weixin.qq.com/",
                        client_kwargs={
                            "scope": "snsapi_base",
                            "response_type": "code",
                            "appid": wecom_corpid,
                            "agentid": wecom_agentid,
                        },
                    )
                    log.info("企业微信OAuth客户端注册成功")
                except Exception as e:
                    log.error(f"企业微信OAuth客户端注册失败: {e}")
                    raise e
                    
            # 直接设置固定授权URL，不通过OAuth库构建
            OAUTH_PROVIDERS["wecom"] = {
                "name": "企业微信",
                "redirect_uri": wecom_redirect_uri,
                "register": simple_wecom_oauth_register,
                "custom_handler": WecomOAuthProvider.handle_callback,
                "custom_authorize_url": full_authorize_url
            }
            
            log.info("✅ 企业微信 OAuth 提供商注册成功")
        except Exception as e:
            log.error(f"❌ 企业微信 OAuth 提供商注册失败: {e}")
            log.exception(e)
    
    @staticmethod
    async def handle_callback(client, token, request):
        """处理企业微信回调"""
        try:
            log.info("正在处理企业微信回调")
            log.info(f"请求参数: {request.url}")
            log.info(f"token: {token}")
            
            # 从环境变量获取配置
            wecom_corpid = os.environ.get("WECOM_CORPID")
            wecom_corpsecret = os.environ.get("WECOM_CORPSECRET")
            
            if not wecom_corpid or not wecom_corpsecret:
                log.error("企业微信配置不完整")
                return None
            
            # 从请求中获取code
            code = request.query_params.get("code")
            if not code:
                log.error("企业微信回调缺少 code 参数")
                return None
                
            # 获取 access_token
            log.info("获取企业微信 access_token")
            access_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wecom_corpid}&corpsecret={wecom_corpsecret}"
            access_token_response = requests.get(access_token_url)
            access_token_data = access_token_response.json()
            
            log.info(f"access_token响应: {access_token_data}")
            
            if access_token_data.get("errcode") != 0:
                log.error(f"获取企业微信 access_token 失败: {access_token_data}")
                return None
            
            access_token = access_token_data.get("access_token")
            
            log.info(f"获取用户信息，code: {code}")
            user_info_url = f"https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token={access_token}&code={code}"
            user_info_response = requests.get(user_info_url)
            user_info_data = user_info_response.json()
            
            log.info(f"用户信息响应: {user_info_data}")
            
            if user_info_data.get("errcode") != 0:
                log.error(f"获取企业微信用户信息失败: {user_info_data}")
                return None
            
            userid = user_info_data.get("UserId")
            if not userid:
                log.error("企业微信回调获取用户 ID 失败")
                return None
            
            # 获取用户详情
            log.info(f"获取用户 {userid} 的详细信息")
            user_detail_url = f"https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={access_token}&userid={userid}"
            user_detail_response = requests.get(user_detail_url)
            user_detail_data = user_detail_response.json()
            
            log.info(f"用户详情响应: {user_detail_data}")
            
            if user_detail_data.get("errcode") != 0:
                log.error(f"获取企业微信用户详情失败: {user_detail_data}")
                return None
            
            # 构造标准的 OAuth 用户信息
            log.info(f"用户认证成功: {user_detail_data.get('name', userid)}")
            
            # 注意：企业微信返回的用户信息格式与标准 OIDC 不同，需要进行转换
            return {
                "sub": f"wecom:{userid}",  # 唯一标识
                "name": user_detail_data.get("name", userid),
                "email": user_detail_data.get("email", f"{userid}@work.weixin"),
                "picture": user_detail_data.get("avatar", ""),
                "preferred_username": user_detail_data.get("name", userid),
            }
        except Exception as e:
            log.error(f"处理企业微信回调失败: {e}")
            log.exception(e)
            return None

# 注册企业微信 OAuth 提供商
WecomOAuthProvider.register() 