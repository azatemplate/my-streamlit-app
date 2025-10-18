import streamlit as st
import subprocess
import sys
from PIL import Image, ImageFile
import os
import json
import time

# ✅ AUTO-INSTALL MISSING PACKAGES
@st.cache_data
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import piexif
except ImportError:
    st.warning("⏳ Đang cài đặt piexif...")
    install_package("piexif")
    import piexif

ImageFile.LOAD_TRUNCATED_IMAGES = True

CONFIG_FILE = "config.json"
OUTPUT_FOLDER = "output"

# ========== Các hàm xử lý ảnh & metadata ==========
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

def rational_to_dms(value):
    try:
        degrees = int(float(value))
        minutes = int((float(value) - degrees) * 60)
        seconds = int((float(value) - degrees - minutes / 60) * 3600)
        return [(degrees, 1), (minutes, 1), (seconds, 1)]
    except:
        return [(0, 1), (0, 1), (0, 1)]

def remove_diacritics(input_str):
    try:
        import unicodedata
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    except:
        return input_str

def edit_image_metadata(output_image_path, metadata):
    try:
        img = Image.open(output_image_path)
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
            metadata["DateTimeOriginal"] = time.strftime("%Y:%m:%d %H:%M:%S")

        metadata["Tags"] = remove_diacritics(metadata.get("Tags", ""))
        metadata["Comments"] = remove_diacritics(metadata.get("Comments", ""))

        if "GPSLatitude" in metadata and "GPSLongitude" in metadata:
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = rational_to_dms(metadata["GPSLatitude"])
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = rational_to_dms(metadata["GPSLongitude"])
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = b'N' if float(metadata["GPSLatitude"]) >= 0 else b'S'
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = b'E' if float(metadata["GPSLongitude"]) >= 0 else b'W'

        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata["ImageDescription"].encode('utf-8')
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
        pass  # Silent fail for non-JPG

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

        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, (0, 0), image)
            image = background

        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            base_scale = 1 / 3
            user_scale = config["logo_scale"] / 100.0
            logo_scale = base_scale * user_scale
            logo_width = int(image.width * logo_scale)
            logo_height = int(logo_width * (logo.height / logo.width))
            logo_resized = logo.resize((logo_width, logo_height), Image.LANCZOS)

            opacity_value = config["opacity"] / 100.0
            alpha = logo_resized.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity_value))
            logo_resized.putalpha(alpha)

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

        out_ext = config["output_format"].lower()
        out_name = os.path.splitext(os.path.basename(img_path))[0] + f".{out_ext}"
        output_image_path = os.path.join(OUTPUT_FOLDER, out_name)

        if out_ext in ["jpg", "jpeg"]:
            image.convert("RGB").save(output_image_path, "JPEG", quality=85, optimize=True)
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
    st.set_page_config(page_title="GEOTAG ẢNH", page_icon="📸", layout="wide")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    st.title("📸 GEOTAG ẢNH HOÀNG LOẠT")
    st.markdown("*HỖ TRỢ: 0967849934*")

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
        with col1: config["opacity"] = st.slider("Độ mờ (%)", 0, 100, config["opacity"])
        with col2: config["logo_scale"] = st.slider("Kích thước (%)", 10, 200, config["logo_scale"])
        config["output_format"] = st.selectbox("Định dạng", ["jpg", "jpeg", "png", "webp"], index=["jpg", "jpeg", "png", "webp"].index(config["output_format"]))
        
        if st.button("💾 Lưu"): 
            save_config(config)
            st.success("Đã lưu!")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📁 Chọn Ảnh")
        uploaded_files = st.file_uploader("Chọn ảnh", type=['jpg', 'jpeg', 'png', 'webp', 'heic'], accept_multiple_files=True)
        
        if uploaded_files:
            image_paths = []
            os.makedirs("temp", exist_ok=True)
            for file in uploaded_files:
                temp_path = os.path.join("temp", file.name)
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                image_paths.append(temp_path)
            
            st.success(f"✅ **{len(image_paths)} ảnh**")
            st.text("\n".join([f"• {os.path.basename(p)}" for p in image_paths[:5]]))

    with col2:
        st.subheader("🏷️ Metadata")
        if st.button("📝 Tạo metadata.txt"):
            with open("metadata.txt", "w", encoding="utf-8") as f:
                f.write("# Tên trường: Giá trị\n")
                f.write("ImageDescription: Mô tả ảnh\n")
                f.write("Tags: từ khóa 1, từ khóa 2\n")
                f.write("GPSLatitude: 21.0285\n")
                f.write("GPSLongitude: 105.8542\n")
            st.success("✅ Đã tạo `metadata.txt`!")

        st.subheader("🏷️ Logo")
        logo_file = st.file_uploader("Chọn logo", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            logo_path = os.path.join("temp", logo_file.name)
            with open(logo_path, "wb") as f:
                f.write(logo_file.getbuffer())
            st.image(logo_file, width=150)
            config["logo_path"] = logo_path
        else:
            config["logo_path"] = ""

    # Process
    if st.button("🚀 CHẠY XỬ LÝ", type="primary") and uploaded_files:
        if not os.path.exists("metadata.txt"):
            st.error("❌ **Cần metadata.txt!** Click 'Tạo metadata.txt'")
            return

        metadata = load_metadata_from_file("metadata.txt")
        save_config(config)

        progress_bar = st.progress(0)
        status_text = st.empty()
        result_text = st.empty()

        success_count = 0
        total = len(image_paths)

        for i, img_path in enumerate(image_paths):
            status_text.text(f"⏳ {os.path.basename(img_path)} ({i+1}/{total})")
            progress_bar.progress((i + 1) / total)

            output_path, error = process_single_image(img_path, config, metadata, config.get("logo_path"))
            
            if error:
                result_text.error(f"❌ {os.path.basename(img_path)}")
            else:
                success_count += 1
                result_text.success(f"✅ {os.path.basename(output_path)}")

        progress_bar.progress(1.0)
        st.success(f"🎉 **{success_count}/{total} THÀNH CÔNG!**")
        st.info(f"📁 **Output:** `{OUTPUT_FOLDER}`")

        # Download button
        with open(os.path.join(OUTPUT_FOLDER, "result.txt"), "w") as f:
            f.write(f"Thành công: {success_count}/{total}\n")
        with open(os.path.join(OUTPUT_FOLDER, "result.txt"), "rb") as f:
            st.download_button("📥 Tải kết quả", f, "geotag_result.zip")

    elif st.button("🚀 CHẠY XỬ LÝ"):
        st.warning("⚠️ Chọn ảnh trước!")

    st.markdown("---")
    st.markdown("*© 2025 GEOTAG ẢNH - 0967849934*")

if __name__ == "__main__":
    main()
