# API设计文档
## VoiceReminder AI - 后端接口设计

**版本**: v1.0  
**日期**: 2026-02-08

---

## 1. Kimi API集成

### 1.1 API配置
```python
# config.py
KIMI_API_KEY = "your_kimi_api_key"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = "moonshot-v1-32k"  # Kimi 2.5模型
```

### 1.2 核心解析函数

```python
import requests
import json
from datetime import datetime, timedelta
import re

class KimiReminderParser:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.moonshot.cn/v1/chat/completions"
        
    def parse_voice_text(self, voice_text):
        """
        解析语音文本，提取提醒信息
        
        参数:
            voice_text (str): 语音识别后的文本
            
        返回:
            dict: 结构化的提醒信息
        """
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        current_datetime = current_time.strftime("%Y-%m-%d %H:%M")
        
        # 构建Prompt
        prompt = f"""你是一个专业的日程助手，请从用户的语音输入中提取以下信息。

用户输入: "{voice_text}"

当前时间: {current_datetime}

请严格按照以下JSON格式返回，不要添加任何其他文字：
{{
  "time": "YYYY-MM-DD HH:mm",
  "title": "事项标题",
  "description": "详细描述",
  "location": "地点或null",
  "category": "工作/生活/学习/其他",
  "priority": "高/中/低",
  "repeat": "once/daily/weekly/monthly",
  "tags": ["标签1", "标签2"]
}}

时间识别规则：
1. "明天" = {(current_time + timedelta(days=1)).strftime("%Y-%m-%d")}
2. "后天" = {(current_time + timedelta(days=2)).strftime("%Y-%m-%d")}
3. "下周一" = 计算下周一的日期
4. "3天后" = {(current_time + timedelta(days=3)).strftime("%Y-%m-%d")}
5. 如果只说了时间没说日期，默认为今天
6. 如果没有明确时间，默认为18:00
7. "马上"、"立刻" = 当前时间+5分钟

优先级判断：
- 包含"紧急"、"重要"、"马上"、"立刻" → 高
- 包含"可以"、"有空"、"随时" → 低
- 其他 → 中

分类判断：
- 包含"会议"、"汇报"、"项目"、"工作" → 工作
- 包含"学习"、"课程"、"培训"、"考试" → 学习
- 包含"健身"、"购物"、"吃饭"、"家人" → 生活
- 其他 → 其他

请直接返回JSON，不要有任何解释。"""

        # 调用Kimi API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "moonshot-v1-32k",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的日程解析助手，擅长从自然语言中提取时间、事项等关键信息。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # 降低随机性，提高准确性
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # 提取JSON（处理可能的markdown代码块）
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                reminder_data = json.loads(json_match.group())
                
                # 数据验证和清洗
                reminder_data = self._validate_and_clean(reminder_data, voice_text)
                
                return {
                    "success": True,
                    "data": reminder_data,
                    "original_text": voice_text
                }
            else:
                return {
                    "success": False,
                    "error": "AI返回格式错误",
                    "original_text": voice_text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API调用失败: {str(e)}",
                "original_text": voice_text
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析失败: {str(e)}",
                "original_text": voice_text
            }
    
    def _validate_and_clean(self, data, original_text):
        """验证和清洗AI返回的数据"""
        # 确保必填字段存在
        if not data.get("time"):
            # 默认为今天18:00
            data["time"] = (datetime.now().replace(hour=18, minute=0)).strftime("%Y-%m-%d %H:%M")
        
        if not data.get("title"):
            # 使用原始文本的前20个字符作为标题
            data["title"] = original_text[:20]
        
        # 设置默认值
        data.setdefault("description", original_text)
        data.setdefault("location", None)
        data.setdefault("category", "其他")
        data.setdefault("priority", "中")
        data.setdefault("repeat", "once")
        data.setdefault("tags", [])
        
        # 验证枚举值
        valid_categories = ["工作", "生活", "学习", "其他"]
        if data["category"] not in valid_categories:
            data["category"] = "其他"
        
        valid_priorities = ["高", "中", "低"]
        if data["priority"] not in valid_priorities:
            data["priority"] = "中"
        
        valid_repeats = ["once", "daily", "weekly", "monthly"]
        if data["repeat"] not in valid_repeats:
            data["repeat"] = "once"
        
        return data


# 使用示例
if __name__ == "__main__":
    parser = KimiReminderParser(api_key="your_api_key_here")
    
    # 测试用例
    test_cases = [
        "明天下午3点和张总开会讨论Q2方案",
        "提醒我每天早上8点喝水",
        "下周一上午10点在会议室A进行产品评审",
        "3天后下午2点去健身房",
        "马上提醒我给妈妈打电话",
        "每周五晚上7点团队聚餐"
    ]
    
    for test in test_cases:
        print(f"\n输入: {test}")
        result = parser.parse_voice_text(test)
        if result["success"]:
            print(f"解析成功:")
            print(json.dumps(result["data"], ensure_ascii=False, indent=2))
        else:
            print(f"解析失败: {result['error']}")
```

---

## 2. 语音识别API集成

### 2.1 讯飞语音识别（推荐）

```python
import websocket
import json
import base64
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time

class XunfeiASR:
    """讯飞语音识别"""
    
    def __init__(self, app_id, api_key, api_secret):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = "wss://iat-api.xfyun.cn/v2/iat"
        
    def create_url(self):
        """生成鉴权URL"""
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        signature_origin = f"host: iat-api.xfyun.cn\ndate: {date}\nGET /v2/iat HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        values = {
            "authorization": authorization,
            "date": date,
            "host": "iat-api.xfyun.cn"
        }
        
        return self.url + '?' + urlencode(values)
    
    def recognize(self, audio_file_path):
        """
        识别音频文件
        
        参数:
            audio_file_path (str): 音频文件路径（PCM/WAV格式）
            
        返回:
            str: 识别结果文本
        """
        result_text = ""
        
        def on_message(ws, message):
            nonlocal result_text
            data = json.loads(message)
            if data['code'] != 0:
                print(f"识别错误: {data['message']}")
                return
            
            result = data['data']['result']
            for item in result['ws']:
                for word in item['cw']:
                    result_text += word['w']
        
        def on_open(ws):
            # 读取音频文件并发送
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
                
            # 分帧发送
            frame_size = 1280  # 每帧大小
            status = 0  # 0:首帧 1:中间帧 2:尾帧
            
            for i in range(0, len(audio_data), frame_size):
                frame = audio_data[i:i+frame_size]
                
                if i == 0:
                    status = 0
                elif i + frame_size >= len(audio_data):
                    status = 2
                else:
                    status = 1
                
                params = {
                    "common": {"app_id": self.app_id},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin"
                    },
                    "data": {
                        "status": status,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(frame).decode()
                    }
                }
                
                ws.send(json.dumps(params))
        
        ws_url = self.create_url()
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_open=on_open
        )
        
        ws.run_forever()
        return result_text


# Android端调用示例（Java）
"""
// 使用讯飞Android SDK
import com.iflytek.cloud.SpeechRecognizer;
import com.iflytek.cloud.RecognizerListener;

public class VoiceRecognizer {
    private SpeechRecognizer recognizer;
    
    public void startRecognition() {
        recognizer = SpeechRecognizer.createRecognizer(context, null);
        
        // 设置参数
        recognizer.setParameter(SpeechConstant.DOMAIN, "iat");
        recognizer.setParameter(SpeechConstant.LANGUAGE, "zh_cn");
        recognizer.setParameter(SpeechConstant.ACCENT, "mandarin");
        
        // 开始识别
        recognizer.startListening(new RecognizerListener() {
            @Override
            public void onResult(RecognizerResult result, boolean isLast) {
                String text = parseResult(result);
                // 调用Kimi API解析
                parseWithKimi(text);
            }
        });
    }
}
"""
```

---

## 3. Android本地数据库设计

### 3.1 数据库Schema

```sql
-- 提醒表
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,                    -- 标题
    description TEXT,                       -- 描述
    reminder_time DATETIME NOT NULL,        -- 提醒时间
    location TEXT,                          -- 地点
    category TEXT DEFAULT '其他',           -- 分类
    priority TEXT DEFAULT '中',             -- 优先级
    repeat_type TEXT DEFAULT 'once',        -- 重复类型
    tags TEXT,                              -- 标签（JSON数组）
    is_completed INTEGER DEFAULT 0,         -- 是否完成
    calendar_event_id INTEGER,              -- 系统日历事件ID
    original_voice_text TEXT,               -- 原始语音文本
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 语音记录表（用于统计和优化）
CREATE TABLE voice_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_text TEXT NOT NULL,               -- 语音识别文本
    ai_parse_result TEXT,                   -- AI解析结果（JSON）
    parse_success INTEGER DEFAULT 1,        -- 解析是否成功
    user_modified INTEGER DEFAULT 0,        -- 用户是否修改
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户设置表
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 索引
CREATE INDEX idx_reminder_time ON reminders(reminder_time);
CREATE INDEX idx_category ON reminders(category);
CREATE INDEX idx_is_completed ON reminders(is_completed);
```

### 3.2 数据访问层（DAO）

```kotlin
// ReminderDao.kt
@Dao
interface ReminderDao {
    @Query("SELECT * FROM reminders WHERE is_completed = 0 ORDER BY reminder_time ASC")
    fun getActiveReminders(): List<Reminder>
    
    @Query("SELECT * FROM reminders WHERE DATE(reminder_time) = DATE('now') AND is_completed = 0")
    fun getTodayReminders(): List<Reminder>
    
    @Insert
    fun insert(reminder: Reminder): Long
    
    @Update
    fun update(reminder: Reminder)
    
    @Delete
    fun delete(reminder: Reminder)
    
    @Query("UPDATE reminders SET is_completed = 1 WHERE id = :id")
    fun markAsCompleted(id: Long)
}

// Reminder实体类
@Entity(tableName = "reminders")
data class Reminder(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    val description: String?,
    val reminderTime: Long,  // Unix timestamp
    val location: String?,
    val category: String,
    val priority: String,
    val repeatType: String,
    val tags: String?,  // JSON array
    val isCompleted: Boolean = false,
    val calendarEventId: Long?,
    val originalVoiceText: String?,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)
```

---

## 4. API调用成本估算

### 4.1 Kimi API定价（参考）
- 输入: ¥0.012 / 1K tokens
- 输出: ¥0.012 / 1K tokens
- 平均每次解析: ~500 tokens
- 单次成本: ¥0.006

### 4.2 月度成本预估

| 用户规模 | 日均调用 | 月度调用 | 月度成本 |
|---------|---------|---------|---------|
| 100人 | 500次 | 15,000次 | ¥90 |
| 1000人 | 5000次 | 150,000次 | ¥900 |
| 10000人 | 50000次 | 1,500,000次 | ¥9,000 |

**成本优化策略**:
1. 免费用户每日5次限制
2. 会员无限次（¥9.9/月）
3. 缓存常见解析结果
4. 批量调用优化

---

## 5. 错误处理

### 5.1 错误码定义

```python
ERROR_CODES = {
    1001: "语音识别失败",
    1002: "AI解析失败",
    1003: "时间格式错误",
    1004: "日历创建失败",
    1005: "网络连接失败",
    1006: "API调用超限",
    1007: "权限不足"
}
```

### 5.2 降级方案

```python
def parse_with_fallback(voice_text):
    """带降级的解析函数"""
    try:
        # 尝试Kimi API
        result = kimi_parser.parse(voice_text)
        if result["success"]:
            return result
    except Exception as e:
        log_error(e)
    
    # 降级到规则解析
    try:
        result = rule_based_parser.parse(voice_text)
        return result
    except Exception as e:
        log_error(e)
    
    # 最终降级：手动输入
    return {
        "success": False,
        "fallback": True,
        "message": "AI解析失败，请手动输入"
    }
```

---

## 6. 测试用例

### 6.1 时间解析测试

```python
test_cases = [
    # 绝对时间
    ("明天下午3点开会", "2026-02-09 15:00"),
    ("2月10号上午10点", "2026-02-10 10:00"),
    
    # 相对时间
    ("3天后下午2点", "2026-02-11 14:00"),
    ("下周一早上9点", "2026-02-10 09:00"),
    
    # 模糊时间
    ("明天早上", "2026-02-09 09:00"),
    ("今晚", "2026-02-08 19:00"),
    
    # 紧急时间
    ("马上提醒我", "2026-02-08 14:05"),  # 当前时间+5分钟
    
    # 重复时间
    ("每天早上8点", "daily"),
    ("每周五下午6点", "weekly")
]
```

---

**文档状态**: ✅ 已完成  
**维护人**: 技术团队
