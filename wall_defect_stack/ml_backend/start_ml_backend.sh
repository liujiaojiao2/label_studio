#!/bin/bash
# ML Backend 实时上传模式启动脚本

echo "=========================================="
echo "🚀 ML Backend - 实时上传模式"
echo "=========================================="
echo ""

# 检查 Label Studio URL
if [ -z "$LABEL_STUDIO_URL" ]; then
    echo "⚠️  未设置 LABEL_STUDIO_URL 环境变量"
    echo ""
    echo "请输入 Label Studio 地址（例如：http://localhost:8080）："
    read -r ls_url
    
    if [ -z "$ls_url" ]; then
        echo "❌ 必须提供 Label Studio 地址"
        exit 1
    fi
    
    export LABEL_STUDIO_URL="$ls_url"
    echo "✅ LABEL_STUDIO_URL: $LABEL_STUDIO_URL"
else
    echo "✅ LABEL_STUDIO_URL: $LABEL_STUDIO_URL"
fi

echo ""

# 检查 API Key
if [ -z "$LABEL_STUDIO_API_KEY" ]; then
    echo "⚠️  未设置 LABEL_STUDIO_API_KEY 环境变量"
    echo ""
    echo "请输入 Label Studio API Token："
    echo "（获取方法：Label Studio → 右上角头像 → Account & Settings → Access Token）"
    read -r -s api_key
    echo ""
    
    if [ -z "$api_key" ]; then
        echo "❌ 必须提供 API Token"
        exit 1
    fi
    
    export LABEL_STUDIO_API_KEY="$api_key"
    echo "✅ API Token 已设置"
else
    echo "✅ API Token 已设置"
fi

echo ""
echo "=========================================="
echo "🔍 测试 Label Studio 连接..."
echo "=========================================="

# 测试连接
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Token $LABEL_STUDIO_API_KEY" \
    "$LABEL_STUDIO_URL/api/projects/" 2>/dev/null)

if [ "$response" = "200" ]; then
    echo "✅ Label Studio 连接成功！"
else
    echo "⚠️  Label Studio 连接失败 (HTTP $response)"
    echo "请检查："
    echo "  1. Label Studio URL 是否正确"
    echo "  2. API Token 是否有效"
    echo "  3. Label Studio 服务是否正常运行"
    echo ""
    echo "是否仍要继续启动？(y/n)"
    read -r continue
    if [ "$continue" != "y" ]; then
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "📊 当前配置"
echo "=========================================="
echo "Label Studio URL: $LABEL_STUDIO_URL"
echo "API Token: ${LABEL_STUDIO_API_KEY:0:10}..."
echo "预测模式: 实时上传（每处理完一个任务立即上传）"
echo "批量限制: ${MAX_BATCH_SIZE:-10000} 个任务"
echo ""
echo "=========================================="
echo "🎯 使用说明"
echo "=========================================="
echo "1. 在 Label Studio 中选择要预测的任务（可全选）"
echo "2. 点击 'Actions → Retrieve Predictions'"
echo "3. 等待处理完成（可能需要较长时间）"
echo "4. 如果浏览器超时，不用担心，刷新页面即可看到结果"
echo ""
echo "查看实时进度："
echo "  tail -f ml_backend.log | grep '上传'"
echo ""
echo "=========================================="
echo "🚀 正在启动 ML Backend..."
echo "=========================================="
echo ""

# 启动服务
python app.py









