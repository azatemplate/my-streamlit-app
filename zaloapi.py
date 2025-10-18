import streamlit as st
from PIL import Image, ImageFile
import io
import time
import zipfile
from datetime import datetime

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ========== INIT SESSION STATE ==========
if "config" not in st.session_state:
    st.session_state.config = {
        "max_size": 600,
        "logo_position": "third",
        "opacity": 50,
        "logo_scale": 100,
        "output_format": "jpg"
    }

if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = []

if "logo_bytes" not in st.session_state:
    st.session_state.logo_bytes = None

if "metadata" not in st.session_state:
    st.session_state.metadata = {
        "ImageDescription": "Ảnh đẹp từ Hoàng Loạt",
        "Tags": "hoàng loạt, du lịch, đẹp",
        "GPSLatitude": "21.0285",
        "GPSLongitude": "105.8542",
        "Artist": "Hoàng Loạt",
        "Copyright": "2025",
        "XPTitle": "Ảnh đẹp",
        "XPSubject": "Chụp ảnh chuyên nghiệp"
    }

if "processed_images" not in st.session_state:
    st.session_state.processed_images = []

# ========== HÀM XỬ LÝ ==========
def remove_diacritics(text):
    return text.replace("á", "a").replace("à", "a").replace("ả", "a").replace("ã", "a").replace("ạ", "a") \
              .replace("â", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ý", "y")

def process_single_image(image_bytes, config, metadata, logo_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        image.thumbnail((config["max_size"], config["max_size"]))

        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, (0, 0), image)
            image = background

        # Chèn logo
        if logo_bytes:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            base_scale = 1/3
            user_scale = config["logo_scale"]/100
            logo_scale = base_scale * user_scale
            logo_width = int(image.width * logo_scale)
            logo_height = int(logo_width * (logo.height/logo.width))
            logo_resized = logo.resize((logo_width, logo_height), Image.LANCZOS)

            opacity_value = config["opacity"]/100
            alpha = logo_resized.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity_value))
            logo_resized.putalpha(alpha)

            position = config["logo_position"]
            if position == "third":
                x, y = image.width//3, image.height//3
            else:  # topright
                x, y = image.width - logo_width - 20, 20

            image.paste(logo_resized, (x, y), logo_resized)

        # Lưu vào buffer
        output_buffer = io.BytesIO()
        out_ext = config["output_format"].lower()
        
        if out_ext in ["jpg", "jpeg"]:
            image.convert("RGB").save(output_buffer, "JPEG", quality=85, optimize=True)
        elif out_ext == "png":
            image.save(output_buffer, "PNG", optimize=True)
        elif out_ext == "webp":
            image.save(output_buffer, "WEBP", quality=80)

        output_bytes = output_buffer.getvalue()
        
        # Metadata text
        meta_text = "\n".join([f"{k}: {remove_diacritics(v)}" for k, v in metadata.items()])
        meta_bytes = meta_text.encode("utf-8")
        
        return output_bytes, meta_bytes, True
        
    except Exception as e:
        return None, None, str(e)

def create_zip(all_images, all_metas):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for i, (img_bytes, meta_bytes) in enumerate(zip(all_images, all_metas)):
            img_name = f"anh_{i+1}.{st.session_state.config['output_format']}"
            meta_name = f"anh_{i+1}.txt"
            zf.writestr(img_name, img_bytes)
            zf.writestr(meta_name, meta_bytes)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# ========== UI ==========
st.set_page_config(page_title="GEOTAG ẢNH", page_icon="📸", layout="wide")

st.title("📸 GEOTAG ẢNH HOÀNG LOẠT")
st.markdown("**HỖ TRỢ: 0967849934** | *Streamlit Cloud OK 100%*")

# TABS
tab1, tab2, tab3 = st.tabs(["⚙️ Cài Đặt", "📁 Ảnh & Logo", "🏷️ Metadata & Xử Lý"])

# TAB 1: CÀI ĐẶT
with tab1:
    st.header("⚙️ CÀI ĐẶT XỬ LÝ")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.config["max_size"] = st.slider("Max Size", 200, 2000, st.session_state.config["max_size"])
        st.session_state.config["logo_position"] = st.radio(
            "Vị trí Logo", ["third", "topright"],
            format_func=lambda x: "1/3 ảnh" if x == "third" else "Góc trên phải",
            index=0 if st.session_state.config["logo_position"] == "third" else 1
        )
    with col2:
        st.session_state.config["opacity"] = st.slider("Độ mờ (%)", 0, 100, st.session_state.config["opacity"])
        st.session_state.config["logo_scale"] = st.slider("Kích thước (%)", 10, 200, st.session_state.config["logo_scale"])
    
    st.session_state.config["output_format"] = st.selectbox(
        "Định dạng", ["jpg", "jpeg", "png", "webp"],
        index=["jpg", "jpeg", "png", "webp"].index(st.session_state.config["output_format"])
    )

# TAB 2: ẢNH & LOGO
with tab2:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📁 UPLOAD ẢNH")
        uploaded_files = st.file_uploader("Chọn nhiều ảnh", 
                                        type=['jpg', 'jpeg', 'png', 'webp', 'heic'], 
                                        accept_multiple_files=True)
        
        if uploaded_files:
            st.session_state.image_bytes = [f.getvalue() for f in uploaded_files]
            st.success(f"✅ **{len(st.session_state.image_bytes)} ảnh**")
            st.write(f"• " + ", ".join([f.name for f in uploaded_files[:3]]))
            if len(uploaded_files) > 3:
                st.write(f"... và {len(uploaded_files)-3} ảnh nữa")
    
    with col2:
        st.subheader("🏷️ LOGO")
        logo_file = st.file_uploader("Chọn logo", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            st.session_state.logo_bytes = logo_file.getvalue()
            st.image(logo_file, width=150)
            st.success("✅ Logo OK!")
        else:
            st.info("👆 Chọn PNG/JPG")

# TAB 3: METADATA & PROCESS
with tab3:
    st.header("🏷️ METADATA EDITOR")
    
    # Metadata Editor
    metadata_text = st.text_area(
        "Chỉnh sửa metadata:",
        value="\n".join([f"{k}: {v}" for k, v in st.session_state.metadata.items()]),
        height=250,
        help="Mỗi dòng: Tên: Giá trị"
    )
    
    if st.button("💾 Lưu Metadata"):
        new_metadata = {}
        for line in metadata_text.split("\n"):
            if ": " in line and not line.startswith("#"):
                key, value = line.split(": ", 1)
                new_metadata[key.strip()] = value.strip()
        st.session_state.metadata = new_metadata
        st.success("✅ Metadata đã lưu!")
    
    # Preview metadata
    st.subheader("📋 XEM TRƯỚC")
    for key, value in st.session_state.metadata.items():
        st.write(f"**{key}:** {value}")
    
    # PROCESS BUTTON
    if st.button("🚀 XỬ LÝ TẤT CẢ", type="primary", use_container_width=True):
        if not st.session_state.image_bytes:
            st.error("❌ Chọn ảnh trước!")
            st.stop()
        
        st.subheader("⏳ ĐANG XỬ LÝ...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_images = []
        all_metas = []
        success_count = 0
        
        for i, img_bytes in enumerate(st.session_state.image_bytes):
            status_text.text(f"⏳ Ảnh {i+1}/{len(st.session_state.image_bytes)}")
            progress_bar.progress((i+1)/len(st.session_state.image_bytes))
            
            img_out, meta_out, error = process_single_image(
                img_bytes, st.session_state.config, 
                st.session_state.metadata, st.session_state.logo_bytes
            )
            
            if error:
                st.error(f"❌ Ảnh {i+1}: {error}")
            else:
                all_images.append(img_out)
                all_metas.append(meta_out)
                success_count += 1
        
        progress_bar.progress(1.0)
        status_text.text("🎉 HOÀN THÀNH!")
        
        st.session_state.processed_images = list(zip(all_images, all_metas))
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ **{success_count} ảnh OK!**")
        with col2:
            st.info(f"📊 +{success_count} file metadata")

    # DOWNLOAD SECTION
    if st.session_state.processed_images:
        st.subheader("📥 TẢI KẾT QUẢ")
        
        # ZIP DOWNLOAD
        zip_data = create_zip(
            [img for img, _ in st.session_state.processed_images],
            [meta for _, meta in st.session_state.processed_images]
        )
        st.download_button(
            label=f"🚀 TẢI ZIP ({len(st.session_state.processed_images)} ảnh + metadata)",
            data=zip_data,
            file_name=f"geotag_hoang_loat_{int(time.time())}.zip",
            mime="application/zip"
        )
        
        # PREVIEW
        st.subheader("👀 XEM TRƯỚC")
        cols = st.columns(3)
        for i, (img_bytes, _) in enumerate(st.session_state.processed_images[:3]):
            with cols[i]:
                img = Image.open(io.BytesIO(img_bytes))
                st.image(img, width=150)

st.markdown("---")
st.markdown("*© 2025 GEOTAG ẢNH HOÀNG LOẠT - 0967849934*")
