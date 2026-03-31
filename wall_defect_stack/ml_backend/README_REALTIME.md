# 实时上传模式使用说明

## 🚀 功能特点

本 ML Backend 已配置为**实时上传模式**：
- ✅ 每处理完一个任务立即上传到 Label Studio
- ✅ 支持大批量任务（默认最多 10000 个）
- ✅ 避免 HTTP 超时问题
- ✅ 即使浏览器超时，已处理的结果仍会保存

---

## 📋 使用步骤

### 1️⃣ 配置 Label Studio 连接信息

在启动 ML Backend 之前，需要设置以下环境变量：

```bash
# Label Studio 地址
export LABEL_STUDIO_URL=http://localhost:8080

# Label Studio API Token
export LABEL_STUDIO_API_KEY=your_api_token_here
```

**获取 API Token 的方法：**
1. 登录 Label Studio
2. 点击右上角头像
3. 选择 **Account & Settings**
4. 找到并复制 **Access Token**

### 2️⃣ 启动 ML Backend

```bash
cd "/home/star/jiaojiao/Label Studio/wall_defect_stack/ml_backend"
python app.py
```

### 3️⃣ 在 Label Studio 中使用

1. 打开 Label Studio 项目
2. 选择要预测的任务（可以全选，比如 1566 个任务）
3. 点击 **Actions → Retrieve Predictions**
4. 等待处理完成

**重要提示：**
- ⚠️ 浏览器可能在 60-120 秒后显示超时，这是正常的
- ⚠️ 后端仍在继续处理，每完成一个任务就会上传
- ✅ 处理完成后**刷新页面**即可看到所有预测结果

---

## 📊 工作原理

```
传统批量模式（已弃用）：
处理任务1 → 处理任务2 → ... → 处理任务1566 → 一次性返回所有结果
❌ 问题：处理时间过长导致 HTTP 超时

实时上传模式（当前）：
处理任务1 → 立即上传 ✅
处理任务2 → 立即上传 ✅
处理任务3 → 立即上传 ✅
...
处理任务1566 → 立即上传 ✅
✅ 优势：每个任务独立上传，不会超时
```

---

## ⚙️ 高级配置

### 调整批量大小限制

默认支持 10000 个任务，如需调整：

```bash
export MAX_BATCH_SIZE=5000  # 改为 5000 个任务
```

### 查看处理进度

```bash
# 查看实时日志
tail -f /path/to/ml_backend.log

# 过滤上传相关日志
tail -f /path/to/ml_backend.log | grep "上传"

# 统计已上传的任务数量
grep "已实时上传" /path/to/ml_backend.log | wc -l
```

---

## 🐛 常见问题

### Q1: 浏览器显示超时，但任务还在处理？
**A:** 这是正常的。浏览器的 HTTP 请求有超时限制（通常 60-120 秒），但后端会继续处理。你可以：
- 查看服务器日志确认处理进度
- 等待处理完成后刷新页面查看结果

### Q2: 如何确认任务是否上传成功？
**A:** 查看服务器日志：
```bash
grep "✅ 任务.*已实时上传" /path/to/ml_backend.log
```

### Q3: 部分任务上传失败怎么办？
**A:** 检查以下几点：
1. Label Studio URL 是否正确
2. API Token 是否有效
3. Label Studio 服务是否正常运行
4. 网络连接是否正常

验证命令：
```bash
# 测试 API 连接
curl -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
     $LABEL_STUDIO_URL/api/projects/
```

### Q4: 想要取消正在处理的任务？
**A:** 直接停止 ML Backend 服务（Ctrl+C），已上传的任务结果会保留。

---

## 📈 性能指标

假设每个任务处理时间为 2-5 秒：

| 任务数量 | 预计处理时间 | 是否超时 |
|---------|-------------|---------|
| 10 个   | 20-50 秒    | ✅ 不超时 |
| 100 个  | 3-8 分钟    | ✅ 不超时 |
| 1000 个 | 30-80 分钟  | ✅ 不超时 |
| 1566 个 | 50-130 分钟 | ✅ 不超时 |

**说明：** 实时上传模式下，每个任务独立上传，不存在整体超时问题。

---

## 🔧 故障排查清单

如果遇到问题，请按以下步骤检查：

### ✅ 检查 1：环境变量是否设置
```bash
echo "Label Studio URL: $LABEL_STUDIO_URL"
echo "API Token 前10位: ${LABEL_STUDIO_API_KEY:0:10}..."
```

### ✅ 检查 2：Label Studio 连接是否正常
```bash
curl -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
     $LABEL_STUDIO_URL/api/projects/
# 应该返回项目列表 JSON
```

### ✅ 检查 3：ML Backend 是否正常运行
```bash
curl http://localhost:9090/health
# 应该返回 {"status": "UP"} 或类似信息
```

### ✅ 检查 4：查看详细日志
```bash
# 查看最近的错误
tail -100 /path/to/ml_backend.log | grep "ERROR"

# 查看上传统计
grep "上传" /path/to/ml_backend.log | tail -20
```

---

## 💡 最佳实践

### ✅ 推荐做法
1. 先用少量任务（3-5 个）测试，确保配置正确
2. 再用中等批量（20-50 个）验证稳定性
3. 最后处理全部任务

### ⚠️ 注意事项
1. 处理大批量任务时，不要关闭 ML Backend 服务
2. 确保服务器有足够的磁盘空间存储临时文件
3. 建议在低峰期处理大批量任务

### 📊 监控建议
```bash
# 创建一个简单的监控脚本
watch -n 5 'grep "已实时上传" /path/to/ml_backend.log | wc -l'
```

---

## 🎯 快速测试

运行以下命令快速测试配置：

```bash
# 1. 设置环境变量（示例）
export LABEL_STUDIO_URL=http://localhost:8080
export LABEL_STUDIO_API_KEY=your_token_here

# 2. 测试 API 连接
curl -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
     $LABEL_STUDIO_URL/api/projects/

# 3. 启动 ML Backend
python app.py

# 4. 在 Label Studio 中选择 3 个任务测试
```

---

## 📞 技术支持

如遇到问题，请提供以下信息：
1. 任务数量
2. 错误信息（如有）
3. 服务器日志（最近 50 行）
4. Label Studio 版本

```bash
# 导出日志
tail -50 /path/to/ml_backend.log > debug.log
```

---

## 🔄 更新日志

- **2025-12-02**: 改为实时上传模式，移除批量模式选项
- 默认支持 10000 个任务的批量处理
- 优化日志输出，便于监控进度









