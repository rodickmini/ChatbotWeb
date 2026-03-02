from flask import Flask, request, jsonify, render_template
import os
import json
import requests
from config import MODEL_CONFIG, APP_CONFIG

app = Flask(__name__)

# 对话存储
conversations = {}
conversation_counter = 1

# 调用本地Ollama模型
def get_model_response(prompt, history=[]):
    try:
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
            "stream": MODEL_CONFIG["stream"]
        })
        
        # 解析响应
        if response.status_code == 200:
            data = response.json()
            return data["message"]["content"]
        else:
            return f"错误：{response.status_code} - {response.text}"
    except Exception as e:
        return f"连接Ollama模型失败：{str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    
    if not conversation_id:
        # 新对话
        global conversation_counter
        conversation_id = f"conv_{conversation_counter}"
        conversation_counter += 1
        conversations[conversation_id] = []
    
    # 添加用户消息到对话历史
    conversations[conversation_id].append({'role': 'user', 'content': message})
    
    # 获取模型响应
    response = get_model_response(message, conversations[conversation_id])
    
    # 添加模型响应到对话历史
    conversations[conversation_id].append({'role': 'assistant', 'content': response})
    
    return jsonify({
        'conversation_id': conversation_id,
        'response': response,
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