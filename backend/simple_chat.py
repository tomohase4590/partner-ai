import ollama

def chat():
    """シンプルなチャット"""
    print("パートナーAI - ローカルチャット")
    print("終了するには 'exit' と入力してください\n")
    
    model = "gemma3:4b"  # または gemma3:12b, qwen2.5:32b
    history = []
    
    while True:
        user_input = input("あなた: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("さようなら！")
            break
        
        # メッセージ履歴に追加
        history.append({"role": "user", "content": user_input})
        
        # Ollama呼び出し
        response = ollama.chat(
            model=model,
            messages=history
        )
        
        ai_message = response['message']['content']
        history.append({"role": "assistant", "content": ai_message})
        
        print(f"\nAI: {ai_message}\n")

if __name__ == "__main__":
    chat()