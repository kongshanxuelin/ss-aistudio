marked.setOptions({ gfm: true, breaks: true });
window.MathJax = {
    tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']]
    }
};

var isLoading = false;

// 最后接收消息的dom节点信息
var domDiv = null;
var responseContent = '';
var responseContentThink = '';
var mcpCalls = [];

var think_start = 0;
var messageResv = null;
var messageSend = null;

var tmpl_msg_resv = `<div class='thinking'><h4 class='quote-thinking-head' onclick="javascript:$(this).next().toggle()"></h4><div class='quote-thinking'></div></div><div class='mcplist'></div><div class='ans-content'></div>`;

//存储全部上下文消息
var messes = []

function initBtnCopy() {
	$('#chat-box').on('click','.copy-btn',function(){
		var button = $(this);
		let codeBlock = button.parent().parent().find('code');
		let textArea = document.createElement("textarea");
		textArea.value = codeBlock.text();
		document.body.appendChild(textArea);
		textArea.select();
		document.execCommand("copy");
		document.body.removeChild(textArea);
		button.text("已复制!");
		setTimeout(() => { button.text("复制"); }, 1500);
	});
}

function renderCopyBtn(){
	$("pre").each(function(){
		var parentDiv = $(this).parent();
		if(parentDiv.is('div') && parentDiv.hasClass('code-block')){
			
		}else{
			var $wrapper = $(this).wrap('<div class="code-block"></div>');
			var lang = $(this).find("code").prop('class');
			var lang_code = '';
			const match = lang.match(/language-(\w+)/);
			if (match && match[1]) {
				lang_code = match[1];
			}
			var $html = '<div class="d-flex justify-content-between align-items-center" style="padding:0px 12px;background-color:#585a73;color:#fafafc">'+
						'<span>'+lang_code+'</span>'+
						'<button type="button" class="btn btn-default copy-btn">复制</button>'+
						'</div>';
			$($html).prependTo($wrapper);
		}
	});
}
function ischeckedChat(){
    return $('#chk_lianxu').is(':checked');
}
function renderThinking(){
	const endTime = new Date();
	if(responseContentThink!=""){
		$(domDiv).find(".thinking").show();
		var secs = (1.0*(endTime - think_start) / 1000).toFixed(2);
		var tip = '已深度思考';
		if(secs > 1){
			tip = `已深度思考（用时 ${secs} 秒）`;
		}
		$(domDiv).find(".thinking > h4").html(tip);
		$(domDiv).find(".quote-thinking").html(responseContentThink);
	}
}

function renderMCPList(){
	$(domDiv).find(".mcplist").empty();
	if(mcpCalls.length > 0){
		$(domDiv).find(".mcplist").show();
  	    var html = "";
		for(var k=0;k<mcpCalls.length;k++){
			var param = mcpCalls[k];
			for(var i=0;i<param.length;i+=2){
			  var funcObj = param[i];
			  var funcResult = param[i+1];
			  var func = "",resp="";
			  if(funcObj.role && funcObj.role === "assistant"){
				func = funcObj.tool_calls[0].function.name.split(":")[1];
				if(funcResult.content.indexOf("失败")>0){
					func += "<span class='func-error'>调用失败</span>";
				}else{
					func += "<span class='func-succ'>已完成</span>";
				}
				console.log("func:",func);
			  }
			  if(funcResult){
				var formattedJson = funcResult.content;  
				if(formattedJson.indexOf("失败")>0){
					formattedJson = funcResult.content;
				}else{
					jsonObject = JSON.parse(formattedJson);
					formattedJson = JSON.stringify(jsonObject, null, 2);
				}
				resp = "<pre><code class='language-json hljs' data-highlighted='yes'>"+formattedJson+"</code></pre>";
			  }					  
  			  html += `<div class='mcplist-item'><h4 class='quote-mcp-head' onclick="javascript:$(this).next().toggle()">${func}</h4><div class='quote-mcp'>${resp}</div></div>`;
			}
		}
		$(domDiv).find(".mcplist").html(html);
		hljs.highlightAll();
	}
}

function addMessageSent(message) {
	$('#chat-box').append(`<div class='message sent'>${message}</div>`);
    $('#chat-box').scrollTop($('#chat-box')[0].scrollHeight);
}

function addMessageRecv(text){
	if(typeof(domDiv) == "undefined" || domDiv == null){
		messageResv = document.createElement('div');
        messageResv.classList.add('message', 'received');
		messageResv.innerHTML = tmpl_msg_resv;
        document.getElementById('chat-box').appendChild(messageResv);
		domDiv = messageResv;
	}
	$(domDiv).find(".ans-content").html(text);
	MathJax.typesetPromise([domDiv]);
	html = $(domDiv).find(".ans-content").html();
	html = marked.parse(html);
	$(domDiv).find(".ans-content").html(html);
	renderThinking();
	renderMCPList();
	$('#chat-box').scrollTop($('#chat-box')[0].scrollHeight);
}

function updateUIState() {
    if(isLoading){
        $('#send-btn').text('取消');
    }else{
        $('#send-btn').text('发送');
    }
    $('#message-input').prop('disabled', isLoading);
}

function sendStopMessage() {
	console.log('sendStopMessage');
	nativeAPI.call('stop');
}
function renderAll(){
	$(".received").each(function(){  
	  MathJax.typesetPromise([this]);
	  html = "<div class='ans-content'>" + marked.parse($(this).html()) + "</div>";
	  $(this).html(html);
	});
    hljs.highlightAll();
	renderCopyBtn();
	initBtnCopy();
}
function gclear(){
	responseContent = '';
	responseContentThink = '';
	mcpCalls = [];
	domDiv = null;
}
$(document).ready(function() {
	initBtnCopy();
	console.log("xxxx");
    if(typeof(nativeAPI)!= 'undefined'){
        ((obj) => {
            obj.register('receiveAnswer', (param)=>{
				console.log("receiveAnswer");
				responseContentThink = '';
                responseContent += param;
                addMessageRecv(responseContent);
            })
			obj.register('receiveThinking', (param)=>{
				console.log("receiveThinking");
				if(responseContentThink == ''){
					think_start = new Date();
				}
				responseContentThink += param;
                addMessageRecv('');
            })
            obj.register('finishAnswer', ()=>{
                isLoading = false;
				gclear();
                updateUIState();
                hljs.highlightAll();
				renderCopyBtn();
				initBtnCopy();
            })
            obj.register('abortAnswer', ()=>{
                isLoading = false;
				gclear();
                updateUIState();
                renderCopyBtn();
            })
            obj.register('errorAnswer', (param)=>{
                addMessageRecv("ERROR:"+param);
				gclear();
            })
            // 收到引用消息
            obj.register('receiveQuote', (param)=>{
                console.log('引用消息:',param);
				var html = "<ul>";
				for(var i=0;i<param.length;i++){
					var item = param[i];
					html += "<li id='" + item.docId + "'>" + item.fileName + "</li>";
				}
				html += "</ul>";
				$('#chat-box').append(`<div class='message ${messageClass}'>${renderedMessage}</div>`);
            })
			// 收到MCP消息
			obj.register('receiveMcp', (param)=>{
                console.log('MCP Server消息:',typeof(param),param);
				if(typeof(param)=='string'){
					param = JSON.parse(param);
				}
				mcpCalls.push(param);
            })
			//删除回调
			obj.register('clearHistory',(param)=>{
				console.log("清空当前会话消息。");
				$("#chat-box").empty();
			});
            obj.register('receiveHistory', (param)=>{
                console.log('receiveHistory:',param);
				param = param.historyList;
                for (let i = 0; i < param.length; i++) {
					think_start = new Date();
					domDiv = null;
					var type = 'received';
                    const role = param[i].role;
					if(role == 'user'){
						type = 'sent';
					}
					responseContent = param[i].content;
					//思考过程
					if(typeof(param[i].thinking) != "undefined"){
						responseContentThink = param[i].thinking;
					}else{
						responseContentThink = '';
					}
					//mcp calls
					if(typeof(param[i].mcpCalls) != "undefined"){
						mcpCalls = param[i].mcpCalls;
					}else{
						mcpCalls = [];
					}
					if(type=='sent'){
						addMessageSent(responseContent);
					}else{
						addMessageRecv(responseContent);
					}
                }
				renderAll();
				gclear();
            })
        })(nativeAPI)
    }

    $('#clear-btn').click(function() {
        addMessageRecv('已清除上下文！');
        messes = [];
    });

    $("#clear-msg-btn").click(function(){
        messes = [];
        $('#chat-box').html('');       
        addMessageRecv('现在你可以开始提问了！'); 
    });

    $('#send-btn').click(function() {
        if($('#send-btn').text() == '取消'){
            console.log('触发取消请求');
            if(typeof(nativeAPI) != 'undefined'){
                nativeAPI.call('stop');
            }
            isLoading = false;
            updateUIState();
            $('#send-btn').prop('disabled', true);
			$('#chat-input').val('');
            return;
        }
        let message = $('#chat-input').val().trim();
        if (message !== '') {
            messes.push({ role: "user", content: message });
            addMessageSent(message);		
            $('#chat-input').val('');

            responseContent = '';
			responseContentThink = '';
            isLoading = true;
            $('#chat-input').val('');
            if(typeof(nativeAPI) != 'undefined'){
                var succ = null;
                if(ischeckedChat()){
                    succ = nativeAPI.call('question', messes);
                }else{
                    succ = nativeAPI.call('question', [{ role: "user", content: message }]);    
                }
			    console.log('succ:' + succ);
            }
            updateUIState();
            addMessageRecv('处理中...');
        }
    });

    $('#chat-input').keypress(function(e) {
        if (e.which === 13) { 
		    event.preventDefault(); 
			$('#send-btn').click(); 
		}
    });

    $('#chat-input').keyup(function(e) {
        if($(this).val().length > 0 || $('#send-btn').text() == '取消'){
            $('#send-btn').prop('disabled', false);
        }else{
            $('#send-btn').prop('disabled', true);
        }
    });
});


