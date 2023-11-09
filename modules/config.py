from collections import defaultdict
from contextlib import contextmanager
import os
import logging
import sys
import json

from . import shared
from . import presets


__all__ = [
    "my_api_key",
    "authflag",
    "auth_list",
    "dockerflag",
    "retrieve_proxy",
    "log_level",
    "advance_docs",
    "update_doc_config",
    "usage_limit",
    "multi_api_key",
    "server_name",
    "server_port",
    "share",
    "check_update",
    "latex_delimiters_set",
    "hide_history_when_not_logged_in",
    "default_chuanhu_assistant_model"
]

if os.path.exists("config.json"):
    with open("config.json", "r") as f:
        config = json.load(f)
else:
    config = {}

lang_config = config.get("language", "auto")
language = os.environ.get("LANGUAGE", lang_config)

hide_history_when_not_logged_in = config.get("hide_history_when_not_logged_in", False)
check_update = config.get("check_update", True)

if os.path.exists("api_key.txt"):
    logging.info("检测到api_key.txt文件，正在进行迁移...")
    with open("api_key.txt", "r") as f:
        config["openai_api_key"] = f.read().strip()
    os.rename("api_key.txt", "api_key(deprecated).txt")
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

if os.path.exists("auth.json"):
    logging.info("检测到auth.json文件，正在进行迁移...")
    auth_list = []
    with open("auth.json", "r") as f:
            auth = json.load(f)
            for _ in auth:
                if auth[_]["username"] and auth[_]["password"]:
                    auth_list.append((auth[_]["username"], auth[_]["password"]))
                else:
                    logging.error("请检查auth.json文件中的用户名和密码！")
                    sys.exit(1)
    config["users"] = auth_list
    os.rename("auth.json", "auth(deprecated).json")
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

## 处理docker if we are running in Docker
dockerflag = config.get("dockerflag", False)
if os.environ.get("dockerrun") == "yes":
    dockerflag = True

## 处理 api-key 以及 允许的用户列表
my_api_key = config.get("openai_api_key", "")
my_api_key = os.environ.get("OPENAI_API_KEY", my_api_key)

usage_limit = os.environ.get("USAGE_LIMIT", config.get("usage_limit", 120))

## 多账户机制
multi_api_key = config.get("multi_api_key", False) # 是否开启多账户机制
if multi_api_key:
    api_key_list = config.get("api_key_list", [])
    if len(api_key_list) == 0:
        logging.error("多账号模式已开启，但api_key_list为空，请检查config.json")
        sys.exit(1)
    shared.state.set_api_key_queue(api_key_list)

auth_list = config.get("users", []) # 实际上是使用者的列表
authflag = len(auth_list) > 0  # 是否开启认证的状态值，改为判断auth_list长度

# 处理自定义的api_host，优先读环境变量的配置，如果存在则自动装配
api_host = os.environ.get("OPENAI_API_BASE", config.get("openai_api_base", None))
if api_host is not None:
    shared.state.set_api_host(api_host)

default_chuanhu_assistant_model = config.get("default_chuanhu_assistant_model", "gpt-3.5-turbo")
for x in ["GOOGLE_CSE_ID", "GOOGLE_API_KEY", "WOLFRAM_ALPHA_APPID", "SERPAPI_API_KEY"]:
    if config.get(x, None) is not None:
        os.environ[x] = config[x]

@contextmanager
def retrieve_openai_api(api_key = None):
    old_api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key is None:
        os.environ["OPENAI_API_KEY"] = my_api_key
        yield my_api_key
    else:
        os.environ["OPENAI_API_KEY"] = api_key
        yield api_key
    os.environ["OPENAI_API_KEY"] = old_api_key

## 处理log
log_level = config.get("log_level", "INFO")
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
)

## 处理代理：
http_proxy = os.environ.get("HTTP_PROXY", "")
https_proxy = os.environ.get("HTTPS_PROXY", "")
http_proxy = config.get("http_proxy", http_proxy)
https_proxy = config.get("https_proxy", https_proxy)

# 重置系统变量，在不需要设置的时候不设置环境变量，以免引起全局代理报错
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

local_embedding = config.get("local_embedding", False) # 是否使用本地embedding

@contextmanager
def retrieve_proxy(proxy=None):
    """
    1, 如果proxy = NONE，设置环境变量，并返回最新设置的代理
    2，如果proxy ！= NONE，更新当前的代理配置，但是不更新环境变量
    """
    global http_proxy, https_proxy
    if proxy is not None:
        http_proxy = proxy
        https_proxy = proxy
        yield http_proxy, https_proxy
    else:
        old_var = os.environ["HTTP_PROXY"], os.environ["HTTPS_PROXY"]
        os.environ["HTTP_PROXY"] = http_proxy
        os.environ["HTTPS_PROXY"] = https_proxy
        yield http_proxy, https_proxy # return new proxy

        # return old proxy
        os.environ["HTTP_PROXY"], os.environ["HTTPS_PROXY"] = old_var

## 处理latex options
user_latex_option = config.get("latex_option", "default")
if user_latex_option == "default":
    latex_delimiters_set = [
        {"left": "$$", "right": "$$", "display": True},
        {"left": "$", "right": "$", "display": False},
        {"left": "\\(", "right": "\\)", "display": False},
        {"left": "\\[", "right": "\\]", "display": True},
    ]
elif user_latex_option == "strict":
    latex_delimiters_set = [
        {"left": "$$", "right": "$$", "display": True},
        {"left": "\\(", "right": "\\)", "display": False},
        {"left": "\\[", "right": "\\]", "display": True},
    ]
elif user_latex_option == "all":
    latex_delimiters_set = [
        {"left": "$$", "right": "$$", "display": True},
        {"left": "$", "right": "$", "display": False},
        {"left": "\\(", "right": "\\)", "display": False},
        {"left": "\\[", "right": "\\]", "display": True},
        {"left": "\\begin{equation}", "right": "\\end{equation}", "display": True},
        {"left": "\\begin{align}", "right": "\\end{align}", "display": True},
        {"left": "\\begin{alignat}", "right": "\\end{alignat}", "display": True},
        {"left": "\\begin{gather}", "right": "\\end{gather}", "display": True},
        {"left": "\\begin{CD}", "right": "\\end{CD}", "display": True},
    ]
elif user_latex_option == "disabled":
    latex_delimiters_set = []
else:
    latex_delimiters_set = [
        {"left": "$$", "right": "$$", "display": True},
        {"left": "$", "right": "$", "display": False},
        {"left": "\\(", "right": "\\)", "display": False},
        {"left": "\\[", "right": "\\]", "display": True},
    ]

## 处理advance docs
advance_docs = defaultdict(lambda: defaultdict(dict))
advance_docs.update(config.get("advance_docs", {}))
def update_doc_config(two_column_pdf):
    global advance_docs
    advance_docs["pdf"]["two_column"] = two_column_pdf

    logging.info(f"更新后的文件参数为：{advance_docs}")

## 处理gradio.launch参数
server_name = config.get("server_name", None)
server_port = config.get("server_port", None)
if server_name is None:
    if dockerflag:
        server_name = "0.0.0.0"
    else:
        server_name = "127.0.0.1"
if server_port is None:
    if dockerflag:
        server_port = 7860

assert server_port is None or type(server_port) == int, "要求port设置为int类型"

# 设置默认model
default_model = config.get("default_model", "")
try:
    presets.DEFAULT_MODEL = presets.MODELS.index(default_model)
except ValueError:
    pass

share = config.get("share", False)
