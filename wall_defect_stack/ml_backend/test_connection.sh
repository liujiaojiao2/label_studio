#!/bin/bash
# 测试 Label Studio 连接

echo "=========================================="
echo "🔍 测试 Label Studio 连接"
echo "=========================================="
echo ""

# 检查环境变量
if [ -z "$LABEL_STUDIO_URL" ]; then
    echo "❌ 未设置 LABEL_STUDIO_URL"
    echo "请运行: export LABEL_STUDIO_URL=http://your-url"
    exit 1
fi

if [ -z "$LABEL_STUDIO_API_KEY" ]; then
    echo "❌ 未设置 LABEL_STUDIO_API_KEY"
    echo "请运行: export LABEL_STUDIO_API_KEY=your_token"
    exit 1
fi

echo "✅ 环境变量已设置"
echo "   URL: $LABEL_STUDIO_URL"
echo "   Token: ${LABEL_STUDIO_API_KEY:0:10}..."
echo ""

# 测试连接
echo "正在测试连接..."
response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
    "$LABEL_STUDIO_URL/api/projects/")

http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

echo ""
if [ "$http_code" = "200" ]; then
    echo "✅ 连接成功！"
    echo ""
    echo "Label Studio 项目列表："
    echo "$body" | python3 -m json.tool 2>/dev/null | head -20
    echo ""
    echo "=========================================="
    echo "✅ 配置正确，可以启动 ML Backend"
    echo "=========================================="
    echo ""
    echo "运行以下命令启动："
    echo "  ./start_ml_backend.sh"
    echo ""
else
    echo "❌ 连接失败 (HTTP $http_code)"
    echo ""
    echo "响应内容："
    echo "$body"
    echo ""
    echo "请检查："
    echo "  1. Label Studio URL 是否正确"
    echo "  2. API Token 是否有效"
    echo "  3. Label Studio 服务是否正常运行"
    echo ""
    echo "=========================================="
    exit 1
fi









