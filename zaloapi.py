import streamlit as st
from PIL import Image, ImageFile
import os
import json
import time

ImageFile.LOAD_TRUNCATED_IMAGES = True

CONFIG_FILE = "config.json"
OUTPUT_FOLDER = "output"

# ========== Các hàm xử lý ảnh (KHÔNG DÙNG piexif) ==========
def load_metadata_from_file(file_path):
    metadata = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as file:
                for line in file:
                    line = line.strip()
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        metadata[key] = value
        except:
            pass
    return metadata

def remove_diacritics(input_str):
    # Simple version không cần unicodedata
    return input_str.replace("á", "a").replace("à", "a").replace("ả", "a").replace("ã", "a").replace("ạ", "a") \
                   .replace("â", "a").replace("ầ", "a").replace("ấ", "a").replace("ẩ", "a").replace("ẫ", "a").replace("ậ", "a") \
                   .replace("é", "e").replace("è", "e").replace("ẻ", "e").replace("ẽ", "e").replace("ẹ", "e") \
                   .replace("ê", "e").replace("ề", "e").replace("ế", "e").replace("ể", "e").replace("ễ", "e").replace("ệ", "e") \
                   .replace("í", "i").replace("ì", "i").replace("ỉ", "i").replace("ĩ", "i").replace("ị", "i") \
                   .replace("ó", "o").replace("ò", "o").replace("ỏ", "o").replace("õ", "o").replace("ọ", "o") \
                   .replace("ô", "o").replace("ồ", "o").replace("ố", "o").replace("ổ", "o").replace("ỗ", "o").replace("ộ", "o") \
                   .replace("ơ", "o").replace("ờ", "o").replace("ớ", "o").replace("ở", "o").replace("ỡ", "o").replace("ợ", "o") \
                   .replace("ú", "u").replace("ù", "u").replace("ủ", "u").replace("ũ", "u").replace("ụ", "u") \
                   .replace("ư", "u").replace("ừ", "u").replace("ứ", "u").replace("ử", "u").replace("ữ", "u").replace("ự", "u") \
                   .replace("ý", "y").replace("ỳ", "y").replace("ỷ", "y").replace("ỹ", "y").replace("ỵ", "y")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "max_size": 600,
        "logo_position": "third",
        "opacity": 50,
        "logo_scale": 100,
        "output_format": "jpg"
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except:
        pass

def process_single_image(img_path, config, metadata, logo_path):
    try:
        image = Image.open(img_path)
        image.load()
        image.thumbnail((config["max_size"], config["max_size"]))

        # Xử lý nền trong suốt
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, (0, 0), image)
            image = background

        # Chèn logo nếu có
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            
            base_scale = 1 / 3
            user_scale = config["logo_scale"] / 100.0
            logo_scale = base_scale * user_scale
            logo_width = int(image.width * logo_scale)
            logo_height = int(logo_width * (logo.height / logo.width))
            logo_resized = logo.resize((logo_width, logo_height), Image.LANCZOS)

            # Áp dụng độ mờ
            opacity_value = config["opacity"] / 100.0
            alpha = logo_resized.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity_value))
            logo_resized.putalpha(alpha)

            # Vị trí logo
            position = config["logo_position"]
            if position == "third":
                x = image.width // 3
                y = image.height // 3
            elif position == "topright":
                x = image.width - logo_width - 20
                y = 20
            else:
                x, y = 100, image.height - logo_height - 100

            image.paste(logo_resized, (x, y), logo_resized)

        # Lưu ảnh
        out_ext = config["output_format"].lower()
        out_name = os.path.splitext(os.path.basename(img_path))[0] + f".{out_ext}"
        output_image_path = os.path.join(OUTPUT_FOLDER, out_name)

        if out_ext in ["jpg", "jpeg"]:
            image.convert("RGB").save(output_image_path, "JPEG", quality=85, optimize=True)
        elif out_ext == "png":
            image.save(output_image_path, "PNG", optimize=True)
        elif out_ext == "webp":
            image.save(output_image_path, "WEBP", quality=80, method=6)

        # Metadata đơn giản (text file kèm theo)
        if metadata:
            meta_name = out_name + ".txt"
            with open(os.path.join(OUTPUT_FOLDER, meta_name), "w", encoding="utf-8") as f:
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")

        return output_image_path, True
    except Exception as e:
        return None, str(e)

# ========== Streamlit App ==========
def main():
    st.set_page_config(page_title="GEOTAG ẢNH", page_icon="📸", layout="wide")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    st.title("📸 GEOTAG ẢNH HOÀNG LOẠT")
    st.markdown("**HỖ TRỢ: 0967849934** | *Không cần cài thêm package!*")

    config = load_config()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cài đặt")
        config["max_size"] = st.slider("Max Size", 200, 2000, config["max_size"])
        config["logo_position"] = st.radio(
            "Vị trí Logo", 
            ["third", "topright"], 
            format_func=lambda x: "1/3 ảnh" if x == "third" else "Góc trên bên phải",
            index=0 if config["logo_position"] == "third" else 1
        )
        col1, col2 = st.columns(2)
        with col1: 
            config["opacity"] = st.slider("Độ mờ (%)", 0, 100, config["opacity"])
        with col2: 
            config["logo_scale"] = st.slider("Kích thước (%)", 10, 200, config["logo_scale"])
        config["output_format"] = st.selectbox(
            "Định dạng", 
            ["jpg", "jpeg", "png", "webp"], 
            index=["jpg", "jpeg", "png", "webp"].index(config["output_format"])
        )
        
        if st.button("💾 Lưu"): 
            save_config(config)
            st.success("Đã lưu!")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📁 Chọn Ảnh")
        uploaded_files = st.file_uploader(
            "Chọn nhiều ảnh", 
            type=['jpg', 'jpeg', 'png', 'webp', 'heic'], 
            accept_multiple_files=True
        )
        
        image_paths = []
        if uploaded_files:
            for file in uploaded_files:
                temp_path = os.path.join("temp", file.name)
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                image_paths.append(temp_path)
            
            st.success(f"✅ **{len(image_paths)} ảnh**")
            with st.expander("📋 Danh sách ảnh"):
                for path in image_paths:
                    st.text(f"• {os.path.basename(path)}")

    with col2:
        st.subheader("🏷️ Metadata")
        if st.button("📝 Tạo metadata.txt"):
            with open("metadata.txt", "w", encoding="utf-8") as f:
                f.write("# Tên trường: Giá trị\n")
                f.write("ImageDescription: Mô tả ảnh\n")
                f.write("Tags: từ khóa 1, từ khóa 2\n")
                f.write("GPSLatitude: 21.0285\n")
                f.write("GPSLongitude: 105.8542\n")
                f.write("Artist: Hoàng Loạt\n")
                f.write("Copyright: 2025\n")
            st.success("✅ Đã tạo `metadata.txt`!")

        st.info("**Mỗi ảnh sẽ có file `.txt` kèm metadata**")

        st.subheader("🏷️ Logo")
        logo_file = st.file_uploader("Chọn logo", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            logo_path = os.path.join("temp", f"logo_{int(time.time())}_{logo_file.name}")
            with open(logo_path, "wb") as f:
                f.write(logo_file.getbuffer())
            st.image(logo_file, caption="Logo Preview", width=150)
            config["logo_path"] = logo_path
        else:
            config["logo_path"] = ""

    # Process button
    if st.button("🚀 CHẠY XỬ LÝ", type="primary", use_container_width=True):
        if not image_paths:
            st.warning("⚠️ **Chọn ảnh trước!**")
            st.stop()
        
        if not os.path.exists("metadata.txt"):
            st.error("❌ **Cần metadata.txt!** Click 'Tạo metadata.txt'")
            st.stop()

        metadata = load_metadata_from_file("metadata.txt")
        save_config(config)

        st.subheader("⏳ ĐANG XỬ LÝ...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_placeholder = st.container()

        success_count = 0
        total = len(image_paths)

        for i, img_path in enumerate(image_paths):
            with result_placeholder.container():
                status_text.text(f"⏳ {os.path.basename(img_path)} ({i+1}/{total})")
                progress_bar.progress((i + 1) / total)

                output_path, error = process_single_image(
                    img_path, config, metadata, config.get("logo_path")
                )
                
                if error:
                    st.error(f"❌ {os.path.basename(img_path)}: {error}")
                else:
                    success_count += 1
                    st.success(f"✅ {os.path.basename(output_path)}")

        progress_bar.progress(1.0)
        status_text.text("🎉 HOÀN TẤT!")

        col_a, col_b = st.columns(2)
        with col_a:
            st.success(f"**{success_count}/{total} THÀNH CÔNG!**")
        with col_b:
            st.info(f"📁 **Output:** `{OUTPUT_FOLDER}`")

        # Download all images
        if success_count > 0:
            st.subheader("📥 TẢI KẾT QUẢ")
            
            # List files
            output_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            if output_files:
                cols = st.columns(min(4, len(output_files)))
                for i, filename in enumerate(output_files):
                    with cols[i % 4]:
                        img_path = os.path.join(OUTPUT_FOLDER, filename)
                        with open(img_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ {filename}",
                                data=f.read(),
                                file_name=filename,
                                mime="image/jpeg"
                            )

                # Preview
                st.subheader("👀 XEM TRƯỚC")
                preview_cols = st.columns(3)
                for i, filename in enumerate(output_files[:3]):
                    with preview_cols[i]:
                        img = Image.open(os.path.join(OUTPUT_FOLDER, filename))
                        st.image(img, caption=filename, width=150)

    st.markdown("---")
    st.markdown("*© 2025 GEOTAG ẢNH HOÀNG LOẠT - HỖ TRỢ: 0967849934*")

if __name__ == "__main__":
    main()
