import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# -----------------------------
# 🧱 Cấu hình giao diện chính
# -----------------------------
st.set_page_config(page_title="Qforia", layout="wide")
st.title("🔍 Qforia: Trình mô phỏng Query Fan-Out cho AI")

# -----------------------------
# ⚙️ Cấu hình bên trái
# -----------------------------
st.sidebar.header("Cấu hình")
gemini_key = st.sidebar.text_input("🔑 Nhập khóa Gemini API", type="password")

input_mode = st.sidebar.radio(
    "Chế độ nhập truy vấn",
    ["Truy vấn đơn", "Danh sách hàng loạt"]
)

if input_mode == "Truy vấn đơn":
    user_query = st.sidebar.text_area(
        "✍️ Nhập câu hỏi của bạn",
        "Xe SUV điện nào tốt nhất để lái lên núi Rainier?",
        height=120
    )
else:
    bulk_text = st.sidebar.text_area(
        "📋 Dán các truy vấn (mỗi dòng một câu hỏi)",
        "Xe SUV điện tốt nhất để đi trong tuyết\nPhương pháp tập ngủ cho trẻ nhỏ\nCách bảo quản men chua trong ngăn đá",
        height=180
    )

mode = st.sidebar.radio(
    "🧠 Chế độ tìm kiếm",
    ["Tổng quan AI (đơn giản)", "Chế độ AI (nâng cao)"]
)

# -----------------------------
# 🔐 Cấu hình API Gemini
# -----------------------------
if gemini_key:
    genai.configure(api_key=gemini_key)
    model_name = "gemini-2.5-pro"
    model = genai.GenerativeModel(model_name)
else:
    st.error("⚠️ Vui lòng nhập Gemini API Key để tiếp tục.")
    st.stop()

# -----------------------------
# 📚 Các loại định dạng nội dung
# -----------------------------
ALLOWED_FORMATS = [
    "web_article", "faq_page", "how_to_steps", "comparison_table",
    "buyers_guide", "checklist", "product_spec_sheet", "glossary/definition",
    "pricing_page", "review_roundup", "tutorial_video/transcript",
    "podcast_transcript", "code_samples/docs", "api_reference",
    "calculator/tool", "dataset", "image_gallery", "map/local_pack",
    "forum/qna", "pdf_whitepaper", "case_study", "press_release",
    "interactive_widget"
]

# -----------------------------
# 🧩 Hàm tạo prompt cho mô hình
# -----------------------------
def QUERY_FANOUT_PROMPT(q, mode):
    min_queries_simple = 10
    min_queries_complex = 20

    if mode == "Tổng quan AI (đơn giản)":
        num_queries_instruction = (
            f"Phân tích truy vấn: \"{q}\". Dựa trên chế độ '{mode}', "
            f"bạn cần xác định số lượng truy vấn mở rộng tối ưu (tối thiểu {min_queries_simple}). "
            f"Với truy vấn đơn giản, tạo khoảng {min_queries_simple}-{min_queries_simple + 2} truy vấn. "
            f"Nếu có nhiều khía cạnh, tạo {min_queries_simple + 3}-{min_queries_simple + 5} truy vấn. "
            f"Hãy giải thích ngắn gọn lý do chọn số lượng này."
        )
    else:
        num_queries_instruction = (
            f"Phân tích truy vấn: \"{q}\". Dựa trên chế độ '{mode}', "
            f"bạn cần xác định số lượng truy vấn mở rộng tối ưu (tối thiểu {min_queries_complex}). "
            f"Với truy vấn phức tạp (so sánh, hướng dẫn, đặc tả...), tạo "
            f"{min_queries_complex + 5}-{min_queries_complex + 10} truy vấn. "
            f"Hãy giải thích lý do."
        )

    routing_note = (
        "Với MỖI truy vấn mở rộng, hãy xác định kiểu nội dung phù hợp nhất "
        "(ví dụ: hướng dẫn → 'how_to_steps', so sánh → 'comparison_table', bài viết → 'web_article'). "
        "Chỉ chọn MỘT nhãn trong danh sách sau:\n"
        + ", ".join(ALLOWED_FORMATS) +
        ".\nTrả về JSON với các trường 'routing_format' và 'format_reason'."
    )

    return (
        f"Bạn đang mô phỏng hệ thống fan-out truy vấn của Google.\n"
        f"Truy vấn gốc: \"{q}\"\nChế độ: \"{mode}\"\n\n"
        f"{num_queries_instruction}\n\n"
        f"Mỗi loại biến thể cần có ít nhất một truy vấn:\n"
        f"1. Reformulations\n2. Related Queries\n3. Implicit Queries\n4. Comparative Queries\n"
        f"5. Entity Expansions\n6. Personalized Queries\n\n"
        f"{routing_note}\n\n"
        f"Trả về JSON đúng cấu trúc sau:\n"
        "{\n"
        "  \"generation_details\": {\n"
        "    \"target_query_count\": 12,\n"
        "    \"reasoning_for_count\": \"...\"\n"
        "  },\n"
        "  \"expanded_queries\": [\n"
        "    {\n"
        "      \"query\": \"...\",\n"
        "      \"type\": \"reformulation | related | implicit | comparative | entity_expansion | personalized\",\n"
        "      \"user_intent\": \"...\",\n"
        "      \"reasoning\": \"...\",\n"
        "      \"routing_format\": \"one_of_allowed_labels\",\n"
        "      \"format_reason\": \"1 câu lý do\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

# -----------------------------
# 🧮 Hàm sinh kết quả fan-out
# -----------------------------
def generate_fanout(query, mode):
    prompt = QUERY_FANOUT_PROMPT(query, mode)
    response = model.generate_content(prompt)
    json_text = response.text.strip()

    # Xử lý khi có markdown fence
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]
    json_text = json_text.strip()

    data = json.loads(json_text)
    generation_details = data.get("generation_details", {})
    expanded_queries = data.get("expanded_queries", [])

    return generation_details, expanded_queries, json_text

# -----------------------------
# 🚀 Chạy mô phỏng
# -----------------------------
if 'last_runs' not in st.session_state:
    st.session_state.last_runs = []

if st.sidebar.button("🚀 Chạy Fan-Out"):
    # Tạo danh sách truy vấn
    if input_mode == "Truy vấn đơn":
        lookups = [user_query.strip()] if user_query.strip() else []
    else:
        lookups = [q.strip() for q in bulk_text.splitlines() if q.strip()]

    if not lookups:
        st.warning("⚠️ Vui lòng nhập ít nhất một truy vấn.")
        st.stop()

    all_rows, run_summaries, errors = [], [], []

    status = st.status("🔄 Đang xử lý truy vấn…", expanded=True)
    progress = st.progress(0)
    total = len(lookups)

    for i, q in enumerate(lookups, start=1):
        try:
            details, expanded, raw = generate_fanout(q, mode)
            run_summaries.append({
                "Truy vấn gốc": q,
                "Số lượng mục tiêu": details.get("target_query_count"),
                "Giải thích": details.get("reasoning_for_count", "")
            })
            for obj in expanded:
                all_rows.append({
                    "Truy vấn gốc": q,
                    "Truy vấn mở rộng": obj.get("query", ""),
                    "Loại": obj.get("type", ""),
                    "Ý định người dùng": obj.get("user_intent", ""),
                    "Giải thích": obj.get("reasoning", ""),
                    "Định dạng": obj.get("routing_format", ""),
                    "Lý do định dạng": obj.get("format_reason", "")
                })
            status.write(f"✅ Hoàn tất: **{q}** — tạo {len(expanded)} truy vấn.")
        except json.JSONDecodeError as e:
            msg = f"❌ Lỗi JSON khi xử lý '{q}': {e}"
            status.write(msg)
            errors.append({"Truy vấn": q, "Lỗi": str(e)})
        except Exception as e:
            msg = f"❌ Lỗi khác khi xử lý '{q}': {e}"
            status.write(msg)
            errors.append({"Truy vấn": q, "Lỗi": str(e)})

        progress.progress(i / total)

    status.update(label="✅ Hoàn tất toàn bộ.", state="complete")

    # Kết quả
    if all_rows:
        df = pd.DataFrame(all_rows)
        st.subheader("📊 Kết quả Fan-Out")
        st.dataframe(df, use_container_width=True, height=(min(len(df), 20) + 1) * 35 + 3)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Tải về CSV",
            data=csv,
            file_name="qforia_output.csv",
            mime="text/csv"
        )
    else:
        st.warning("Không có truy vấn mở rộng nào được tạo ra.")

    if run_summaries:
        st.markdown("---")
        st.subheader("🧠 Tóm tắt kế hoạch sinh truy vấn")
        st.dataframe(pd.DataFrame(run_summaries), use_container_width=True)

    if errors:
        st.markdown("---")
        st.subheader("⚠️ Lỗi trong quá trình xử lý")
        st.dataframe(pd.DataFrame(errors), use_container_width=True)
