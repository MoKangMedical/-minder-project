# Kimi API集成示例代码
## VoiceReminder AI - 实战代码

本文件包含完整的Kimi API集成示例，可直接用于测试和开发。

---

## Python版本 (用于测试)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi API 语音提醒解析器
用于测试Kimi API的解析效果
"""

import requests
import json
from datetime import datetime, timedelta
import re

class KimiReminderParser:
    """Kimi提醒解析器"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.moonshot.cn/v1/chat/completions"
    
    def parse_voice_text(self, voice_text):
        """
        解析语音文本
        
        Args:
            voice_text: 语音识别后的文本
            
        Returns:
            dict: 解析结果
        """
        current_time = datetime.now()
        
        # 构建Prompt
        prompt = self._build_prompt(voice_text, current_time)
        
        # 调用API
        try:
            result = self._call_kimi_api(prompt)
            return self._parse_response(result, voice_text)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_text": voice_text
            }
    
    def _build_prompt(self, text, current_time):
        """构建Prompt"""
        tomorrow = (current_time + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after_tomorrow = (current_time + timedelta(days=2)).strftime("%Y-%m-%d")
        
        return f"""你是一个专业的日程助手，请从用户的语音输入中提取提醒信息。

用户输入: "{text}"

当前时间: {current_time.strftime("%Y-%m-%d %H:%M")}
明天: {tomorrow}
后天: {day_after_tomorrow}

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
1. "明天" = {tomorrow}
2. "后天" = {day_after_tomorrow}
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
    
    def _call_kimi_api(self, prompt):
        """调用Kimi API"""
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
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        return response.json()
    
    def _parse_response(self, result, original_text):
        """解析API响应"""
        try:
            ai_response = result['choices'][0]['message']['content']
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_match:
                raise ValueError("未找到JSON格式")
            
            reminder_data = json.loads(json_match.group())
            
            # 验证和清洗数据
            reminder_data = self._validate_data(reminder_data, original_text)
            
            return {
                "success": True,
                "data": reminder_data,
                "original_text": original_text
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"解析失败: {str(e)}",
                "original_text": original_text
            }
    
    def _validate_data(self, data, original_text):
        """验证和清洗数据"""
        # 确保必填字段
        if not data.get("time"):
            data["time"] = (datetime.now().replace(hour=18, minute=0)).strftime("%Y-%m-%d %H:%M")
        
        if not data.get("title"):
            data["title"] = original_text[:20]
        
        # 设置默认值
        data.setdefault("description", original_text)
        data.setdefault("location", None)
        data.setdefault("category", "其他")
        data.setdefault("priority", "中")
        data.setdefault("repeat", "once")
        data.setdefault("tags", [])
        
        return data


# 测试代码
if __name__ == "__main__":
    # 替换成你的API Key
    API_KEY = "YOUR_KIMI_API_KEY"
    
    parser = KimiReminderParser(api_key=API_KEY)
    
    # 测试用例
    test_cases = [
        "明天下午3点和张总开会讨论Q2方案",
        "提醒我每天早上8点喝水",
        "下周一上午10点在会议室A进行产品评审",
        "3天后下午2点去健身房",
        "马上提醒我给妈妈打电话",
        "每周五晚上7点团队聚餐",
        "重要！明天上午9点提交报告",
        "有空的时候提醒我买菜"
    ]
    
    print("=" * 60)
    print("Kimi API 测试")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 #{i}")
        print(f"输入: {test}")
        print("-" * 60)
        
        result = parser.parse_voice_text(test)
        
        if result["success"]:
            print("✅ 解析成功:")
            print(json.dumps(result["data"], ensure_ascii=False, indent=2))
        else:
            print(f"❌ 解析失败: {result['error']}")
        
        print("=" * 60)
```

---

## Android版本 (Kotlin)

```kotlin
// KimiReminderParser.kt
package com.voicereminder.ai.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

/**
 * Kimi提醒解析器
 */
class KimiReminderParser(private val apiKey: String) {
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()
    
    private val apiUrl = "https://api.moonshot.cn/v1/chat/completions"
    
    /**
     * 解析语音文本
     */
    suspend fun parseVoiceText(voiceText: String): ReminderResult {
        return withContext(Dispatchers.IO) {
            try {
                val prompt = buildPrompt(voiceText)
                val response = callKimiApi(prompt)
                parseResponse(response, voiceText)
            } catch (e: Exception) {
                ReminderResult(
                    success = false,
                    error = e.message,
                    originalText = voiceText
                )
            }
        }
    }
    
    /**
     * 构建Prompt
     */
    private fun buildPrompt(text: String): String {
        val currentTime = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
            .format(Date())
        
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.DAY_OF_MONTH, 1)
        val tomorrow = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            .format(calendar.time)
        
        return """
你是一个专业的日程助手，请从用户的语音输入中提取提醒信息。

用户输入: "$text"

当前时间: $currentTime
明天: $tomorrow

请严格按照以下JSON格式返回：
{
  "time": "YYYY-MM-DD HH:mm",
  "title": "事项标题",
  "description": "详细描述",
  "location": "地点或null",
  "category": "工作/生活/学习/其他",
  "priority": "高/中/低",
  "repeat": "once/daily/weekly/monthly",
  "tags": ["标签1", "标签2"]
}

时间识别规则：
1. "明天" = $tomorrow
2. 如果没有明确时间，默认为18:00
3. "马上"、"立刻" = 当前时间+5分钟

请直接返回JSON，不要有任何解释。
        """.trimIndent()
    }
    
    /**
     * 调用Kimi API
     */
    private fun callKimiApi(prompt: String): String {
        val json = JSONObject().apply {
            put("model", "moonshot-v1-32k")
            put("messages", JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "system")
                    put("content", "你是一个专业的日程解析助手。")
                })
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            })
            put("temperature", 0.3)
            put("max_tokens", 500)
        }
        
        val requestBody = json.toString()
            .toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(apiUrl)
            .addHeader("Authorization", "Bearer $apiKey")
            .addHeader("Content-Type", "application/json")
            .post(requestBody)
            .build()
        
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw Exception("API调用失败: ${response.code}")
            }
            return response.body?.string() ?: throw Exception("响应为空")
        }
    }
    
    /**
     * 解析API响应
     */
    private fun parseResponse(response: String, originalText: String): ReminderResult {
        return try {
            val jsonResponse = JSONObject(response)
            val content = jsonResponse
                .getJSONArray("choices")
                .getJSONObject(0)
                .getJSONObject("message")
                .getString("content")
            
            // 提取JSON
            val jsonMatch = Regex("\\{.*\\}", RegexOption.DOT_MATCHES_ALL)
                .find(content)?.value
                ?: throw Exception("未找到JSON格式")
            
            val reminderData = JSONObject(jsonMatch)
            
            ReminderResult(
                success = true,
                data = ReminderData(
                    time = reminderData.optString("time", ""),
                    title = reminderData.optString("title", originalText.take(20)),
                    description = reminderData.optString("description", originalText),
                    location = reminderData.optString("location", null),
                    category = reminderData.optString("category", "其他"),
                    priority = reminderData.optString("priority", "中"),
                    repeat = reminderData.optString("repeat", "once"),
                    tags = reminderData.optJSONArray("tags")?.let { array ->
                        List(array.length()) { array.getString(it) }
                    } ?: emptyList()
                ),
                originalText = originalText
            )
        } catch (e: Exception) {
            ReminderResult(
                success = false,
                error = "解析失败: ${e.message}",
                originalText = originalText
            )
        }
    }
}

/**
 * 提醒数据
 */
data class ReminderData(
    val time: String,
    val title: String,
    val description: String,
    val location: String?,
    val category: String,
    val priority: String,
    val repeat: String,
    val tags: List<String>
)

/**
 * 解析结果
 */
data class ReminderResult(
    val success: Boolean,
    val data: ReminderData? = null,
    val error: String? = null,
    val originalText: String
)

// 使用示例
/*
val parser = KimiReminderParser(apiKey = "YOUR_API_KEY")

lifecycleScope.launch {
    val result = parser.parseVoiceText("明天下午3点开会")
    
    if (result.success) {
        val data = result.data!!
        println("时间: ${data.time}")
        println("标题: ${data.title}")
        println("分类: ${data.category}")
    } else {
        println("错误: ${result.error}")
    }
}
*/
```

---

## 使用说明

### Python版本

1. **安装依赖**:
```bash
pip install requests
```

2. **替换API Key**:
```python
API_KEY = "你的Kimi API Key"
```

3. **运行测试**:
```bash
python kimi_parser.py
```

### Android版本

1. **添加依赖** (build.gradle):
```gradle
dependencies {
    implementation 'com.squareup.okhttp3:okhttp:4.11.0'
    implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.1'
}
```

2. **添加权限** (AndroidManifest.xml):
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

3. **使用示例**:
```kotlin
val parser = KimiReminderParser(apiKey = "YOUR_API_KEY")

lifecycleScope.launch {
    val result = parser.parseVoiceText("明天下午3点开会")
    
    if (result.success) {
        // 创建提醒
        createReminder(result.data!!)
    } else {
        // 显示错误
        showError(result.error)
    }
}
```

---

## 测试结果示例

### 输入
```
"明天下午3点和张总开会讨论Q2方案"
```

### 输出
```json
{
  "success": true,
  "data": {
    "time": "2026-02-09 15:00",
    "title": "和张总开会",
    "description": "讨论Q2方案",
    "location": null,
    "category": "工作",
    "priority": "中",
    "repeat": "once",
    "tags": ["会议", "Q2"]
  },
  "original_text": "明天下午3点和张总开会讨论Q2方案"
}
```

---

## 常见问题

### Q1: API调用失败怎么办？
**A**: 检查以下几点：
1. API Key是否正确
2. 网络连接是否正常
3. 是否有足够的余额
4. 请求格式是否正确

### Q2: 解析结果不准确怎么办？
**A**: 可以：
1. 优化Prompt
2. 调整temperature参数
3. 增加更多示例
4. 收集错误样本优化

### Q3: 成本太高怎么办？
**A**: 
1. 设置免费用户调用上限
2. 缓存常见解析结果
3. 开发规则引擎作为降级方案

---

**文件创建**: 2026-02-08  
**最后更新**: 2026-02-08
