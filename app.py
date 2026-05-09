from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
from google import genai # Đã bổ sung thư viện gọi AI

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return send_file("adidas-dss.html")

# ==============================
# 📊 LOAD DATA
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, "Adidas_chuanhoa.xlsx")

df = pd.read_excel(file_path, header=9)
df.columns = ['Retailer','Retailer ID','Invoice Date','Region','State','City',
               'Product','Price per Unit','Units Sold','Total Sales',
               'Operating Profit','Operating Margin','Sales Method']
df['Invoice Date'] = pd.to_datetime(df['Invoice Date'])

# ==============================
# 📋 TÍNH TOÁN DỮ LIỆU THỰC TẾ
# ==============================
total_revenue = df['Total Sales'].sum()
total_profit  = df['Operating Profit'].sum()
total_units   = df['Units Sold'].sum()
avg_margin    = df['Operating Margin'].mean()

y2021 = df[df['Invoice Date'].dt.year == 2021]
y2020 = df[df['Invoice Date'].dt.year == 2020]

# Tháng 12/2021
dec21     = df[(df['Invoice Date'].dt.year==2021) & (df['Invoice Date'].dt.month==12)]
dec_rev   = dec21['Total Sales'].sum()
dec_units = dec21['Units Sold'].sum()
dec_profit= dec21['Operating Profit'].sum()
dec_price = dec_rev / dec_units
dec_cost_pu = (dec_rev - dec_profit) / dec_units
dec_ln_pu   = dec_profit / dec_units

# Kịch bản TH3
kb1_rev = dec_price * 0.95 * dec_units * 1.10
kb2_rev = dec_price * 1.00 * dec_units * 1.15
kb3_rev = dec_price * 1.05 * dec_units * 0.92

# Goal Seek TH4
target_profit = 35_000_000
units_needed  = target_profit / dec_ln_pu
max_capacity  = 200_000

# Khu vực
reg_stats = df.groupby('Region').agg(
    Rev=('Total Sales','sum'), Units=('Units Sold','sum'),
    Profit=('Operating Profit','sum')).reset_index()
reg_stats['Rev_pu']  = reg_stats['Rev'] / reg_stats['Units']
reg_stats['Cost_pu'] = (reg_stats['Rev'] - reg_stats['Profit']) / reg_stats['Units']
reg_stats['LN_pu']   = reg_stats['Profit'] / reg_stats['Units']
reg_stats['CostPct'] = reg_stats['Cost_pu'] / reg_stats['Rev_pu'] * 100

# Sản phẩm
prod_stats = df.groupby('Product').agg(
    Rev=('Total Sales','sum'), Units=('Units Sold','sum'),
    Profit=('Operating Profit','sum')).sort_values('Rev', ascending=False).reset_index()
prod_stats['Margin'] = prod_stats['Profit'] / prod_stats['Rev'] * 100
prod_stats['Share']  = prod_stats['Rev'] / total_revenue * 100

# Kênh bán
meth_stats = df.groupby('Sales Method').agg(
    Rev=('Total Sales','sum'), Units=('Units Sold','sum'),
    Profit=('Operating Profit','sum')).sort_values('Rev', ascending=False).reset_index()
meth_stats['Margin'] = meth_stats['Profit'] / meth_stats['Rev'] * 100
meth_stats['Rev_pu'] = meth_stats['Rev'] / meth_stats['Units']

# TH1 Dự báo
monthly_2021 = y2021.groupby(y2021['Invoice Date'].dt.to_period('M'))['Total Sales'].sum().values
growth_rates = [(monthly_2021[i]-monthly_2021[i-1])/monthly_2021[i-1] for i in range(1,12)]
g = np.mean(growth_rates)
forecast = {f"T{t}/2022": int(dec_rev * (1+g)**t) for t in range(1,7)}


# ==============================
# 🎯 CÂU TRẢ LỜI CHUẨN THEO ĐỒ ÁN
# ==============================
def answer_yeu_to_anh_huong():
    return (
        "📊 Yếu tố ảnh hưởng đến doanh thu Adidas (TH2 – Hồi quy đa biến)\n\n"
        "Dựa trên mô hình Multiple Regression với R² = 99,67%, cả giá bán và sản lượng "
        "đều tác động đến doanh thu, nhưng mức độ không như nhau:\n\n"
        "• Giá bán – t-Stat = 33,8 ← mạnh hơn\n"
        "  Tăng 50% giá → doanh thu tăng ~29,8 triệu USD\n\n"
        "• Sản lượng – t-Stat = 20,77\n"
        "  Tăng 50% sản lượng → doanh thu tăng ~23,1 triệu USD\n\n"
        "Phương trình: DT = −56.910.312 + 148.799×Giá + 385×Sản lượng\n\n"
        "✅ Kết luận: Giá bán là yếu tố ảnh hưởng mạnh hơn đến doanh thu "
        "ở cấp độ chiến lược (phân tích tổng hợp theo tháng). Tuy nhiên, "
        "trên thực tế cần duy trì cả hai: giữ giá ổn định và gia tăng sản lượng "
        "để tối ưu hóa doanh thu bền vững."
    )

def answer_tang_sl_hay_gia():
    return (
        "📊 Nên tăng sản lượng hay tăng giá? (TH2 + TH3)\n\n"
        "Mặc dù hồi quy cho thấy giá bán có t-Stat cao hơn (33,8 vs 20,77), "
        "kết quả phân tích kịch bản tháng 12/2021 chỉ ra:\n\n"
        f"• Kịch bản 1 – Giá giảm 5%, SL tăng 10%: {kb1_rev/1e6:.2f}M USD\n"
        f"• Kịch bản 2 – Giữ giá, SL tăng 15%: {kb2_rev/1e6:.2f}M USD ← TỐT NHẤT\n"
        f"• Kịch bản 3 – Giá tăng 5%, SL giảm 8%: {kb3_rev/1e6:.2f}M USD\n\n"
        "Tăng giá khiến sản lượng giảm → doanh thu không tối ưu (trade-off).\n\n"
        "✅ Kết luận: Duy trì giá ổn định và gia tăng sản lượng thông qua "
        "mở rộng kênh phân phối, đẩy mạnh marketing và các chương trình kích cầu "
        "là chiến lược tối ưu nhất. Việc tăng giá tùy tiện có thể xói mòn "
        "biên lợi nhuận và định vị thương hiệu."
    )

def answer_kenh_ban():
    instore = meth_stats[meth_stats['Sales Method']=='In-store'].iloc[0]
    online  = meth_stats[meth_stats['Sales Method']=='Online'].iloc[0]
    outlet  = meth_stats[meth_stats['Sales Method']=='Outlet'].iloc[0]
    return (
        "📊 Hiệu quả các kênh bán hàng Adidas 2020–2021\n\n"
        f"• In-store: DT {instore['Rev']/1e6:.1f}M USD · {instore['Units']/1e3:.0f}K SP · "
        f"Biên LN {instore['Margin']:.1f}% · DT/SP ${instore['Rev_pu']:.0f}\n\n"
        f"• Outlet: DT {outlet['Rev']/1e6:.1f}M USD · {outlet['Units']/1e3:.0f}K SP · "
        f"Biên LN {outlet['Margin']:.1f}% · DT/SP ${outlet['Rev_pu']:.0f}\n\n"
        f"• Online: DT {online['Rev']/1e6:.1f}M USD · {online['Units']/1e3:.0f}K SP "
        f"← sản lượng nhiều nhất · Biên LN {online['Margin']:.1f}% ← cao nhất · "
        f"DT/SP ${online['Rev_pu']:.0f}\n\n"
        "✅ Kết luận: In-store dẫn đầu doanh thu (40%), nhưng Online có "
        "biên lợi nhuận cao nhất (38,7%) và sản lượng lớn nhất (809K SP) → "
        "kênh hiệu quả nhất về đơn vị sản phẩm. Khuyến nghị đẩy mạnh đầu tư "
        "mở rộng kênh Online để tối ưu biên lợi nhuận."
    )

def answer_kich_ban():
    return (
        "📊 So sánh 3 kịch bản kinh doanh (TH3 – Scenario Manager)\n\n"
        f"Cơ sở tháng 12/2021: DT {dec_rev/1e6:.2f}M USD · "
        f"Giá TB ${dec_price:.0f} · SL {dec_units:,.0f} SP\n\n"
        f"• Kịch bản 1 – Giá giảm 5%, SL tăng 10%: {kb1_rev/1e6:.2f}M USD\n"
        f"• Kịch bản 2 – Giá giữ nguyên, SL tăng 15%: {kb2_rev/1e6:.2f}M USD ← TỐT NHẤT\n"
        f"• Kịch bản 3 – Giá tăng 5%, SL giảm 8%: {kb3_rev/1e6:.2f}M USD (thấp nhất)\n\n"
        "Kịch bản 3 tuy giá cao hơn nhưng sản lượng giảm mạnh → doanh thu thấp nhất, "
        "thể hiện rõ yếu tố đánh đổi (trade-off) giữa giá và sản lượng.\n\n"
        "✅ Kết luận: Kịch bản 2 tối ưu nhất. Duy trì giá ổn định + tăng sản lượng 15% "
        "thông qua mở rộng kênh phân phối và kích cầu."
    )

def answer_san_pham():
    result = "📊 Phân tích danh mục sản phẩm Adidas 2020–2021\n\n"
    for i, r in prod_stats.iterrows():
        note = ""
        if i == 0: note = " ← Dẫn đầu"
        elif i == 5: note = " ← Thấp nhất, tiềm năng tăng trưởng"
        result += (f"• {r['Product']}: {r['Rev']/1e6:.1f}M USD ({r['Share']:.1f}%) · "
                   f"Biên {r['Margin']:.1f}%{note}\n")
    result += (
        "\n✅ Kết luận:\n"
        "• Men's Street Footwear dẫn đầu (23,2%) → ưu tiên giữ vững và đầu tư.\n"
        "• Women's Apparel đứng thứ 2, biên LN ổn định → tiếp tục phát triển.\n"
        "• Women's Athletic Footwear thấp nhất (11,9%) → tiềm năng đầu tư "
        "marketing để đa dạng hóa doanh thu."
    )
    return result

def answer_solver():
    south = reg_stats[reg_stats['Region']=='South'].iloc[0]
    se    = reg_stats[reg_stats['Region']=='Southeast'].iloc[0]
    return (
        "📊 Tối ưu phân bổ sản lượng theo khu vực (TH5 – Solver LP)\n\n"
        "Ràng buộc: Tổng 2.400.000 SP · Mỗi khu vực ≥ 240.000 SP · Chi phí ≤ 60% DT\n\n"
        "Kết quả Solver (Simplex LP):\n"
        "• Northeast: 240.000 SP (10%) – mức tối thiểu\n"
        "• West: 240.000 SP (10%) – mức tối thiểu\n"
        "• Midwest: 240.000 SP (10%) – mức tối thiểu\n"
        "• Southeast: 268.675 SP (11,2%)\n"
        f"• South: 1.411.325 SP (58,8%) ← Ưu tiên cao nhất\n\n"
        "Tại sao South được ưu tiên?\n"
        f"• South: CP/SP = ${south['Cost_pu']:.0f} · DT/SP = ${south['Rev_pu']:.0f} · "
        f"CP/DT = {south['CostPct']:.1f}% < 60% → không bị ràng buộc\n"
        f"• Southeast: CP/SP = ${se['Cost_pu']:.0f} · DT/SP = ${se['Rev_pu']:.0f} · "
        f"CP/DT = {se['CostPct']:.1f}% > 60% → bị ràng buộc, không thể tăng thêm\n\n"
        "Tổng lợi nhuận tối đa: 360.032.673 USD\n\n"
        "✅ Kết luận: Tập trung logistics và kênh phân phối vào khu vực South, "
        "duy trì mức tối thiểu ở 4 khu vực còn lại để giữ thị phần."
    )

def answer_du_bao():
    lines = "\n".join([f"  • {m}: {v/1e6:.2f}M USD" for m, v in forecast.items()])
    return (
        "📊 Dự báo doanh thu 6 tháng đầu năm 2022 (TH1 – Tăng trưởng lũy kế)\n\n"
        f"Tốc độ tăng trưởng trung bình g = {g*100:.2f}%/tháng\n"
        f"Cơ sở T12/2021: {dec_rev/1e6:.2f}M USD\n"
        "Công thức: DT(t) = DT(0) × (1 + g)^t\n\n"
        f"{lines}\n\n"
        "✅ Kết luận: Doanh thu kỳ vọng vượt mốc 100 triệu USD vào T6/2022. "
        "Doanh nghiệp cần chuẩn bị hàng tồn kho, nhân sự và logistics "
        "cho giai đoạn cao điểm. Cập nhật mô hình định kỳ khi có dữ liệu mới."
    )

def answer_goal_seek():
    return (
        "📊 Xác định sản lượng mục tiêu (TH4 – Goal Seek)\n\n"
        "Mục tiêu lợi nhuận: 35.000.000 USD/tháng\n\n"
        f"Dữ liệu T12/2021:\n"
        f"• Giá bán TB: ${dec_price:.2f}/SP\n"
        f"• Chi phí đơn vị: ${dec_cost_pu:.2f}/SP\n"
        f"• Lợi nhuận/SP: ${dec_ln_pu:.2f}\n\n"
        f"→ Sản lượng cần: {int(units_needed):,} SP/tháng\n"
        f"→ Năng lực tối đa: {max_capacity:,} SP/tháng\n"
        f"→ Đánh giá: KHẢ THI (dư địa {int(max_capacity - units_needed):,} SP)\n\n"
        "✅ Kết luận: Mục tiêu đạt được nhưng khoảng cách với trần không lớn. "
        "Cần kiểm soát chi phí chặt chẽ và tối ưu logistics để nâng biên lợi nhuận, "
        "tránh phụ thuộc hoàn toàn vào việc tăng sản lượng."
    )


# ==============================
# 🔍 KEYWORD MATCHING
# ==============================
def find_canned_answer(q: str):
    q_low = q.lower()

    if any(k in q_low for k in ["yếu tố", "ảnh hưởng", "tác động", "mạnh nhất", "t-stat", "hồi quy", "regression"]):
        return answer_yeu_to_anh_huong()

    if any(k in q_low for k in ["tăng sản lượng hay", "tăng giá hay", "nên làm gì để tăng",
                                  "sl hay giá", "sản lượng hay giá", "chiến lược tăng doanh thu"]):
        return answer_tang_sl_hay_gia()

    if any(k in q_low for k in ["kênh bán", "kênh phân phối", "in-store", "online", "outlet",
                                  "kênh nào hiệu quả", "kênh tốt nhất"]):
        return answer_kenh_ban()

    if any(k in q_low for k in ["kịch bản", "scenario", "kb1", "kb2", "kb3", "tháng 12/2021",
                                  "tối ưu nhất để tăng doanh thu"]):
        return answer_kich_ban()

    if any(k in q_low for k in ["sản phẩm", "men's", "women's", "footwear", "apparel",
                                  "athletic", "danh mục", "tiềm năng nhất"]):
        return answer_san_pham()

    if any(k in q_low for k in ["solver", "khu vực", "phân bổ", "south", "northeast",
                                  "midwest", "southeast", "linear programming", "lp tối ưu"]):
        return answer_solver()

    if any(k in q_low for k in ["dự báo", "2022", "tháng tới", "forecast", "tăng trưởng tháng"]):
        return answer_du_bao()

    if any(k in q_low for k in ["goal seek", "mục tiêu lợi nhuận", "35 triệu", "sản lượng cần",
                                  "191", "lợi nhuận mục tiêu", "khả thi"]):
        return answer_goal_seek()

    return None


# ==============================
# 🤖 AI ENGINE  (Google Gemini)
# ==============================
SYSTEM_PROMPT = f"""Bạn là chuyên gia phân tích DSS cho công ty Adidas tại thị trường Mỹ (2020-2021).
Trả lời bằng tiếng Việt, ngắn gọn, trích dẫn số liệu cụ thể, đưa ra khuyến nghị rõ ràng.

DỮ LIỆU THỰC TẾ:
- Tổng DT: 886,129,459 USD | LN: 325,971,216 USD | SL: 2,212,704 SP | Biên: 41.35%
- 2020: 177.4M USD → 2021: 708.7M USD (+299.5% YoY)

MÔ HÌNH HỒI QUY (TH2, R²=99.67%):
- DT = -56,910,312 + 148,799×Giá + 385×SL
- t-Stat Giá=33.8 (mạnh hơn) | t-Stat SL=20.77
- Tăng 50% giá → +29.8M | Tăng 50% SL → +23.1M

KỊCH BẢN T12/2021 (TH3): KB1=80.36M | KB2=88.43M (tốt nhất) | KB3=74.28M
GOAL SEEK (TH4): cần 191,310 SP để đạt LN 35M/tháng (khả thi)
SOLVER (TH5): South 1,411,325 SP (59%) - LN tối đa 360,032,673 USD
DỰ BÁO 2022 (TH1, g=4.82%): T1=80.6M T2=84.5M T3=88.6M T4=92.8M T5=97.3M T6=102M

KẾT LUẬN CHIẾN LƯỢC: Duy trì giá ổn định + tăng SL Online + tập trung South + đầu tư Men's Street Footwear
"""

def call_ai(question: str) -> str:
    from google import genai
    
    # Mình sẽ dán Key của bạn vào đây
    api_key = "AIzaSyBChTvMmD6Y3gbef1u6j6bDRhM9iFwVLbU" 
    
    if not api_key or "AIzaSy" not in api_key:
        return "⚠️ API Key không hợp lệ."

    try:
        # Khởi tạo client theo chuẩn SDK mới nhất
        client = genai.Client(api_key=api_key)
        
        # Sử dụng model gemini-1.5-flash để ổn định nhất cho bản Free
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=SYSTEM_PROMPT + "\n\nCâu hỏi: " + question
        )
        return response.text
    except Exception as e:
        # Bắt lỗi 429 hoặc 404 để phản hồi rõ ràng cho Lan
        error_msg = str(e)
        if "429" in error_msg:
            return "⚠️ Tài khoản hết lượt dùng Free trong phút này. Hãy đợi 30s hoặc dùng Quick Ask."
        return f"⚠️ Lỗi Gemini API: {error_msg}"
    
# ==============================
# 🎯 MAIN ROUTER
# ==============================
def ask(question: str) -> str:
    canned = find_canned_answer(question)
    if canned:
        return canned
    return call_ai(question)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").strip()
    
    # Ưu tiên dùng câu trả lời từ dữ liệu nội bộ trước (không tốn API)
    canned = find_canned_answer(user_msg) 
    if canned:
        return jsonify({"reply": canned})
    
    # Nếu không có câu trả lời mẫu mới gọi đến Gemini
    return jsonify({"reply": call_ai(user_msg)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
