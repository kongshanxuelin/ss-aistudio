marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'javascript';
        return hljs.highlight(code, { language }).value;
    }
});

goPageHome = document.getElementById('goPageHome')
if(goPageHome){
    goPageHome.addEventListener('click',() => {   
        window.nativeAPI.gotoPage('./index.html')
    })
}

function renderMarkdownWithMath(text) {
    text = text.replace(/\$\$(.*?)\$\$/gs, function(_, equation) {
        return '<div class="math-block">' + katex.renderToString(equation, { displayMode: true, throwOnError: false }) + '</div>';
    });
    text = text.replace(/\$(.*?)\$/g, function(_, equation) {
        return '<span class="math-inline">' + katex.renderToString(equation, { throwOnError: false }) + '</span>';
    });
    return marked.parse(text);
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("pre").forEach(pre => {
        const button = document.createElement("button");
        button.classList.add("copy-btn");
        button.textContent = "复制";

        button.addEventListener("click", function () {
            const code = pre.querySelector("code").innerText;
            navigator.clipboard.writeText(code).then(() => {
                button.textContent = "已复制!";
                setTimeout(() => button.textContent = "复制", 2000);
            });
        });

        pre.appendChild(button);
    });
});

$(document).ready(function() {
    function sendMessage() {
        let inputText = $('#chat-input').val().trim();
        if (inputText !== '') {
            let htmlContent = renderMarkdownWithMath(inputText);
            $('#chat-box').append('<div class="chat-message sent">' + htmlContent + '</div>');

            document.querySelectorAll("pre code").forEach((block) => { hljs.highlightElement(block); });

            $('#chat-input').val('').height(40);
            $('#chat-box').scrollTop($('#chat-box')[0].scrollHeight);
            
            // setTimeout(function() {
            //     $('#chat-box').append('<div class="chat-message received">' + htmlContent + '</div>');
            //     $('#chat-box').scrollTop($('#chat-box')[0].scrollHeight);
            //     document.querySelectorAll("pre code").forEach((block) => { hljs.highlightElement(block); });
            // }, 500);
        }
    }

    $('#send-btn').click(function() {
        sendMessage();
    });

    $('#chat-input').on('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    // $('#chat-input').on('input', function() {
    //     this.style.height = 'auto';
    //     this.style.height = (this.scrollHeight) + 'px';
    // });

    $('#file-upload').change(function() {
        let fileName = this.files[0] ? this.files[0].name : "未选择文件";
        alert("选中的文件: " + fileName);
    });
});