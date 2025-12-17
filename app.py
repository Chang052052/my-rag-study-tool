import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re  # 引入正则库，用于高亮替换

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="Scholar Flow Highlight")

st.markdown("""
<style>
    .result-box {
        padding: 18px;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        margin-bottom: 15px;
        background-color: #ffffff;
        transition: 0.2s;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    .result-box:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
    }
    .file-badge {
        background-color: #eff6ff;
        color: #1d4ed8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        border: 1px solid #dbeafe;
    }
    .score-badge {
        background-color: #f0fdf4;
        color: #15803d;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        float: right;
    }
    /* 核心：高亮样式 */
    .highlight {
        background-color: #fef08a; /* 荧光黄 */
        color: #000;
        padding: 0 2px;
        border-radius: 3px;
        font-weight: bold;
        border-bottom: 2px solid #facc15;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 辅助函数
# ==========================================

def convert_image_to_pdf_bytes(image_file):
    try:
        image = Image.open(image_file)
        if image.mode != 'RGB': image = image.convert('RGB')
        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format='PDF')
        return pdf_bytes.getvalue()
    except: return None

def highlight_text(text, query):
    """
    使用正则表达式，不区分大小写地高亮关键词
    """
    if not query: return text
    
    # 1. 拆分关键词，过滤掉太短的词
    keywords = [re.escape(k) for k in query.split() if len(k) > 0]
    if not keywords: return text
    
    # 2. 构建正则匹配模式 (word1|word2|word3)
    pattern = re.compile(r'(' + '|'.join(keywords) + r')', re.IGNORECASE)
    
    # 3. 替换为带样式的 HTML
    # lambda m: 保持原文的大小写，只加标签
    highlighted = pattern.sub(lambda m: f'<span class="highlight">{m.group(1)}</span>', text)
    
    return highlighted

# ==========================================
# 3. 核心逻辑
# ==========================================

def process_files_live(uploaded_files):
    docs_map = {}
    total_pages = 0
    progress_bar = st.sidebar.progress(0)
    
    for i, file in enumerate(uploaded_files):
        try:
            file.seek(0)
            file_bytes = None
            if file.type == "application/pdf":
                file_bytes = file.read()
            elif file.type in ["image/png", "image/jpeg", "image/jpg"]:
                file_bytes = convert_image_to_pdf_bytes(file)
            
            if file_bytes:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                docs_map[file.name] = {"doc": doc}
                total_pages += len(doc)
        except: pass
        progress_bar.progress((i + 1) / len(uploaded_files))
        
    progress_bar.empty()
    return docs_map, total_pages

def search_logic(docs_map, query):
    results = []
    keywords = query.lower().split()
    if not keywords: return []
    
    for filename, data in docs_map.items():
        doc = data["doc"]
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if not text.strip(): continue
            
            text_lower = text.lower()
            
            # === 评分逻辑 ===
            score = 0
            for k in keywords:
                # 统计关键词出现的总次数作为分数
                count = text_lower.count(k)
                score += count * 10  # 基础分：出现一次加10分
            
            # 如果包含完整短语，额外加分 (例如搜 "Cauchy Theorem"，如果这两个词挨着，加分)
            if query.lower() in text_lower:
                score += 50 

            if score > 0:
                # 智能截取：找到第一个关键词的位置
                first_idx = text_lower.find(keywords[0])
                start = max(0, first_idx - 120)
                end = min(len(text), first_idx + 250)
                snippet = text[start:end].replace("\n", " ")
                
                results.append({
                    "filename": filename,
                    "page": page_num,
                    "score": score,
                    "snippet": "..." + snippet + "...", # 原始文本，用于后续高亮处理
                    "full_text": text # 保留全文备用
                })
    
    # === 排序逻辑 ===
    # 按照分数从高到低排序 (Reverse=True)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:30]

# ==========================================
# 4. 界面布局
# ==========================================

st.title("🎓 Scholar Flow V14")
st.caption("✨ 新特性：智能荧光笔高亮 + 最佳结果置顶")

if 'preview_img' not in st.session_state:
    st.session_state.preview_img = None
    st.session_state.preview_info = ""

# --- 侧边栏 ---
with st.sidebar:
    st.header("📂 资料库")
    uploaded_files = st.file_uploader(
        "上传文件 (PDF/图片)", 
        type=["pdf", "png", "jpg", "jpeg"], 
        accept_multiple_files=True,
        key="uploader"
    )
    
    docs_map = {}
    if uploaded_files:
        with st.spinner("正在建立索引..."):
            docs_map, _ = process_files_live(uploaded_files)
        st.success(f"已索引 {len(docs_map)} 个文件")

# --- 主界面 ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🔍 搜索")
    with st.form(key='s_form'):
        query = st.text_input("关键词", placeholder="输入后回车...")
        btn = st.form_submit_button("🔎 搜索")
    
    if (btn or query) and docs_map:
        results = search_logic(docs_map, query)
        
        if not results:
            st.warning("未找到结果")
        else:
            st.write(f"找到 {len(results)} 条最相关的结果：")
            
            for i, res in enumerate(results):
                # 1. 对摘录进行高亮处理
                highlighted_snippet = highlight_text(res['snippet'], query)
                
                with st.container():
                    # 结果卡片 HTML
                    st.markdown(f"""
                    <div class="result-box">
                        <div style="margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                            <span>
                                <span class="file-badge">📄 {res['filename']}</span>
                                <span style="font-size:0.85rem; color:#64748b; margin-left:5px;">第 {res['page'] + 1} 页</span>
                            </span>
                            <span class="score-badge">相关度: {res['score']}</span>
                        </div>
                        <div style="font-size:0.95rem; line-height:1.6; color:#334155;">
                            {highlighted_snippet}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 按钮单独放，方便交互
                    if st.button(f"👉 查看第 {res['page']+1} 页原图", key=f"v_{i}"):
                        doc = docs_map[res['filename']]["doc"]
                        page = doc[res['page']]
                        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                        st.session_state.preview_img = pix.tobytes("png")
                        st.session_state.preview_info = f"{res['filename']} - P{res['page']+1}"
                    
                    # 稍微加点间距
                    st.write("")

with col2:
    st.subheader("📄 高清原文")
    if st.session_state.preview_img:
        st.info(f"正在查看: {st.session_state.preview_info}")
        st.image(st.session_state.preview_img, use_column_width=True)
    else:
        st.markdown(
            """
            <div style="height: 500px; border: 2px dashed #cbd5e1; border-radius: 12px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; color: #94a3b8; background-color: #f8fafc;">
                <h3 style="margin:0">👈 左侧点击查看</h3>
                <p>点击“查看原图”按钮以显示详情</p>
            </div>
            """, unsafe_allow_html=True
        )
