mkdir -p log

# 모델 서버 실행 (백그라운드)
CUDA_VISIBLE_DEVICES=0 vllm serve MLP-KTLim/llama-3-Korean-Bllossom-8B --port 8000 > log/Bllossom-8B_model_server.log 2>&1 &

# 임베더 실행 (백그라운드)
CUDA_VISIBLE_DEVICES= vllm serve Qwen/Qwen2.5-7B-Instruct --task embedding --port 9000 > log/qwen_embedding_server.log 2>&1 &

# 실행 상태 출력
echo "Servers are running in the background:"
echo "- Bllossom-8B model logs: log/Bllossom-8B_model_server.log"
echo "- Qwen2.5-7B embedder logs: log/qwen_embedding_server.log"

# 로그 크기 제한 로직 (주기적으로 실행)
MAX_SIZE=100000 # 10MB
while true; do
    for LOG_FILE in log/Bllossom-8B_model_server.log log/qwen_embedding_server.log; do
        if [ -f "$LOG_FILE" ]; then
            FILE_SIZE=$(stat -c%s "$LOG_FILE")
            if [ $FILE_SIZE -gt $MAX_SIZE ]; then
                # 파일을 절반으로 줄임
                tail -c $((FILE_SIZE/2)) "$LOG_FILE" > "$LOG_FILE.tmp"
                mv "$LOG_FILE.tmp" "$LOG_FILE"
            fi
        fi
    done
    sleep 600
done &

# 프로세스 종료시 
# pkill -f "port 8000" && pkill -f "port 9000"
# fuser -k 8000/tcp && fuser -k 9000/tcp