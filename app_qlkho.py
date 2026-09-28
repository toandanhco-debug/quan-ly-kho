import io
import json
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Quản Lý Kho Vật Tư Điện & Thiết Bị (Cloud)", layout="wide"
)

# --- ĐƯỜNG DẪN KẾT NỐI GOOGLE SHEETS WEB APP CỦA BẠN ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzrMRNJ5cPoFpOGFvK3vP3Q4RCurkTJQtIfxH7qkrEjKF5ZF8CYOfNfFrOatGoimGEwWg/exec"


# Hàm tải dữ liệu từ Google Sheets
def load_data():
  try:
    response = requests.get(f"{WEB_APP_URL}?action=getData")
    data = response.json()
    if len(data) > 1:
      headers = data[0]
      rows = data[1:]
      df = pd.DataFrame(rows, columns=headers)
      df["Tồn Kho"] = pd.to_numeric(df["Tồn Kho"], errors="coerce").fillna(0)
      return df
    else:
      return pd.DataFrame(
          columns=[
              "Mã VT",
              "Tên Vật Tư / Thiết Bị",
              "Phân Loại",
              "Đơn Vị",
              "Tồn Kho",
              "Khu Vực Lưu Trữ",
          ]
      )
  except Exception as e:
    st.error(f"Lỗi kết nối đến Google Sheets: {e}")
    return pd.DataFrame(
        columns=[
            "Mã VT",
            "Tên Vật Tư / Thiết Bị",
            "Phân Loại",
            "Đơn Vị",
            "Tồn Kho",
            "Khu Vực Lưu Trữ",
        ]
    )


# Hàm cập nhật số lượng hoặc khu vực
def update_row_in_sheet(ma_vt, new_ton_kho, new_khu_vuc=None):
  payload = {
      "action": "update",
      "ma_vt": ma_vt,
      "ton_kho": int(new_ton_kho),
      "khu_vuc": new_khu_vuc,
  }
  try:
    requests.post(WEB_APP_URL, json=payload)
  except Exception as e:
    st.error(f"Lỗi cập nhật: {e}")


# Hàm thêm vật tư mới
def add_row_to_sheet(ma_vt, ten_vt, phan_loai, don_vi, ton_kho, khu_vuc):
  payload = {
      "action": "add",
      "ma_vt": ma_vt,
      "ten_vt": ten_vt,
      "phan_loai": phan_loai,
      "don_vi": don_vi,
      "ton_kho": int(ton_kho),
      "khu_vuc": khu_vuc,
  }
  try:
    response = requests.post(WEB_APP_URL, json=payload)
    return response.json().get("status") == "success"
  except Exception as e:
    st.error(f"Lỗi thêm mới: {e}")
    return False


# Tải dữ liệu vào session state
if "inventory" not in st.session_state:
  st.session_state.inventory = load_data()

# --- THANH ĐIỀU HƯỚNG (SIDEBAR) ---
st.sidebar.title("⚡ Quản Lý Kho (Cloud)")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "📂 Chọn tính năng:",
    [
        "📦 Tra cứu & Nhập/Xuất Kho",
        "🚚 Chuyển Khu Vực Thiết Bị",
        "➕ Thêm Vật Tư / Thiết Bị Mới",
    ],
)

# ==========================================
# TÍNH NĂNG 1: TRA CỨU & NHẬP / XUẤT KHO
# ==========================================
if menu == "📦 Tra cứu & Nhập/Xuất Kho":
  st.title("📦 Tra Cứu Tồn Kho & Giao Dịch (Đồng Bộ Google Sheets)")

  if st.button("🔄 Làm mới dữ liệu từ Google Sheets"):
    st.session_state.inventory = load_data()
    st.rerun()

  st.subheader("🔍 Tra cứu vật tư / thiết bị")
  search_query = st.text_input(
      "Nhập tên hoặc mã vật tư cần tìm kiếm:",
      placeholder="Ví dụ: Cáp, Aptomat, Máy hàn...",
  )

  df = st.session_state.inventory
  if search_query and not df.empty:
    mask = (
        df["Tên Vật Tư / Thiết Bị"]
        .str.contains(search_query, case=False, na=False)
        | df["Mã VT"].str.contains(search_query, case=False, na=False)
        | df["Khu Vực Lưu Trữ"].str.contains(search_query, case=False, na=False)
    )
    filtered_df = df[mask]
  else:
    filtered_df = df

  st.dataframe(filtered_df, use_container_width=True, hide_index=True)

  st.divider()

  st.subheader("🔄 Thực Hiện Giao Dịch Nhập / Xuất Kho")
  if not st.session_state.inventory.empty:
    with st.form("transaction_form"):
      col1, col2, col3 = st.columns(3)

      with col1:
        trans_type = st.selectbox(
            "Chọn loại giao dịch", ["Nhập kho (+)", "Xuất kho (-)"]
        )

      with col2:
        item_code = st.selectbox(
            "Chọn Mã Vật Tư / Thiết Bị", st.session_state.inventory["Mã VT"]
        )

      with col3:
        quantity = st.number_input(
            "Số lượng giao dịch", min_value=1, value=1, step=1
        )

      submit_button = st.form_submit_button(
          label="Xác nhận và Cập nhật kho", use_container_width=True
      )

      if submit_button:
        row = st.session_state.inventory[
            st.session_state.inventory["Mã VT"] == item_code
        ].iloc[0]
        current_stock = int(row["Tồn Kho"])
        item_name = row["Tên Vật Tư / Thiết Bị"]

        if trans_type == "Nhập kho (+)":
          new_stock = current_stock + quantity
          update_row_in_sheet(item_code, new_stock)
          st.success(
              f"✅ Nhập kho thành công: +{quantity} cho [{item_code}]"
              f" {item_name}!"
          )
          st.session_state.inventory = load_data()
          st.rerun()
        else:
          if current_stock >= quantity:
            new_stock = current_stock - quantity
            update_row_in_sheet(item_code, new_stock)
            st.success(
                f"✅ Xuất kho thành công: -{quantity} cho [{item_code}]"
                f" {item_name}!"
            )
            st.session_state.inventory = load_data()
            st.rerun()
          else:
            st.error(
                f"❌ Lỗi: Tồn kho không đủ! (Hiện chỉ còn {current_stock})"
            )

  st.divider()
  st.subheader("📥 Xuất dữ liệu báo cáo")


  def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="TonKho")
    return output.getvalue()


  excel_data = to_excel(st.session_state.inventory)
  st.download_button(
      label="Tải xuống danh sách tồn kho hiện tại (File Excel chuẩn)",
      data=excel_data,
      file_name="bao_cao_ton_kho_thiet_bi_dien.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
      use_container_width=True,
  )

# ==========================================
# TÍNH NĂNG 2: CHUYỂN KHU VỰC THIẾT BỊ
# ==========================================
elif menu == "🚚 Chuyển Khu Vực Thiết Bị":
  st.title("🚚 Điều Chuyển Thiết Bị Giữa Các Khu Vực")
  st.markdown("Chọn thiết bị cần chuyển và nhập tên khu vực đích đến mới.")

  if not st.session_state.inventory.empty:
    with st.form("transfer_form"):
      transfer_item = st.selectbox(
          "Chọn Mã & Tên Thiết Bị Cần Chuyển",
          st.session_state.inventory["Mã VT"]
          + " - "
          + st.session_state.inventory["Tên Vật Tư / Thiết Bị"],
      )
      new_location = st.text_input(
          "Khu vực đích đến mới", placeholder="Ví dụ: Công trường B, Kho tổng..."
      )

      submit_transfer = st.form_submit_button(
          label="Xác nhận chuyển khu vực", use_container_width=True
      )

      if submit_transfer:
        if not new_location.strip():
          st.warning("⚠️ Vui lòng nhập tên khu vực đến mới!")
        else:
          item_code_selected = transfer_item.split(" - ")[0]
          row = st.session_state.inventory[
              st.session_state.inventory["Mã VT"] == item_code_selected
          ].iloc[0]
          current_stock = int(row["Tồn Kho"])

          update_row_in_sheet(
              item_code_selected, current_stock, new_location.strip()
          )
          st.success(
              f"🎉 Đã chuyển thiết bị [{item_code_selected}] sang khu vực:"
              f" {new_location} thành công!"
          )
          st.session_state.inventory = load_data()
  else:
    st.info("Hiện chưa có thiết bị nào trong kho.")

# ==========================================
# TÍNH NĂNG 3: THÊM VẬT TƯ / THIẾT BỊ MỚI
# ==========================================
elif menu == "➕ Thêm Vật Tư / Thiết Bị Mới":
  st.title("➕ Thêm Mới Vật Tư Ngành Điện & Thiết Bị")
  st.markdown("Dữ liệu sẽ được lưu thẳng lên Google Sheets chung.")

  with st.form("add_item_form"):
    new_code = st.text_input("Mã Vật Tư / Thiết Bị (Ví dụ: VT003)")
    new_name = st.text_input("Tên Vật Tư / Thiết Bị")
    new_category = st.selectbox(
        "Phân Loại", ["Vật tư ngành điện", "Máy móc thiết bị"]
    )
    new_unit = st.text_input("Đơn vị tính (Ví dụ: Mét, Cái, Bộ)")
    new_stock = st.number_input(
        "Số lượng tồn kho ban đầu", min_value=0, value=0, step=1
    )
    new_location = st.text_input(
        "Khu vực lưu trữ ban đầu",
        value="Kho Tổng",
        placeholder="Ví dụ: Kho Tổng, Công trường A...",
    )

    submit_add = st.form_submit_button(
        label="Thêm vào hệ thống kho", use_container_width=True
    )

    if submit_add:
      if not new_code or not new_name or not new_unit or not new_location:
        st.warning("⚠️ Vui lòng điền đầy đủ các thông tin!")
      else:
        success = add_row_to_sheet(
            new_code,
            new_name,
            new_category,
            new_unit,
            new_stock,
            new_location,
        )
        if success:
          st.success(
              f"🎉 Đã thêm thành công vật tư [{new_code}] lên Google Sheets!"
          )
          st.session_state.inventory = load_data()
        else:
          st.error(f"❌ Lỗi: Không thể thêm mới (Có thể mã VT đã tồn tại)!")