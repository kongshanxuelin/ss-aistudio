### 概述
**SS AIStudio** 是一款支持多个大语言模型（LLM）服务商的桌面客户端，为了追求极致性能，采用`c++`和`Python`实现。

![image](https://github.com/user-attachments/assets/0e83b5bd-c157-4d0b-94e9-3231278b6011)
![image](https://github.com/user-attachments/assets/356a87ea-7b64-4b1d-a9e6-1fe93ff8a5eb)

### 主要特性

- 支持修改内置UI：如增加工具栏按钮，修改交互等，仅需要了解基础HTML
- 支持主流 LLM 云服务：OpenAI、ollama本地模型、硅基流动等。
- 基本对话功能：支持数学公式，代码高亮复制等
- 支持融合深度思考
- 文档与数据处理：支持本地知识库构建，支持markdown，pdf，word等
- 支持MCP(模型上下文协议) 服务：支持MCP Server管理（studio，sse等协议支持）

### 安装运行

- 本项目依赖python 3.10版本，请下载解压：http://wps.sumslack.com/Python310.zip 到本程序目录下，目录名：`Python310`
- 本项目依赖cef，请下载解压：http://wps.sumslack.com/browser.zip 到本程序目录下，目录名：`browser`
- 点击exe文件即可运行。



### 功能开发
在`html`文件夹中修改`cef_test.html`和`main.js`即可，核心类`nativeAPI`的回调函数说明：

```javascript
if(typeof(nativeAPI)!= 'undefined'){
        ((obj) => {
			// 开始接收大模型的问答
            obj.register('receiveAnswer', (param)=>{
                ......
            })
			// 开始接收思考过程
			obj.register('receiveThinking', (param)=>{
				......
            })
			// 收到问答结束回调
            obj.register('finishAnswer', ()=>{
                ......
            })
			// 收到取消动作
            obj.register('abortAnswer', ()=>{
                ......
            })
			// 收到错误信息
            obj.register('errorAnswer', (param)=>{
                ......
            })
            // 收到引用消息
            obj.register('receiveQuote', (param)=>{
                ......
            })
			// 收到MCP消息
			obj.register('receiveMcp', (param)=>{
                ......
            })
			//删除回调
			obj.register('clearHistory',(param)=>{
				......
			});
			//首次打开会话窗口的，当前历史聊天消息
            obj.register('receiveHistory', (param)=>{
                ......
            })
        })(nativeAPI)
    }
```

核心类`nativeAPI`的方法说明：

- 发送取消回答：`nativeAPI.call('stop');`
- 大模型提问：`nativeAPI.call('question', [{ role: "user", content: "你是谁？" }]);`
