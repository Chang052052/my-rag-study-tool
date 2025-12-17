import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="Scholar Flow Realtime")

st.markdown("""
<style>
    .result-box {
        padding: 15px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        margin-bottom: 12px;
        background-color: #fff;
        transition: 0.2s;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .result-box:hover {
        border-color: #3b82f6;
        background-color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .file-badge {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 8px;
        border: 1px solid #bae6fd;
    }
    .page-badge {
        background-color: #f1f5f9;
        color: #475569;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑 (移除缓存，确保实时性)
# ==========================================

def convert_image_to_pdf_bytes(image_file):
    """图片转 PDF 流"""
    try:
        image = Image.open(image_file)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format='PDF')
        return pdf_bytes.getvalue()
    except Exception:
        return None

def process_files_live(uploaded_files):
    """
    【关键修改】去掉了 @st.cache 装饰器
    每次运行都重新读取内存中的文件，确保由 file_uploader 传入的最新文件列表被处理
    """
    docs_map = {}
    total_pages = 0
    
    # 进度条
    progress_bar = st.sidebar.progress(0)
    total_files = len(uploaded_files)
    
    for i, file in enumerate(uploaded_files):
        try:
            file_bytes = None
            
            # 读取文件流
            file.seek(0) # 关键：重置指针，防止二次读取为空
            
            if file.type == "application/pdf":
                file_bytes = file.read()
            elif file.type in ["image/png", "image/jpeg", "image/jpg"]:
                file_bytes = convert_image_to_pdf_bytes(file)
            
            if file_bytes:
                # 建立文档对象
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                docs_map[file.name] = {"doc": doc}
                total_pages += len(doc)
                
        except Exception as e:
            st.sidebar.error(f"{file.name} 读取失败")
        
        # 更新进度
        progress_bar.progress((i + 1) / total_files)
        
    progress_bar.empty() # 处理完隐藏进度条
    return docs_map, total_pages

def search_logic(docs_map, query):
    results = []
    keywords = query.lower().split()
    
    for filename, data in docs_map.items():
        doc = data["doc"]
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if not text.strip(): continue # 跳过空页
            
            text_lower = text.lower()
            score = 0
            for k in keywords:
                if k in text_lower: score += 1
            
            if score > 0:
                # 截取片段
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
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:40] # 返回更多结果

# ==========================================
# 3. 界面逻辑
# ==========================================

st.title("🎓 Scholar Flow V13")
st.caption("实时索引版：上传新文件 -> 立即生效")

# 状态管理
if 'preview_img' not in st.session_state:
    st.session_state.preview_img = None
    st.session_state.preview_info = ""

# --- 侧边栏 ---
with st.sidebar:
    st.header("📂 资料库管理")
    
    # 关键：给 uploader 一个固定的 key
    uploaded_files = st.file_uploader(
        "第一步：上传/添加文件", 
        type=["pdf", "png", "jpg", "jpeg"], 
        accept_multiple_files=True,
        key="main_uploader"
    )
    
    docs_map = {}
    
    if uploaded_files:
        st.write("---")
        with st.spinner("正在解析新文件..."):
            # 实时处理，不缓存
            docs_map, total_pages = process_files_live(uploaded_files)
            
        st.success(f"✅ 当前索引：{len(docs_map)} 个文件 | {total_pages} 页")
        
        # 调试信息：显示当前到底有哪些文件
        with st.expander("查看已生效文件列表"):
            for name in docs_map.keys():
                st.text(f"• {name}")
    else:
        st.warning("请上传文件")

# --- 主界面 ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🔍 搜索")
    # 使用 form 来包裹输入框，这样按回车更灵敏
    with st.form(key='search_form'):
        query = st.text_input("第二步：输入关键词", placeholder="输入后按回车...")
        submit_button = st.form_submit_button(label='🔎 开始搜索')
    
    # 当按回车 或 点搜索按钮时触发
    if (submit_button or query) and docs_map:
        results = search_logic(docs_map, query)
        
        if not results:
            st.warning("未找到结果。请检查关键词或确认文件已在左侧列表中。")
        else:
            st.write(f"找到 {len(results)} 条相关内容：")
            
            for i, res in enumerate(results):
                with st.container():
                    # 结果卡片
                    st.markdown(f"""
                    <div style="margin-bottom: 5px;">
                        <span class="file-badge">📄 {res['filename']}</span>
                        <span class="page-badge">第 {res['page'] + 1} 页</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.caption(res['snippet'])
                    
                    if st.button(f"👉 查看原图", key=f"view_{i}"):
                        doc = docs_map[res['filename']]["doc"]
                        page = doc[res['page']]
                        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                        st.session_state.preview_img = pix.tobytes("png")
                        st.session_state.preview_info = f"{res['filename']} (第 {res['page']+1} 页)"
                    
                    st.markdown("---")

with col2:
    st.subheader("📄 原文透视")
    if st.session_state.preview_img:
        st.info(f"正在查看: {st.session_state.preview_info}")
        st.image(st.session_state.preview_img, use_column_width=True)
    else:
        st.markdown(
            """
            <div style="height: 400px; border: 2px dashed #cbd5e1; border-radius: 12px; 
            display: flex; align-items: center; justify-content: center; color: #94a3b8;">
                请点击左侧搜索结果查看详情
            </div>
            """, unsafe_allow_html=True
        )
