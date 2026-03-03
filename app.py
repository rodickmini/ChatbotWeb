from flask import Flask, request, jsonify, render_template
import os
import json
import requests
from openai import OpenAI
from config import MODEL_CONFIG, DEEPSEEK_CONFIG, DEFAULT_MODEL, APP_CONFIG

app = Flask(__name__)

# 对话存储
conversations = {}
conversation_counter = 1

# 调用模型（支持流式输出）
def get_model_response(prompt, history=[], stream=False):
    try:
        if DEFAULT_MODEL == "deepseek":
            # 调用DeepSeek模型
            client = OpenAI(
                api_key=DEEPSEEK_CONFIG["api_key"],
                base_url=DEEPSEEK_CONFIG["api_url"]
            )
            
            # 构建消息历史
            messages = []
            # 添加系统消息
            messages.append({
                "role": "system",
                "content": "你是一个聪明、严谨的 AI 助手。请在给出最终答案前，先进行充分的逻辑推导。"
            })
            # 添加历史消息
            for msg in history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 发送请求到DeepSeek
            response = client.chat.completions.create(
                model=DEEPSEEK_CONFIG["model_name"],
                messages=messages,
                temperature=0.6,
                max_tokens=4096,
                stream=stream,
                extra_body=DEEPSEEK_CONFIG["extra_body"]
            )
            
            return response
        else:
            # 调用本地Ollama模型
            # 构建Ollama API请求
            url = MODEL_CONFIG["api_url"]
            
            # 构建消息历史
            messages = []
            for msg in history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 发送请求到Ollama
            response = requests.post(url, json={
                "model": MODEL_CONFIG["model_name"],  # 使用配置文件中指定的模型
                "messages": messages,
                "stream": stream
            }, stream=stream)
            
            return response
    except Exception as e:
        if DEFAULT_MODEL == "deepseek":
            return f"连接DeepSeek模型失败：{str(e)}"
        else:
            return f"连接本地模型失败：{str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    stream = data.get('stream', True)  # 默认使用流式输出
    
    if not conversation_id:
        # 新对话
        global conversation_counter
        conversation_id = f"conv_{conversation_counter}"
        conversation_counter += 1
        conversations[conversation_id] = []
    
    # 添加用户消息到对话历史
    conversations[conversation_id].append({'role': 'user', 'content': message})
    
    # 获取模型响应
    response = get_model_response(message, conversations[conversation_id], stream)
    
    # 检查是否为错误响应
    if isinstance(response, str) and (response.startswith("连接") or "失败" in response):
        # 添加错误响应到对话历史
        conversations[conversation_id].append({'role': 'assistant', 'content': response})
        return jsonify({
            'conversation_id': conversation_id,
            'response': response,
            'history': conversations[conversation_id],
            'error': True
        })
    
    # 处理流式响应
    if stream:
        if DEFAULT_MODEL == "deepseek":
            # 处理DeepSeek流式响应
            def generate():
                full_response = ""
                for chunk in response:
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            content = delta.content
                            full_response += content
                            yield f"data: {json.dumps({'chunk': content, 'conversation_id': conversation_id})}\n\n"
                # 添加完整响应到对话历史
                conversations[conversation_id].append({'role': 'assistant', 'content': full_response})
                yield f"data: {json.dumps({'complete': True, 'conversation_id': conversation_id})}\n\n"
            return app.response_class(generate(), mimetype='text/event-stream')
        else:
            # 处理本地Ollama模型流式响应
            def generate():
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'message' in data and 'content' in data['message']:
                                content = data['message']['content']
                                if content:
                                    full_response += content
                                    yield f"data: {json.dumps({'chunk': content, 'conversation_id': conversation_id})}\n\n"
                        except json.JSONDecodeError:
                            pass
                # 添加完整响应到对话历史
                conversations[conversation_id].append({'role': 'assistant', 'content': full_response})
                yield f"data: {json.dumps({'complete': True, 'conversation_id': conversation_id})}\n\n"
            return app.response_class(generate(), mimetype='text/event-stream')
    else:
        # 处理非流式响应
        if DEFAULT_MODEL == "deepseek":
            # 处理DeepSeek非流式响应
            full_response = response.choices[0].message.content if response.choices else "模型未返回有效响应"
        else:
            # 处理本地Ollama模型非流式响应
            if response.status_code == 200:
                data = response.json()
                full_response = data["message"]["content"]
            else:
                full_response = f"错误：{response.status_code} - {response.text}"
        
        # 添加完整响应到对话历史
        conversations[conversation_id].append({'role': 'assistant', 'content': full_response})
        
        return jsonify({
            'conversation_id': conversation_id,
            'response': full_response,
            'history': conversations[conversation_id]
        })

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    # 返回所有对话的基本信息
    conv_list = []
    for conv_id, messages in conversations.items():
        if messages:
            # 使用第一条消息作为对话标题
            title = messages[0]['content'][:50] + '...' if len(messages[0]['content']) > 50 else messages[0]['content']
        else:
            title = '空对话'
        conv_list.append({
            'id': conv_id,
            'title': title,
            'message_count': len(messages)
        })
    return jsonify(conv_list)

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    if conversation_id in conversations:
        return jsonify({
            'conversation_id': conversation_id,
            'history': conversations[conversation_id]
        })
    return jsonify({'error': 'Conversation not found'}), 404

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    if conversation_id in conversations:
        del conversations[conversation_id]
        return jsonify({'success': True})
    return jsonify({'error': 'Conversation not found'}), 404

if __name__ == '__main__':
    app.run(
        debug=APP_CONFIG["debug"],
        host=APP_CONFIG["host"],
        port=APP_CONFIG["port"]
    )