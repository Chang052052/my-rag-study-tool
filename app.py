import streamlit as st
import fitz  # PyMuPDF
from PIL import Image

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="Scholar Flow Visual Multi")

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
    .file-tag {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑 (多文件处理)
# ==========================================

def search_across_docs(docs_map, query):
    """
    在所有文档中搜索
    docs_map结构: {'文件名': fitz.Document对象}
    """
    results = []
    query_lower = query.lower()
    keywords = query_lower.split()
    
    # 遍历每一个文档
    for filename, doc in docs_map.items():
        for page_num, page in enumerate(doc):
            text = page.get_text()
            text_lower = text.lower()
            
            # 评分
            score = 0
            for k in keywords:
                if k in text_lower:
                    score += 1
            
            if score > 0:
                # 截取预览
                idx = text_lower.find(keywords[0])
                start = max(0, idx - 100)
                end = min(len(text), idx + 200)
                snippet = text[start:end].replace("\n", " ")
                
                results.append({
                    "filename": filename,
                    "page": page_num,
                    "score": score,
                    "snippet": "..." + snippet + "..."
                })
            
    # 全局排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:15] # 返回前15个结果

# ==========================================
# 3. 界面布局
# ==========================================

st.title("🎓 Scholar Flow Visual Pro")
st.caption("支持【多文件】检索 + 右侧【高清原图】查看")

# 初始化状态
if 'current_view_img' not in st.session_state:
    st.session_state.current_view_img = None
if 'current_view_info' not in st.session_state:
    st.session_state.current_view_info = "请在左侧点击查看"

# --- 侧边栏：多文件上传 ---
with st.sidebar:
    st.header("📂 资料库")
    # accept_multiple_files=True 开启多选
    uploaded_files = st.file_uploader("上传 PDF (支持多选)", type=["pdf"], accept_multiple_files=True)
    
    docs_map = {} # 用于存储文件名到文档对象的映射
    
    if uploaded_files:
        # 这里为了演示简单，每次刷新都重新读取流
        # 在生产环境中通常会用 hash 缓存，但在本地运行这样最稳
        for file in uploaded_files:
            try:
                # 读取文件流并创建 fitz 文档对象
                file_bytes = file.read()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                docs_map[file.name] = doc
            except Exception as e:
                st.error(f"{file.name} 读取失败")
                
        st.success(f"已加载 {len(docs_map)} 个文档")
        with st.expander("已加载列表"):
            for name in docs_map.keys():
                st.text(f"📄 {name}")

# --- 主界面：双栏 ---
col_search, col_view = st.columns([1, 1.2])

with col_search:
    st.subheader("🔍 跨文档搜索")
    query = st.text_input("输入关键词...", placeholder="例如: Cauchy theorem")
    
    if docs_map and query:
        with st.spinner("正在扫描所有文档..."):
            results = search_across_docs(docs_map, query)
        
        if not results:
            st.warning("未找到匹配内容")
        else:
            st.write(f"共找到 {len(results)} 条相关线索：")
            
            for i, res in enumerate(results):
                with st.container():
                    # 显示文件名标签
                    st.markdown(f"""
                    <div style="margin-bottom:5px;">
                        <span class="file-tag">📄 {res['filename']}</span>
                        <b>第 {res['page'] + 1} 页</b>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.caption(res['snippet'])
                    
                    # 按钮：点击查看
                    if st.button(f"👉 查看原图", key=f"btn_{i}"):
                        # 1. 从 map 中取出对应的 doc 对象
                        target_doc = docs_map[res['filename']]
                        # 2. 取出对应的页
                        page = target_doc[res['page']]
                        # 3. 渲染高清图
                        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) # 2.5倍清晰度
                        st.session_state.current_view_img = pix.tobytes("png")
                        st.session_state.current_view_info = f"{res['filename']} - 第 {res['page']+1} 页"
                    
                    st.markdown("---")

with col_view:
    st.subheader("📄 阅读视图")
    
    if st.session_state.current_view_img:
        st.info(f"正在查看：{st.session_state.current_view_info}")
        st.image(st.session_state.current_view_img, use_column_width=True)
    else:
        st.markdown(
            """
            <div style="height: 500px; border: 2px dashed #e5e7eb; border-radius: 10px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af;">
                <h3 style="margin:0;">👈 等待选择</h3>
                <p>请在左侧搜索并点击“查看原图”</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
