#!/bin/bash
# ==============================================================================
# AES-INTEL 自动化管线 - 综合测试与质量核对脚本
# ==============================================================================

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR" || exit 1

REPORT_FILE="TEST_REPORT.md"
DATE_STR=$(date "+%Y-%m-%d %H:%M:%S")

echo "=================================================="
echo "🧪 启动 AES-INTEL 自动化管线系统性质量测试..."
echo "=================================================="

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ 虚拟环境 venv/bin/activate 未找到！"
    exit 1
fi

# 初始化状态变量
PYTEST_STATUS="PASS"
PATH_CHECK_STATUS="PASS"
SYNTAX_STATUS="PASS"
FAILED_LOG=""

# 1. 运行 Pytest 单元测试
echo "1. 运行 pytest 单元测试..."
PYTEST_OUTPUT=$(pytest 2>&1)
PYTEST_EXIT_CODE=$?

if [ $PYTEST_EXIT_CODE -ne 0 ]; then
    PYTEST_STATUS="FAIL"
    FAILED_LOG="${FAILED_LOG}\n- **pytest 单元测试失败**，部分测试未通过。"
fi

# 解析测试通过/失败的数量
TEST_SUMMARY=$(echo "$PYTEST_OUTPUT" | grep -E "passed|failed" | tail -n 1)

# 2. 检查项目根目录下是否有泄漏的 XML 文件 (杜绝低级物理路径配置错误)
echo "2. 检查项目根目录路径安全性..."
LEAKED_XML=$(ls "$PROJECT_DIR"/*.xml 2>/dev/null)
if [ -n "$LEAKED_XML" ]; then
    PATH_CHECK_STATUS="FAIL"
    FAILED_LOG="${FAILED_LOG}\n- **检测到泄露至项目根目录的 XML 文件**:\n$(echo "$LEAKED_XML" | sed 's/^/  - /')"
fi

# 3. 语法分析与静态编译检查
echo "3. 检查代码静态语法..."
SYNTAX_ERRORS=""
for py_file in aes-feeds/*.py; do
    if ! python3 -m py_compile "$py_file" 2>/dev/null; then
        SYNTAX_STATUS="FAIL"
        SYNTAX_ERRORS="${SYNTAX_ERRORS}\n  - 编译失败: $py_file"
    fi
done

if [ "$SYNTAX_STATUS" = "FAIL" ]; then
    FAILED_LOG="${FAILED_LOG}\n- **静态语法检查失败**:${SYNTAX_ERRORS}"
fi

# 4. 生成测试报告 (TEST_REPORT.md)
cat <<EOF > "$REPORT_FILE"
# AES-INTEL 项目集成与质量测试报告

- **测试时间**: $DATE_STR
- **测试环境**: $OSTYPE / Python \$(python3 -V 2>&1)

## 📊 测试结论

$( [ -z "$FAILED_LOG" ] && echo "🟢 **全部检查通过！代码状态健康。**" || echo "🔴 **检测到问题，需要立即修复：**${FAILED_LOG}" )

---

## 🔍 详细检查项目

| 检查项 | 状态 | 说明 |
| :--- | :---: | :--- |
| **pytest 单元测试** | $( [ "$PYTEST_STATUS" = "PASS" ] && echo "✅ PASS" || echo "❌ FAIL" ) | $TEST_SUMMARY |
| **文件输出路径安全性** | $( [ "$PATH_CHECK_STATUS" = "PASS" ] && echo "✅ PASS" || echo "❌ FAIL" ) | 检查是否有 XML 泄露到项目根目录 |
| **Python 代码静态编译** | $( [ "$SYNTAX_STATUS" = "PASS" ] && echo "✅ PASS" || echo "❌ FAIL" ) | 检查 \`aes-feeds\` 下所有脚本的语法正确性 |

---

## 📝 单元测试原始输出摘要

\`\`\`text
\$(echo "$PYTEST_OUTPUT" | tail -n 20)
\`\`\`
EOF

echo "=================================================="
if [ -z "$FAILED_LOG" ]; then
    echo "🟢 【测试成功】全部系统性质量核对已通过！"
    echo "报告已写入: $REPORT_FILE"
    echo "测试结果: $TEST_SUMMARY"
else
    echo "🔴 【测试失败】检测到系统性质量问题！"
    echo "报告已写入: $REPORT_FILE"
    echo -e "$FAILED_LOG"
fi
echo "=================================================="

# 返回正确退出码
if [ "$PYTEST_STATUS" = "PASS" ] && [ "$PATH_CHECK_STATUS" = "PASS" ] && [ "$SYNTAX_STATUS" = "PASS" ]; then
    exit 0
else
    exit 1
fi
