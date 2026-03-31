#!/bin/bash
# Label Studio 1.20.0+ Token 认证问题修复脚本

echo "=========================================="
echo "🔧 Label Studio Token 认证修复工具"
echo "=========================================="
echo ""
echo "检测到 Label Studio 1.20.0+ 版本的认证问题："
echo "  - 旧版 token 认证已被禁用"
echo "  - 需要使用新的 API Token"
echo ""

# 检查当前 token
if [ -n "$LABEL_STUDIO_API_KEY" ]; then
    echo "当前 Token: ${LABEL_STUDIO_API_KEY:0:20}..."
    echo ""
fi

echo "=========================================="
echo "📝 解决方案"
echo "=========================================="
echo ""
echo "方案 1: 在 Label Studio 中重新生成 Token（推荐）"
echo "----------------------------------------"
echo "1. 登录 Label Studio"
echo "2. 点击右上角头像 → Account & Settings"
echo "3. 找到 'Access Token' 部分"
echo "4. 点击 'Create New Token' 或 'Regenerate'"
echo "5. 给 Token 取个名字（例如：ML Backend）"
echo "6. 复制新生成的 Token"
echo ""

echo "方案 2: 使用 API Key（如果组织已禁用 Token）"
echo "----------------------------------------"
echo "1. 登录 Label Studio"
echo "2. Settings → Organization → API Keys"
echo "3. 创建新的 API Key"
echo "4. 复制 API Key"
echo ""

echo "=========================================="
echo "🔑 输入新的 Token/API Key"
echo "=========================================="
echo ""
echo "请输入新的 Label Studio Token 或 API Key："
read -r -s new_token
echo ""

if [ -z "$new_token" ]; then
    echo "❌ 未输入 Token，退出"
    exit 1
fi

# 设置新 token
export LABEL_STUDIO_API_KEY="$new_token"

echo "✅ 新 Token 已设置"
echo ""

# 测试连接
echo "=========================================="
echo "🧪 测试新 Token..."
echo "=========================================="
echo ""

if [ -z "$LABEL_STUDIO_URL" ]; then
    echo "请输入 Label Studio URL（例如：http://localhost:8080）："
    read -r ls_url
    export LABEL_STUDIO_URL="$ls_url"
fi

# 测试 API 连接
echo "正在测试连接到: $LABEL_STUDIO_URL"
response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Token $new_token" \
    "$LABEL_STUDIO_URL/api/projects/" 2>/dev/null)

http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

echo ""
if [ "$http_code" = "200" ]; then
    echo "✅ 认证成功！新 Token 有效"
    echo ""
    echo "=========================================="
    echo "💾 保存配置"
    echo "=========================================="
    echo ""
    echo "是否将新 Token 保存到 ~/.bashrc？(y/n)"
    read -r save_choice
    
    if [ "$save_choice" = "y" ]; then
        # 检查是否已存在配置
        if grep -q "LABEL_STUDIO_API_KEY" ~/.bashrc; then
            echo "⚠️  ~/.bashrc 中已存在 LABEL_STUDIO_API_KEY"
            echo "请手动编辑 ~/.bashrc 更新 Token"
        else
            echo "export LABEL_STUDIO_URL=\"$LABEL_STUDIO_URL\"" >> ~/.bashrc
            echo "export LABEL_STUDIO_API_KEY=\"$new_token\"" >> ~/.bashrc
            echo "✅ 配置已保存到 ~/.bashrc"
            echo "运行以下命令使其生效："
            echo "  source ~/.bashrc"
        fi
    fi
    
    echo ""
    echo "=========================================="
    echo "✅ 修复完成！"
    echo "=========================================="
    echo ""
    echo "现在可以启动 ML Backend："
    echo "  ./start_ml_backend.sh"
    echo ""
    echo "或者在当前终端直接运行："
    echo "  python app.py"
    echo ""
    
elif [ "$http_code" = "401" ]; then
    echo "❌ 认证仍然失败 (HTTP 401)"
    echo ""
    echo "错误响应："
    echo "$body"
    echo ""
    echo "=========================================="
    echo "📞 进一步排查"
    echo "=========================================="
    echo ""
    echo "可能的原因："
    echo "1. Token 格式不正确"
    echo "2. Token 权限不足"
    echo "3. 组织已完全禁用 Token 认证，需要使用 API Key"
    echo "4. Label Studio 版本问题"
    echo ""
    echo "建议："
    echo "1. 确认使用的是 Label Studio 1.20.0+ 的新版 Token"
    echo "2. 尝试创建新的 API Key 而不是 Token"
    echo "3. 检查 Label Studio 的组织设置"
    echo "4. 联系 Label Studio 管理员"
    echo ""
    
else
    echo "❌ 连接失败 (HTTP $http_code)"
    echo ""
    echo "错误响应："
    echo "$body"
    echo ""
    echo "请检查："
    echo "1. Label Studio URL 是否正确"
    echo "2. Label Studio 服务是否正常运行"
    echo "3. 网络连接是否正常"
    echo ""
fi









