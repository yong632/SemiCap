import streamlit as st
import plotly.express as px
import pandas as pd
import yfinance as yf

# 1. Page Configuration (Global Setting)
st.set_page_config(layout="wide", page_title="US Semi & AI Market Map")
st.title("📟 Noah's Semiconductor Stock Map")

# 2. [Horizontal Period Selector UI] - "Return" text completely removed
st.write("### ⏱️ Select Time Period")
period_options = ["1 Year", "1 Month", "1 Week", "Daily"]
selected_display_period = st.radio(
    "Select time range to view:",
    options=period_options,
    index=3,  # Default: 'Daily'
    horizontal=True,
    label_visibility="collapsed"
)

# 💡 Mapping UI display names back to original DataFrame columns for backend stability
period_mapping = {
    "1 Year": "1 Year Return",
    "1 Month": "1 Month Return",
    "1 Week": "1 Week Return",
    "Daily": "Daily Return"
}
selected_period = period_mapping[selected_display_period]

st.subheader(f"📌 Current Period: {selected_display_period}")
st.markdown("---")

# 💡 [안정성 패치 1] 환율 정보는 1시간(ttl=3600) 동안 불러오지 않도록 차단하여 API 피로도를 최소화합니다.
@st.cache_data(ttl=3600)
def get_usd_krw_rate():
    try:
        usd_krw_ticker = yf.Ticker("USDKRW=X")
        # 최근 시장 마감 가격 기준 활용
        rate = usd_krw_ticker.history(period="1d")["Close"].iloc[-1]
        return rate
    except Exception:
        return 1400.0  # API 터질 때를 대비한 안전 장치 기본 환율 설정

# 3. Data Pipeline & Financial Calculation Function
@st.cache_data(ttl=600)  # Cache data for 10 minutes
def get_combined_map_data():
    semi_companies = {
        # Semiconductors (Design/AI)
        "NVDA": {"Name": "NVIDIA", "Industry": "Semiconductors (Design/AI)", "Display_Ticker": "NVDA"},
        "AVGO": {"Name": "Broadcom", "Industry": "Semiconductors (Design/AI)", "Display_Ticker": "AVGO"},
        "AMD": {"Name": "AMD", "Industry": "Semiconductors (Design/AI)", "Display_Ticker": "AMD"},
        
        # Semiconductors (Memory)
        "MU": {"Name": "Micron Technology", "Industry": "Semiconductors (Memory)", "Display_Ticker": "MU"},
        "WDC": {"Name": "Western Digital", "Industry": "Semiconductors (Memory)", "Display_Ticker": "WDC"},
        "SDSK": {"Name": "Sandisk Corp", "Industry": "Semiconductors (Memory)", "Display_Ticker": "SNDK"},
        "005930.KS": {"Name": "Samsung Electronics", "Industry": "Semiconductors (Memory)", "Display_Ticker": "SEC"},
        "000660.KS": {"Name": "SK Hynix", "Industry": "Semiconductors (Memory)", "Display_Ticker": "HYNIX"},
        
        # Semiconductors (IDM & Analog)
        "INTC": {"Name": "Intel", "Industry": "Semiconductors (IDM)", "Display_Ticker": "INTC"},
        "ADI": {"Name": "Analog Devices", "Industry": "Semiconductors (Analog)", "Display_Ticker": "ADI"},
        "TXN": {"Name": "Texas Instruments", "Industry": "Semiconductors (Analog)", "Display_Ticker": "TXN"},
        
        # Semiconductor Equipment
        "ASML": {"Name": "ASML Holding", "Industry": "Semiconductor Equipment", "Display_Ticker": "ASML"},
        "LRCX": {"Name": "Lam Research", "Industry": "Semiconductor Equipment", "Display_Ticker": "LRCX"},
        "AMAT": {"Name": "Applied Materials", "Industry": "Semiconductor Equipment", "Display_Ticker": "AMAT"},
        "KLAC": {"Name": "KLA Corporation", "Industry": "Semiconductor Equipment", "Display_Ticker": "KLAC"},
        
        # AI Server Infrastructure
        "DELL": {"Name": "Dell Technologies", "Industry": "AI Server Hardware", "Display_Ticker": "DELL"},
        "HPE": {"Name": "Hewlett Packard Enterprise", "Industry": "AI Server Hardware", "Display_Ticker": "HPE"}
    }
    
    tickers = list(semi_companies.keys())
    
    progress_bar = st.progress(0, text="🔄 Synchronizing live financial pipeline... Please wait.")
    
    try:
        # 캐싱된 안정적인 환율 가져오기
        usd_krw_rate = get_usd_krw_rate()
        
        # 💡 [안정성 패치 2] 통으로 크게 찌르는 yf.download가 막힐 때를 대비하여 개별 Ticker 히스토리 연산 안전 구조로 전환
        stock_list = []
        total_tickers = len(tickers)
        
        for idx, ticker in enumerate(tickers):
            try:
                progress_percent = int(((idx + 1) / total_tickers) * 100)
                progress_bar.progress(progress_percent, text=f"📊 Fetching data matrix for {ticker}...")
                
                t = yf.Ticker(ticker)
                
                # 시가총액 정보
                market_cap = t.info.get("marketCap", 0)
                if market_cap == 0:
                    continue
                
                # 원화 환율 보정
                if ticker.endswith(".KS"):
                    market_cap = market_cap / usd_krw_rate
                
                # 과거 1년치 주가 이력만 타겟팅 추출하여 API 로드 경량화
                hist = t.history(period="1y")["Close"].dropna()
                if len(hist) < 2:
                    continue
                    
                current_price = hist.iloc[-1]
                prev_day_price = hist.iloc[-2]
                
                prev_week_price = hist.iloc[-6] if len(hist) >= 6 else hist.iloc[0]
                prev_month_price = hist.iloc[-22] if len(hist) >= 22 else hist.iloc[0]
                prev_year_price = hist.iloc[0]
                
                daily_return = round(((current_price - prev_day_price) / prev_day_price) * 100, 2)
                weekly_return = round(((current_price - prev_week_price) / prev_week_price) * 100, 2)
                monthly_return = round(((current_price - prev_month_price) / prev_month_price) * 100, 2)
                yearly_return = round(((current_price - prev_year_price) / prev_year_price) * 100, 2)
                
                display_ticker = semi_companies[ticker]["Display_Ticker"]
                
                stock_list.append({
                    "Ticker": display_ticker,
                    "Name": semi_companies[ticker]["Name"],
                    "Industry": semi_companies[ticker]["Industry"],
                    "MarketCap": market_cap / 1e9,
                    "Daily Return": daily_return,
                    "1 Week Return": weekly_return,
                    "1 Month Return": monthly_return,
                    "1 Year Return": yearly_return
                })
            except Exception:
                continue
                
        progress_bar.empty()
        
        if not stock_list:
            raise ValueError("All API connections rate-limited by provider temporarily.")
            
        df_result = pd.DataFrame(stock_list)
        return df_result.sort_values(by="MarketCap", ascending=False)
        
    except Exception as e:
        progress_bar.empty()
        raise e

# Execute Data Pipeline
try:
    df = get_combined_map_data()
except Exception as e:
    st.error(f"An error occurred during data compilation: Too Many Requests. Rate limited. Try after a while.")
    st.stop()

# 4. Filter Bypass
filtered_df = df.copy()

# Dynamic Data Mapping based on User Selector
filtered_df["Selected_Return"] = filtered_df[selected_period]

# Build Custom Label Formats
filtered_df["Label_Text"] = filtered_df.apply(
    lambda r: f"<b>{r['Ticker']}</b><br>{'+' if r['Selected_Return'] > 0 else ''}{r['Selected_Return']:.2f}%", axis=1
)

# 5. Plotly Treemap Generation
fig = px.treemap(
    filtered_df,
    path=["Industry", "Ticker"],
    values="MarketCap",
    color="Selected_Return",
    color_continuous_scale=[[0.0, "#e63946"], [0.5, "#f7f7f7"], [1.0, "#2a9d8f"]],
    color_continuous_midpoint=0,
    hover_data={"MarketCap": ":$.1fB", "Selected_Return": ":+.2f%"}
)

fig.update_traces(
    texttemplate="%{customdata[2]}",  
    customdata=filtered_df[["MarketCap", "Selected_Return", "Label_Text"]].values,
    textposition="middle center",
    selector=dict(type="treemap")
)

fig.update_layout(
    margin=dict(t=10, l=10, r=10, b=10),
    height=600,
    coloraxis_colorbar=dict(
        orientation="h",
        yanchor="top",
        y=-0.05,
        xanchor="center",
        x=0.5,
        len=0.9,
        thickness=15
    )
)
st.plotly_chart(fig, use_container_width=True)

# 6. Data Grid Display
st.write("### 📋 Real-Time Portfolio Performance Metrics (Sorted by MarketCap)")
st.dataframe(
    filtered_df[["Ticker", "Name", "Industry", "MarketCap", selected_period]]
    .sort_values(by="MarketCap", ascending=False)
    .reset_index(drop=True),
    use_container_width=True
)
