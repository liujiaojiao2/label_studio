# 🚀 快速开始指南

本 ML Backend 已配置为**实时上传模式**，可以处理大批量任务而不会超时。

---

## 📋 三步启动

### 步骤 1：配置环境变量

```bash
# 设置 Label Studio 地址
export LABEL_STUDIO_URL=http://localhost:8080

# 设置 API Token（在 Label Studio → 头像 → Account & Settings → Access Token）
export LABEL_STUDIO_API_KEY=你的API令牌
```

### 步骤 2：测试连接（可选但推荐）

```bash
cd "/home/star/jiaojiao/Label Studio/wall_defect_stack/ml_backend"
./test_connection.sh
```

如果显示 ✅ 连接成功，则配置正确。

### 步骤 3：启动 ML Backend

```bash
./start_ml_backend.sh
```

或者直接运行：
```bash
python app.py
```

---

## 🎯 使用方法

### 在 Label Studio 中获取预测：

1. 打开 Label Studio 项目
2. 选择要预测的任务
   - 可以选择少量任务（3-5 个）测试
   - 也可以全选所有任务（例如 1566 个）
3. 点击 **Actions → Retrieve Predictions**
4. 等待处理完成

**重要提示：**
- ⚠️ 浏览器可能在 60-120 秒后显示超时
- ✅ 这是正常的！后端仍在处理
- ✅ 每处理完一个任务会立即上传到 Label Studio
- 💡 处理完成后**刷新页面**查看所有预测结果

---

## 📊 处理进度监控

### 方法 1：查看日志

```bash
# 实时查看上传进度
tail -f ml_backend.log | grep "上传"

# 统计已上传的任务数量
grep "已实时上传" ml_backend.log | wc -l
```

### 方法 2：在 Label Studio 中查看

定期刷新页面，查看已有多少任务显示了预测结果。

---

## ⏱️ 预计处理时间

假设每个任务处理时间为 2-5 秒：

| 任务数量 | 预计时间 |
|---------|---------|
| 10 个   | 20-50 秒 |
| 50 个   | 2-4 分钟 |
| 100 个  | 3-8 分钟 |
| 500 个  | 15-40 分钟 |
| 1566 个 | 50-130 分钟 |

---

## 🐛 常见问题

### Q: 浏览器显示超时怎么办？
**A:** 不用担心，这是正常的。后端仍在处理任务，刷新页面即可看到已完成的预测结果。

### Q: 如何确认任务是否在处理？
**A:** 查看服务器日志：
```bash
tail -f ml_backend.log
```

### Q: 可以中途取消吗？
**A:** 可以。按 `Ctrl+C` 停止服务，已上传的任务结果会保留。

### Q: 想重新预测某些任务怎么办？
**A:** 在 Label Studio 中删除对应任务的 prediction，然后重新点击 "Retrieve Predictions"。

---

## 💡 最佳实践

### ✅ 推荐流程

1. **小规模测试**：先选 3-5 个任务测试
   ```
   目的：验证配置正确，模型工作正常
   ```

2. **中等规模验证**：选 20-50 个任务
   ```
   目的：验证稳定性，观察处理速度
   ```

3. **大批量处理**：全选所有任务
   ```
   目的：批量预标注
   ```

### ⚠️ 注意事项

- 处理大批量任务时，保持服务器运行，不要关闭
- 确保服务器有足够的磁盘空间
- 建议在低峰期处理大批量任务

---

## 🔧 环境变量说明

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `LABEL_STUDIO_URL` | Label Studio 地址 | 无 | ✅ 是 |
| `LABEL_STUDIO_API_KEY` | API Token | 无 | ✅ 是 |
| `MAX_BATCH_SIZE` | 最大批量大小 | 10000 | ❌ 否 |
| `VISION_PROVIDER` | 视觉模型提供商 | doubao | ❌ 否 |
| `VISION_MODEL` | 视觉模型名称 | doubao-1-5-vision-pro-32k-250115 | ❌ 否 |

---

## 📞 故障排查

### 1. 测试 Label Studio 连接

```bash
./test_connection.sh
```

### 2. 查看详细日志

```bash
tail -100 ml_backend.log
```

### 3. 验证环境变量

```bash
echo "URL: $LABEL_STUDIO_URL"
echo "Token: ${LABEL_STUDIO_API_KEY:0:10}..."
```

### 4. 手动测试 API

```bash
curl -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
     $LABEL_STUDIO_URL/api/projects/
```

---

## 🎉 完整示例

```bash
# 1. 进入目录
cd "/home/star/jiaojiao/Label Studio/wall_defect_stack/ml_backend"

# 2. 设置环境变量
export LABEL_STUDIO_URL=http://localhost:8080
export LABEL_STUDIO_API_KEY=abc123xyz789

# 3. 测试连接（可选）
./test_connection.sh

# 4. 启动服务
./start_ml_backend.sh

# 5. 在 Label Studio 中使用
#    - 选择任务
#    - 点击 "Actions → Retrieve Predictions"
#    - 等待处理完成
#    - 刷新页面查看结果
```

---

## 📚 更多信息

详细说明请查看：`README_REALTIME.md`

祝使用愉快！🎉









