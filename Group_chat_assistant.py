import requests
import json
import time
from datetime import datetime, timedelta
import re

RECEIVE_URL = "https://apibot.luffa.im/robot/receive"
SEND_URL = "https://apibot.luffa.im/robot/sendGroup"
OLLAMA_URL = "http://localhost:11434/api/generate"
SECRET = "your bot's secret key"
LOG_FILE = "message_log.json"

# ==== Initalize history messages ====
try:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        messages = json.load(f)
except FileNotFoundError:
    messages = []

# ==== Fetch Message ====
def fetch_messages():
    payload = {"secret": SECRET}
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(RECEIVE_URL, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        results = []
        for item in data:
            group_uid = item.get("uid", "Unknown Group")
            for msg_str in item.get("message", []):
                try:
                    msg = json.loads(msg_str)
                    msg["group"] = group_uid
                    results.append(msg)
                except json.JSONDecodeError:
                    continue
        return results
    except Exception as e:
        print("❌ Failed to fetch message", e)
        return []

# ==== Parse private message ====
def parse_message(msg):
    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sender": msg.get("uid", "Unknown User"),
        "group": msg.get("group", "Unknown Group"),
        "text": msg.get("text", "")
    }

# ==== write to log ====
def log_message(message):
    messages.append(message)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# ==== Group Message ====
def send_group_message(group_uid, text):
    payload = {
        "secret": SECRET,
        "uid": group_uid,
        "msg": json.dumps({"text": text}),
        "type": "1"
    }
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(SEND_URL, headers=headers, json=payload)
        res.raise_for_status()
        print("✅ Group message sent successfully.")
    except Exception as e:
        print("❌ Failed to send group message:", e)

# ==== Call Ollama and clean <think> ====
def call_ollama(prompt,model="qwen3:0.6b"):
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=data)
        result = response.json()
        raw = result.get("response", "").strip()
        print("🤖 Model response: ", raw)
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return cleaned
    except Exception as e:
        print("❌ Failed to fetch model: ", e)
        return "Failed to fetch model"

# ==== AI command parser ====
def interpret_command(text):
    # get the current date and time
    now = datetime.now()
    system_prompt = (
        "You are an intelligent command parser, parse the historical message time period you need to retrieve, the current time is:" + now.strftime("%Y-%m-%d %H:%M") + "。\n"
        "Please extract the following fields from user input to limit the message retrieval time range\n"
        "- type: always 'instruction'\n"
        "- start_time (optional): start time with format 'yyyy-mm-dd hh:mm'\n"
        "- end_time (optional): end time with format 'yyyy-mm-dd hh:mm'\n"
        "- range (optional): Relative time, such as 10 minutes as '0.1h', others such as '6h', 'today', 'yesterday'\n"
        "- count (optional): recent number of messages\n"
        "Return JSON\n"
        "If no useful information is specified, then return {\"type\": \"instruction\", \"start_time\": \"null\", \"end_time\": \"null\", , \"range\": \"null\", \"count\": \"null\"}\n"
    )
    response = call_ollama(system_prompt + "\n User Input" + text+ "/no_think")
    try:
        return json.loads(response)
    except:
        return {}

# ==== Filter the chat history ====
def filter_messages(group, exclude_message, time_range=None, count=None, start_time=None, end_time=None):
    now = datetime.now()
    group_msgs = [m for m in messages if m["group"] == group and "@Tao_bot" not in m["text"]]

    enriched = []
    for m in group_msgs:
        try:
            m_dt = datetime.strptime(m["time"], "%Y-%m-%d %H:%M:%S")
        except:
            m_dt = now
        enriched.append({**m, "_dt": m_dt})

    selected = []

    if start_time and end_time:
        try:
            t_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            t_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            selected = [m for m in enriched if t_start <= m["_dt"] <= t_end]
            return selected
        except:
            pass

    if time_range:
        if time_range.endswith("h"):
            cutoff = now - timedelta(hours=int(time_range[:-1]))
        elif time_range.endswith("d"):
            cutoff = now - timedelta(days=int(time_range[:-1]))
        elif time_range == "today":
            cutoff = datetime.combine(now.date(), datetime.min.time())
        elif time_range == "yesterday":
            cutoff = datetime.combine(now.date() - timedelta(days=1), datetime.min.time())
            next_day = cutoff + timedelta(days=1)
            selected = [m for m in enriched if cutoff <= m["_dt"] < next_day]
            return selected
        elif time_range == "week":
            monday = now - timedelta(days=now.weekday())
            cutoff = datetime.combine(monday.date(), datetime.min.time())
        else:
            cutoff = now - timedelta(hours=6)
        selected = [m for m in enriched if m["_dt"] >= cutoff]

    if count:
        selected_by_count = enriched[-count:]
        selected_ids = {id(m) for m in selected}
        for m in selected_by_count:
            if id(m) not in selected_ids:
                selected.append(m)

    if not selected:
        fallback = [m for m in enriched if m["_dt"] >= now - timedelta(hours=6)]
        selected = fallback if len(fallback) > 100 else enriched[-100:]

    return selected

# ==== Secondary AI question answering ====
def summarize_with_ai(command_text, history_messages):
    prompt = f"You are an intelligent assistant robot, need to answer questions by combining user chat information and your knowledge, the following is the group chat record:\n\n"
    for m in history_messages:
        prompt += f"{m['sender']}: {m['text']}\n"
    prompt += f"\n The user's question is: {command_text}, Based on the chat history and your knowledge, answer the user's question in the same language as the user's question, without saying unnecessary things /think"
    return call_ollama(prompt,model="qwen3:1.7b") # model="qwen3:1.7b"

# ==== main process ====
if __name__ == "__main__":
    print("🤖 Tao_bot test_v4 running...")
    while True:
        new_msgs = fetch_messages()
        for raw in new_msgs:
            parsed = parse_message(raw)
            log_message(parsed)
            print(f"📩 [{parsed['group']}] {parsed['sender']} -> {parsed['text']}")

            if "@Tao_bot" in parsed["text"]:
                print("🤖 Command detected. Begin parsing....")
                command = interpret_command(parsed["text"])
                selected = filter_messages(
                    parsed["group"],
                    exclude_message=parsed,
                    time_range=command.get("range"),
                    count=command.get("count"),
                    start_time=command.get("start_time"),
                    end_time=command.get("end_time")
                )
                print(f"🔍  {len(selected)} history messanges retrived")
                answer = summarize_with_ai(parsed["text"], selected)
                send_group_message(parsed["group"], f"🤖 {answer}")
        time.sleep(1)
