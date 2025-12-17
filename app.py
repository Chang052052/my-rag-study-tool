import streamlit as st
from pypdf import PdfReader
import re

# ==========================================
# 1. 界面配置
# ==========================================
st.set_page_config(
    page_title="Scholar Flow RAG Multi", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS: 优化卡片样式，增加文件名字段的显示
st.markdown("""
<style>
    .result-card {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
    }
    .meta-tag {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 10px;
        display: inline-block;
    }
    /* 强制渲染数学公式字体 */
    .katex { font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑 (支持多文件)
# ==========================================

@st.cache_data
def process_pdf(file):
    """读取单个 PDF 并提取文本"""
    pages_data = []
    try:
        reader = PdfReader(file)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                # 清洗空白字符
                clean_text = re.sub(r'\s+', ' ', text).strip()
                # 记录文件名、页码、文本
                pages_data.append({
                    "filename": file.name,
                    "page": i + 1, 
                    "text": clean_text
                })
    except Exception as e:
        st.error(f"解析 {file.name} 失败: {e}")
    return pages_data

def search_engine(query, all_pages_data):
    results = []
    keywords = [k.lower() for k in query.split() if len(k) > 1]
    
    if not keywords: return []

    for data in all_pages_data:
        text = data['text']
        text_lower = text.lower()
        
        # 评分机制
        score = 0
        for k in keywords:
            if k in text_lower:
                score += 1
        
        if score > 0:
            # 智能截取上下文
            first_idx = text_lower.find(keywords[0])
            start = max(0, first_idx - 150)
            end = min(len(text), first_idx + 350)
            
            snippet = text[start:end]
            if start > 0: snippet = "..." + snippet
            if end < len(text): snippet = snippet + "..."
            
            # 高亮处理 (Markdown 粗体)
            for k in keywords:
                pattern = re.compile(re.escape(k), re.IGNORECASE)
                snippet = pattern.sub(lambda m: f"**{m.group(0)}**", snippet)

            results.append({
                "filename": data['filename'],
                "page": data['page'],
                "score": score,
                "snippet": snippet
            })
            
    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:8] # 多文件时返回更多结果

# ==========================================
# 3. 界面布局
# ==========================================

with st.sidebar:
    st.title("📚 知识库 (Library)")
    
    # === 关键修改：accept_multiple_files=True ===
    uploaded_files = st.file_uploader(
        "上传 PDF (支持多选)", 
        type=['pdf'], 
        accept_multiple_files=True
    )
    
    knowledge_base = []
    
    if uploaded_files:
        with st.spinner(f"正在分析 {len(uploaded_files)} 个文件..."):
            for file in uploaded_files:
                # 循环处理每个文件，并将结果合并到 knowledge_base
                file_pages = process_pdf(file)
                knowledge_base.extend(file_pages)
                
        st.success(f"✅ 已加载 {len(uploaded_files)} 个文件\n共 {len(knowledge_base)} 页笔记")
        
        # 显示已加载的文件列表
        with st.expander("已加载文件列表"):
            for f in uploaded_files:
                st.text(f"• {f.name}")

st.title("🎓 Scholar Flow Multi")
st.caption("支持多文件检索的 AI 学习助手")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "你好！请一次性上传所有相关的 Lecture Notes 或考卷，我会跨文件为你寻找答案。"}]

# 显示历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "div class" in msg["content"]:
             st.markdown(msg["content"], unsafe_allow_html=True)
        else:
             st.write(msg["content"])

# 输入框
if query := st.chat_input("输入问题 (例如: definition of holomorphic)"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        if not knowledge_base:
            st.warning("⚠️ 请先在左侧上传至少一个 PDF 文件。")
        else:
            results = search_engine(query, knowledge_base)
            
            if results:
                for res in results:
                    # 显示文件名 + 页码
                    st.markdown(f"""
                    <div class="result-card">
                        <span class="meta-tag">📄 {res['filename']}</span>
                        <span class="meta-tag">第 {res['page']} 页</span>
                        <div style="color: #334155; line-height: 1.6; margin-top:8px;">
                    """, unsafe_allow_html=True)
                    
                    st.markdown(res['snippet'])
                    
                    st.markdown("</div></div>", unsafe_allow_html=True)
                    
                st.session_state.messages.append({"role": "assistant", "content": "✅ 搜索完成 (见上方卡片)"})
            else:
                st.error("在所有文件中均未找到相关内容。")
