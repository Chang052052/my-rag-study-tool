import streamlit as st
import fitz  # 这是 PyMuPDF 库
from PIL import Image
import io

# ==========================================
# 1. 页面配置 (开启宽屏模式)
# ==========================================
st.set_page_config(layout="wide", page_title="Scholar Flow Visual")

# CSS 美化
st.markdown("""
<style>
    .result-box {
        padding: 15px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        margin-bottom: 10px;
        background-color: #f9fafb;
        transition: 0.3s;
    }
    .result-box:hover {
        border-color: #3b82f6;
        background-color: #eff6ff;
    }
    .highlight {
        background-color: #fef9c3;
        font-weight: bold;
        padding: 0 2px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑 (使用 PyMuPDF)
# ==========================================

@st.cache_resource
def load_pdf(file):
    """加载 PDF 文件到内存"""
    return fitz.open(stream=file.read(), filetype="pdf")

def search_in_pdf(doc, query):
    """在 PDF 中搜索关键词"""
    results = []
    query_lower = query.lower()
    keywords = query_lower.split()
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        text_lower = text.lower()
        
        # 简单的评分机制
        score = 0
        for k in keywords:
            if k in text_lower:
                score += 1
        
        if score > 0:
            # 截取一段文字作为预览
            idx = text_lower.find(keywords[0])
            start = max(0, idx - 100)
            end = min(len(text), idx + 200)
            snippet = text[start:end].replace("\n", " ")
            
            results.append({
                "page": page_num,
                "score": score,
                "snippet": "..." + snippet + "..."
            })
            
    # 按相关度排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:10]

# ==========================================
# 3. 界面布局
# ==========================================

st.title("🎓 Scholar Flow Visual")
st.caption("左侧搜索关键词，点击结果 -> 右侧显示【PDF原页】（完美数学公式）")

# 初始化 session state 用于存储当前查看的页面
if 'current_page_img' not in st.session_state:
    st.session_state.current_page_img = None
if 'current_doc_name' not in st.session_state:
    st.session_state.current_doc_name = ""

# --- 侧边栏：上传 ---
with st.sidebar:
    st.header("📂 上传文件")
    uploaded_file = st.file_uploader("选择 PDF", type=["pdf"])
    
    doc = None
    if uploaded_file:
        doc = load_pdf(uploaded_file)
        st.success(f"已加载: {uploaded_file.name} ({len(doc)} 页)")

# --- 主界面：双栏布局 ---
col_search, col_view = st.columns([1, 1.2]) # 左窄右宽

with col_search:
    st.subheader("🔍 搜索")
    query = st.text_input("输入关键词 (如: holomorphic definition)", placeholder="回车搜索...")
    
    if doc and query:
        results = search_in_pdf(doc, query)
        
        if not results:
            st.warning("未找到匹配内容")
        else:
            st.write(f"找到 {len(results)} 个结果：")
            
            # 遍历显示结果
            for i, res in enumerate(results):
                # 使用 Streamlit 原生容器做卡片
                with st.container():
                    st.markdown(f"**📄 第 {res['page'] + 1} 页**")
                    st.caption(res['snippet'])
                    
                    # 关键：点击按钮，更新右侧的图片
                    if st.button(f"查看原图 (结果 {i+1})", key=f"btn_{i}"):
                        # 1. 获取该页
                        page = doc[res['page']]
                        # 2. 渲染成高清图片 (zoom=2 表示2倍清晰度)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        # 3. 转换格式供显示
                        img_data = pix.tobytes("png")
                        st.session_state.current_page_img = img_data
                        st.session_state.current_doc_name = f"第 {res['page'] + 1} 页"
                    
                    st.markdown("---")

with col_view:
    st.subheader("📄 阅读视图")
    
    if st.session_state.current_page_img:
        st.info(f"正在查看：{st.session_state.current_doc_name}")
        st.image(st.session_state.current_page_img, use_column_width=True)
    else:
        st.markdown(
            """
            <div style="height: 400px; border: 2px dashed #ccc; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #888;">
                👈 请在左侧点击“查看原图”按钮
            </div>
            """, 
            unsafe_allow_html=True
        )
