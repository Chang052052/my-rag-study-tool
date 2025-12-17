import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="Scholar Flow Ultimate")

st.markdown("""
<style>
    /* 结果卡片样式 */
    .result-box {
        padding: 15px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        margin-bottom: 12px;
        background-color: #f9fafb;
        transition: 0.2s;
    }
    .result-box:hover {
        border-color: #3b82f6;
        background-color: #eff6ff;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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
    .img-tag {
        background-color: #fce7f3;
        color: #9d174d;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑
# ==========================================

def convert_image_to_pdf_bytes(image_file):
    """将图片转换为 PDF 字节流 (为了统一处理)"""
    image = Image.open(image_file)
    # 转换为 RGB 防止报错
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    pdf_bytes = io.BytesIO()
    image.save(pdf_bytes, format='PDF')
    return pdf_bytes.getvalue()

@st.cache_resource(show_spinner=False)
def process_uploaded_files(uploaded_files):
    """
    处理所有上传文件，建立内存索引
    使用 cache_resource 确保性能，但 key 是文件列表，变化时会自动更新
    """
    docs_map = {}
    total_pages = 0
    
    for file in uploaded_files:
        try:
            file_bytes = None
            is_image = False
            
            # 判断文件类型
            if file.type == "application/pdf":
                file_bytes = file.read()
            elif file.type in ["image/png", "image/jpeg", "image/jpg"]:
                file_bytes = convert_image_to_pdf_bytes(file)
                is_image = True
            
            if file_bytes:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                docs_map[file.name] = {
                    "doc": doc,
                    "type": "image" if is_image else "pdf"
                }
                total_pages += len(doc)
        except Exception as e:
            print(f"Error processing {file.name}: {e}")
            
    return docs_map, total_pages

def search_engine(docs_map, query):
    """全库搜索"""
    results = []
    query_lower = query.lower()
    keywords = query_lower.split()
    
    for filename, data in docs_map.items():
        doc = data["doc"]
        file_type = data["type"]
        
        # 如果是纯图片转换来的 PDF，通常没有文字层，无法进行文本搜索
        # 这里给用户一个标记，或者只进行有限尝试
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            # 如果这页完全没字（比如扫描件），跳过搜索
            if not text.strip():
                continue

            text_lower = text.lower()
            
            # 评分算法
            score = 0
            for k in keywords:
                if k in text_lower:
                    score += 1
            
            if score > 0:
                # 提取上下文
                idx = text_lower.find(keywords[0])
                start = max(0, idx - 100)
                end = min(len(text), idx + 200)
                snippet = text[start:end].replace("\n", " ")
                
                results.append({
                    "filename": filename,
                    "page": page_num,
                    "score": score,
                    "snippet": "..." + snippet + "...",
                    "type": file_type
                })
    
    # 排序并返回更多结果 (修正：增加到 30 条)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:30]

# ==========================================
# 3. 界面逻辑
# ==========================================

st.title("🎓 Scholar Flow Ultimate")
st.caption("支持 PDF、JPG、PNG 多格式混合检索 | 自动刷新索引")

# 初始化状态
if 'view_img' not in st.session_state:
    st.session_state.view_img = None
    st.session_state.view_caption = "请搜索并点击结果"

# --- 侧边栏 ---
with st.sidebar:
    st.header("📂 资料库")
    
    # 1. 解锁文件格式限制
    uploaded_files = st.file_uploader(
        "拖入文件 (支持 PDF/图片)", 
        type=["pdf", "png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    
    docs_map = {}
    
    if uploaded_files:
        with st.spinner("正在建立索引 (含新文件)..."):
            # 2. 每次文件列表变化，这里都会重新运行，确保索引最新
            docs_map, total_pages = process_uploaded_files(uploaded_files)
            
        st.success(f"📚 已索引 {len(docs_map)} 个文件\n📄 共 {total_pages} 页内容")
        
        with st.expander("已加载文件详情"):
            for name, data in docs_map.items():
                icon = "🖼️" if data["type"] == "image" else "📄"
                st.text(f"{icon} {name}")
    else:
        st.info("请上传复习资料")

# --- 主界面：双栏 ---
col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("🔍 搜索")
    query = st.text_input("输入关键词...", placeholder="例如: Residue theorem")
    
    if query and docs_map:
        results = search_engine(docs_map, query)
        
        if not results:
            st.warning("🤔 未找到匹配内容。")
            st.caption("提示：如果是纯图片（扫描件），程序可能无法读取其中的文字。需要该图片本身包含文字层（OCR）。")
        else:
            st.write(f"共找到 {len(results)} 条结果：")
            
            for i, res in enumerate(results):
                with st.container():
                    # 动态标签
                    tag_class = "img-tag" if res['type'] == 'image' else "file-tag"
                    icon = "🖼️ 图片" if res['type'] == 'image' else "📄 文档"
                    
                    st.markdown(f"""
                    <div style="margin-bottom:4px;">
                        <span class="{tag_class}">{icon}: {res['filename']}</span>
                        <span style="font-weight:bold; color:#4b5563;">第 {res['page'] + 1} 页</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.caption(res['snippet'])
                    
                    # 查看按钮
                    if st.button(f"👉 查看原件 (结果 {i+1})", key=f"btn_{i}"):
                        doc_obj = docs_map[res['filename']]["doc"]
                        page = doc_obj[res['page']]
                        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                        st.session_state.view_img = pix.tobytes("png")
                        st.session_state.view_caption = f"{res['filename']} - 第 {res['page']+1} 页"
                    
                    st.markdown("---")

with col2:
    st.subheader("📄 阅读视图")
    if st.session_state.view_img:
        st.info(f"正在查看：{st.session_state.view_caption}")
        st.image(st.session_state.view_img, use_column_width=True)
    else:
        st.markdown(
            """
            <div style="height: 500px; border: 2px dashed #e5e7eb; border-radius: 10px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af;">
                <h3>👈 等待指令</h3>
                <p>点击左侧按钮查看高清原图</p>
            </div>
            """, unsafe_allow_html=True
        )
