# 🔐 Label Studio 认证问题解决方案

## 🚨 问题描述

错误信息：
```
❌ 认证失败 (401)
Authentication token no longer valid: legacy token authentication has been disabled for this organization
```

**原因：** 你的 Label Studio 组织已禁用了 **legacy token 认证**，需要使用新的认证方式。

---

## ✅ 解决方案（3 个选项）

### 🥇 方案 1：使用 API Key（推荐）

#### 步骤 1：创建 API Key

```
1. 登录 Label Studio（需要管理员权限）
2. 点击左侧 "Settings"（设置）
3. 选择 "Organization"（组织）
4. 找到 "API Keys" 或 "Access Tokens" 标签页
5. 点击 "Create API Key" 或 "Add Token"
6. 填写名称（例如：ML Backend）
7. 复制生成的 API Key
```

**API Key 可能的位置：**
- Settings → Organization → API Keys
- Organization → Access Tokens
- Settings → Security → API Keys

#### 步骤 2：使用新的 API Key

```bash
# 停止当前服务（Ctrl+C）

# 设置新的 API Key
export LABEL_STUDIO_API_KEY=你的新API_Key

# 重启服务
python app.py
```

#### 步骤 3：测试

```bash
# 测试 API Key 是否有效
curl -H "Authorization: Token YOUR_API_KEY" \
     http://your-labelstudio-url/api/projects/

# 应该返回项目列表（JSON）
```

---

### 🥈 方案 2：让管理员重新启用 Token 认证

如果你不是管理员，可以让管理员重新启用 legacy token 认证：

```
1. 登录 Label Studio（管理员账户）
2. Settings → Organization → Security
3. 找到 "Legacy Token Authentication" 相关设置
4. 启用该选项
5. 保存设置
```

然后你可以继续使用原来的 User Token。

---

### 🥉 方案 3：临时禁用实时上传（权宜之计）

如果暂时无法获取 API Key，可以禁用实时上传，改用批量返回模式：

```bash
# 禁用实时上传
export ENABLE_REALTIME_UPLOAD=false

# 重启服务
python app.py
```

**注意：** 批量返回模式有限制：
- ⚠️ 每次最多处理 20 个任务
- ⚠️ 处理时间不能超过 60-120 秒
- ⚠️ 需要手动分批处理大量任务

---

## 🔍 如何判断你需要哪种方案？

### 情况 1：你是管理员
→ 使用 **方案 1**（创建 API Key）

### 情况 2：你不是管理员
→ 联系管理员帮你创建 API Key（**方案 1**）
→ 或让管理员重新启用 token 认证（**方案 2**）

### 情况 3：暂时无法获取权限
→ 临时使用 **方案 3**（禁用实时上传）

---

## 📊 三种方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| API Key | ✅ 完美解决<br>✅ 支持大批量<br>✅ 实时上传 | ⚠️ 需要管理员权限 | ⭐⭐⭐⭐⭐ |
| 重新启用 Token | ✅ 可继续使用 User Token<br>✅ 支持大批量 | ⚠️ 需要管理员操作<br>⚠️ 不推荐（已废弃） | ⭐⭐⭐ |
| 禁用实时上传 | ✅ 立即可用<br>✅ 无需额外权限 | ❌ 只能处理 20 个任务<br>❌ 需要手动分批 | ⭐⭐ |

---

## 🛠️ 详细配置示例

### 示例 1：使用 API Key（方案 1）

```bash
# 完整配置
export LABEL_STUDIO_URL=http://localhost:8080
export LABEL_STUDIO_API_KEY=your_api_key_here
export ENABLE_REALTIME_UPLOAD=true  # 启用实时上传（默认）

# 启动服务
python app.py

# 在 Label Studio 中可以选择任意数量的任务进行预测
```

### 示例 2：禁用实时上传（方案 3）

```bash
# 完整配置
export LABEL_STUDIO_URL=http://localhost:8080
export LABEL_STUDIO_API_KEY=your_token_here
export ENABLE_REALTIME_UPLOAD=false  # 禁用实时上传
export MAX_BATCH_SIZE=20  # 每次最多 20 个任务

# 启动服务
python app.py

# 在 Label Studio 中每次只能选择 1-20 个任务
```

---

## 🐛 故障排查

### 1. 如何验证 API Key 是否有效？

```bash
curl -H "Authorization: Token YOUR_API_KEY" \
     $LABEL_STUDIO_URL/api/projects/
```

**成功响应：**
```json
[{"id":1,"title":"My Project",...}]
```

**失败响应：**
```json
{"detail":"Invalid token"}
```

### 2. 找不到 API Keys 选项？

可能的原因：
- 你不是管理员（需要管理员权限）
- Label Studio 版本太旧（需要 1.20.0+）
- 组织设置中未启用该功能

**解决办法：** 联系系统管理员

### 3. API Key 仍然失败？

检查以下几点：
```bash
# 1. 确认 URL 正确
echo $LABEL_STUDIO_URL

# 2. 确认 API Key 正确（无多余空格）
echo "$LABEL_STUDIO_API_KEY" | wc -c

# 3. 测试网络连接
curl $LABEL_STUDIO_URL/api/health

# 4. 查看详细错误日志
tail -100 ml_backend.log
```

---

## 💡 推荐配置（最佳实践）

### 生产环境配置

```bash
# ~/.bashrc 或 ~/.zshrc
export LABEL_STUDIO_URL=http://your-labelstudio-url
export LABEL_STUDIO_API_KEY=your_api_key_here
export ENABLE_REALTIME_UPLOAD=true
export MAX_BATCH_SIZE=10000

# 使配置生效
source ~/.bashrc
```

### 开发/测试环境配置

```bash
# 临时配置（当前终端有效）
export LABEL_STUDIO_URL=http://localhost:8080
export LABEL_STUDIO_API_KEY=test_api_key
export ENABLE_REALTIME_UPLOAD=false  # 测试时可以禁用
export MAX_BATCH_SIZE=10
```

---

## 📞 仍然无法解决？

请提供以下信息：

1. **Label Studio 版本：**
   ```bash
   # 在 Label Studio 底部查看版本号
   # 或访问：http://your-url/api/version
   ```

2. **你的角色：** 管理员 / 普通用户

3. **错误日志：**
   ```bash
   tail -100 ml_backend.log
   ```

4. **测试结果：**
   ```bash
   curl -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
        $LABEL_STUDIO_URL/api/projects/
   ```

---

## 🚀 快速操作指南

### 如果你是管理员

```bash
# 1. 在 Label Studio 中创建 API Key
# 2. 配置环境变量
export LABEL_STUDIO_API_KEY=新的API_Key

# 3. 重启服务
python app.py
```

### 如果你不是管理员

```bash
# 临时方案：禁用实时上传
export ENABLE_REALTIME_UPLOAD=false

# 重启服务
python app.py

# 在 Label Studio 中每次选择 ≤20 个任务
```

---

## ✅ 成功标志

配置成功后，你应该看到：

```
✅ 任务 1 已上传
✅ 任务 2 已上传
✅ 任务 3 已上传
...
```

而不是：

```
❌ 任务 1 认证失败 (401)
❌ 任务 2 认证失败 (401)
```

---

## 📚 相关文档

- Label Studio 官方文档：https://labelstud.io/guide/
- API 认证说明：https://labelstud.io/guide/api.html
- 组织设置：https://labelstud.io/guide/manage_users.html









