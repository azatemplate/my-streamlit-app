import streamlit as st
from PIL import Image, ImageFile
import os
import piexif
from datetime import datetime
import unicodedata
import json
import time

ImageFile.LOAD_TRUNCATED_IMAGES = True

CONFIG_FILE = "config.json"
OUTPUT_FOLDER = "output"

# ========== Các hàm xử lý ảnh & metadata ==========
def load_metadata_from_file(file_path):
    metadata = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            for line in file:
                line = line.strip()
                if ": " in line:
                    key, value = line.split(": ", 1)
                    metadata[key] = value
    return metadata

def rational_to_dms(value):
    degrees = int(float(value))
    minutes = int((float(value) - degrees) * 60)
    seconds = int((float(value) - degrees - minutes / 60) * 3600)
    return [(degrees, 1), (minutes, 1), (seconds, 1)]

def remove_diacritics(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def edit_image_metadata(output_image_path, metadata):
    img = Image.open(output_image_path)
    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}

    image_name = os.path.splitext(os.path.basename(output_image_path))[0]

    if "ImageDescription" not in metadata or not metadata["ImageDescription"]:
        metadata["ImageDescription"] = image_name
    if "XPTitle" not in metadata or not metadata["XPTitle"]:
        metadata["XPTitle"] = image_name
    if "XPSubject" not in metadata or not metadata["XPSubject"]:
        metadata["XPSubject"] = image_name
    if "Comments" not in metadata or not metadata["Comments"]:
        metadata["Comments"] = image_name
    if "DateTimeOriginal" not in metadata or not metadata["DateTimeOriginal"]:
        metadata["DateTimeOriginal"] = datetime.now().strftime("%Y:%m:%d %H:%M:%S")

    metadata["Tags"] = remove_diacritics(metadata.get("Tags", ""))
    metadata["Comments"] = remove_diacritics(metadata.get("Comments", ""))

    try:
        if "GPSLatitude" in metadata and "GPSLongitude" in metadata:
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = rational_to_dms(metadata["GPSLatitude"])
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = rational_to_dms(metadata["GPSLongitude"])

        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata["ImageDescription"].encode('utf-8')
        if "Artist" in metadata:
            exif_dict["0th"][piexif.ImageIFD.Artist] = metadata["Artist"].encode('utf-8')
        if "Copyright" in metadata:
            exif_dict["0th"][piexif.ImageIFD.Copyright] = metadata["Copyright"].encode('utf-8')
        if "Make" in metadata:
            exif_dict["0th"][piexif.ImageIFD.Make] = metadata["Make"].encode('utf-8')
        if "Model" in metadata:
            exif_dict["0th"][piexif.ImageIFD.Model] = metadata["Model"].encode('utf-8')
        if "Software" in metadata:
            exif_dict["0th"][piexif.ImageIFD.Software] = metadata["Software"].encode('utf-8')

        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = metadata["DateTimeOriginal"].encode('utf-8')

        exif_dict["0th"][piexif.ImageIFD.Rating] = 5
        exif_dict["0th"][piexif.ImageIFD.RatingPercent] = 100

        exif_dict["0th"][piexif.ImageIFD.XPComment] = metadata["Comments"].encode('utf-16le', errors='ignore')
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = metadata["XPTitle"].encode('utf-16le', errors='ignore')
        exif_dict["0th"][piexif.ImageIFD.XPSubject] = metadata["XPSubject"].encode('utf-16le', errors='ignore')
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = metadata["Tags"].encode('utf-16le', errors='ignore')

        exif_bytes = piexif.dump(exif_dict)
        img.save(output_image_path, "jpeg", exif=exif_bytes)
    except Exception as e:
        st.error(f"Error applying metadata to {output_image_path}: {str(e)}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "max_size": 600,
        "logo_position": "third",
        "opacity": 50,
        "logo_scale": 100,
        "output_format": "jpg"
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def process_single_image(img_path, config, metadata, logo_path):
    try:
        image = Image.open(img_path)
        image.load()
        image.thumbnail((config["max_size"], config["max_size"]))

        # Xử lý nền trong suốt (PNG → JPG)
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, (0, 0), image)
            image = background

        # Chèn logo nếu có
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")

            # Scale logo
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

            # Vị trí dán logo
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
            image.convert("RGB").save(
                output_image_path, "JPEG", quality=85, optimize=True, progressive=True
            )
            edit_image_metadata(output_image_path, metadata.copy())
        elif out_ext == "png":
            image.save(output_image_path, "PNG", optimize=True)
        elif out_ext == "webp":
            image.save(output_image_path, "WEBP", quality=80, method=6)

        return output_image_path, True
    except Exception as e:
        return None, str(e)

# ========== Streamlit App ==========
def main():
    st.set_page_config(
        page_title="GEOTAG ẢNH HOÀNG LOẠT",
        page_icon="📸",
        layout="wide"
    )

    # Tạo thư mục output
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Header
    st.title("📸 GEOTAG ẢNH HOÀNG LOẠT")
    st.markdown("*HỖ TRỢ: 0967849934*")

    # Load config
    config = load_config()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cài đặt")
        
        # Max Size
        config["max_size"] = st.slider("Max Size", 200, 2000, config["max_size"])
        
        # Logo Position
        config["logo_position"] = st.radio(
            "Vị trí Logo", 
            ["third", "topright"], 
            format_func=lambda x: "1/3 ảnh" if x == "third" else "Góc trên bên phải",
            index=0 if config["logo_position"] == "third" else 1
        )
        
        # Opacity & Scale (cùng hàng)
        col1, col2 = st.columns(2)
        with col1:
            config["opacity"] = st.slider("Độ mờ (%)", 0, 100, config["opacity"])
        with col2:
            config["logo_scale"] = st.slider("Kích thước Logo (%)", 10, 200, config["logo_scale"])
        
        # Output Format
        config["output_format"] = st.selectbox(
            "Định dạng xuất", 
            ["jpg", "jpeg", "png", "webp"], 
            index=["jpg", "jpeg", "png", "webp"].index(config["output_format"])
        )
        
        st.markdown("---")
        if st.button("💾 Lưu Cấu hình"):
            save_config(config)
            st.success("Đã lưu cấu hình!")

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📁 Chọn Ảnh")
        uploaded_files = st.file_uploader(
            "Chọn nhiều ảnh", 
            type=['jpg', 'jpeg', 'png', 'webp', 'heic'],
            accept_multiple_files=True,
            help="Hỗ trợ: JPG, JPEG, PNG, WEBP, HEIC"
        )
        
        if uploaded_files:
            image_paths = []
            for file in uploaded_files:
                # Lưu file tạm
                temp_path = os.path.join("temp", file.name)
                os.makedirs("temp", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                image_paths.append(temp_path)
            
            st.text(f"Đã chọn: **{len(image_paths)} ảnh**")
            for path in image_paths[:5]:  # Hiển thị 5 ảnh đầu
                st.text(f"• {os.path.basename(path)}")

    with col2:
        st.subheader("🏷️ Metadata")
        if st.button("📝 Mở metadata.txt"):
            with open("metadata.txt", "w", encoding="utf-8") as f:
                f.write("# Định dạng: Tên trường: Giá trị\n")
                f.write("ImageDescription: Mô tả ảnh\n")
                f.write("Tags: từ khóa 1, từ khóa 2\n")
                f.write("GPSLatitude: 21.0285\n")
                f.write("GPSLongitude: 105.8542\n")
            st.success("Đã tạo metadata.txt! Mở bằng Notepad để chỉnh sửa.")
        
        st.info("**Cần file:** `metadata.txt` trong thư mục gốc")

        st.subheader("🏷️ Logo")
        logo_file = st.file_uploader("Chọn logo", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            logo_path = os.path.join("temp", logo_file.name)
            with open(logo_path, "wb") as f:
                f.write(logo_file.getbuffer())
            st.image(logo_file, caption="Logo Preview", width=150)
            config["logo_path"] = logo_path
        else:
            config["logo_path"] = ""

    # Progress bar & Process button
    if st.button("🚀 CHẠY XỬ LÝ", type="primary", use_container_width=True) and image_paths:
        metadata_file = "metadata.txt"
        if not os.path.exists(metadata_file):
            st.error("❌ **Không tìm thấy metadata.txt**")
            st.info("Tạo file bằng nút 'Mở metadata.txt' ở sidebar")
            return

        metadata = load_metadata_from_file(metadata_file)
        save_config(config)

        progress_bar = st.progress(0)
        status_text = st.empty()
        result_placeholder = st.empty()

        success_count = 0
        total = len(image_paths)

        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

        for i, img_path in enumerate(image_paths):
            status_text.text(f"Đang xử lý: {os.path.basename(img_path)} ({i+1}/{total})")
            progress_bar.progress((i + 1) / total)

            output_path, error = process_single_image(img_path, config, metadata, config.get("logo_path"))
            
            if error:
                result_placeholder.error(f"❌ {os.path.basename(img_path)}: {error}")
            else:
                success_count += 1
                result_placeholder.success(f"✅ {os.path.basename(output_path)}")

        # Kết quả cuối
        progress_bar.progress(1.0)
        status_text.text("🎉 HOÀN TẤT!")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.success(f"**{success_count}/{total} ảnh thành công**")
        with col_b:
            st.info(f"📁 **Output:** `{OUTPUT_FOLDER}`")

        # Download all
        with open(os.path.join(OUTPUT_FOLDER, "__success.txt"), "w") as f:
            f.write(f"Xử lý thành công {success_count}/{total} ảnh\n")
        
        with open(os.path.join(OUTPUT_FOLDER, "__success.txt"), "rb") as f:
            st.download_button(
                label="📥 Tải toàn bộ Output (ZIP)",
                data=f,
                file_name="geotag_result.zip",
                mime="application/zip"
            )

        # Hiển thị ảnh mẫu
        if success_count > 0:
            sample_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))][:3]
            if sample_files:
                st.subheader("👀 **Xem trước kết quả**")
                cols = st.columns(len(sample_files))
                for i, filename in enumerate(sample_files):
                    with cols[i]:
                        img = Image.open(os.path.join(OUTPUT_FOLDER, filename))
                        st.image(img, caption=filename, width=200)

    elif st.button("🚀 CHẠY XỬ LÝ", type="primary") and not image_paths:
        st.warning("⚠️ **Vui lòng chọn ít nhất 1 ảnh!**")

    # Footer
    st.markdown("---")
    st.markdown("*© 2025 GEOTAG ẢNH HOÀNG LOẠT - HỖ TRỢ: 0967849934*")

if __name__ == "__main__":
    main()
