import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="기업 성장 예측기", layout="wide")
st.title("📈 시가총액 & 주가 기반 기업 성장 예측 프로그램 By Lee bros ")

def compute_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(window=period).mean()
    ma_down = down.rolling(window=period).mean()
    rs = ma_up / ma_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_technical_conditions_with_score(df):
    result = []
    score = 0

    price_range = df['Close'].rolling(window=20).max() - df['Close'].rolling(window=20).min()
    box_condition = price_range.iloc[-1] < (df['Close'].mean() * 0.05)
    vol_trend = df['Volume'].tail(10).mean() > df['Volume'].tail(30).mean()
    if box_condition and vol_trend:
        result.append("📌 조건 1: ✅ 거래량 서서히 증가 + 박스권 (매집 가능성 있음)")
        score += 1
    else:
        result.append("📌 조건 1: ❌ 거래량/가격 패턴 불일치")

    lows = df['Low'].rolling(window=3).min()
    if lows.tail(5).is_monotonic_increasing:
        result.append("📌 조건 2: ✅ 저점이 계속 높아지는 상승 삼각형 패턴")
        score += 1
    else:
        result.append("📌 조건 2: ❌ 저점 상승 패턴 아님")

    ma5 = df['Close'].rolling(window=5).mean()
    ma20 = df['Close'].rolling(window=20).mean()
    ma60 = df['Close'].rolling(window=60).mean()
    if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
        result.append("📌 조건 3: ✅ 이평선 정배열 시작 (골든 크로스 가능)")
        score += 1
    else:
        result.append("📌 조건 3: ❌ 이평선 정배열 아님")

    last3 = df.tail(3)
    close_std = df['Close'].std()
    small_bull = all(
        (last3['Close'].iloc[i] > last3['Open'].iloc[i]) and
        ((last3['Close'].iloc[i] - last3['Open'].iloc[i]) < (close_std / 2))
        for i in [0, 1])
    big_bull = (last3['Close'].iloc[2] > last3['Open'].iloc[2]) and \
               ((last3['Close'].iloc[2] - last3['Open'].iloc[2]) > close_std)
    if small_bull and big_bull:
        result.append("📌 조건 4: ✅ 돌파 직전 캔들 패턴 (작은 양봉 + 장대양봉)")
        score += 1
    else:
        result.append("📌 조건 4: ❌ 캔들 패턴 부합하지 않음")

    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    signal = macd.ewm(span=9, adjust=False).mean()
    rsi = compute_rsi(df['Close'])
    macd_cross = macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]
    rsi_bounce = (40 <= rsi.iloc[-1] <= 50) and (rsi.iloc[-1] > rsi.iloc[-2])
    if macd_cross or rsi_bounce:
        result.append("📌 조건 5: ✅ MACD 골든크로스 또는 RSI 반등 신호")
        score += 1
    else:
        result.append("📌 조건 5: ❌ 기술지표 상승 신호 없음")

    recent_high = df['Close'].rolling(window=60).max().iloc[-1]
    near_resistance = df['Close'].iloc[-1] >= recent_high * 0.95
    vol_up = df['Volume'].tail(10).mean() > df['Volume'].tail(30).mean()
    if near_resistance and vol_up and (macd_cross or rsi_bounce):
        result.append("📌 조건 6: ✅ 가격·거래량·기술지표 동시 정렬 (급등 전조 가능)")
        score += 1
    else:
        result.append("📌 조건 6: ❌ 조건 미충족")

    result.append(f"🔢 종합 점수: {score} / 6")
    return result, score

company_input = st.text_input("🔍 분석할 기업명을 입력하세요 (예: 삼성전자, Apple, 테슬라 등)", value="삼성전자")

def company_name_to_ticker(name):
    manual_map = {
        "삼성전자": "005930.KS",
        "현대차": "005380.KS",
        "LG에너지솔루션": "373220.KQ",
        "카카오": "035720.KQ",
        "네이버": "035420.KQ",
        "SK하이닉스": "000660.KS",
        "애플": "AAPL",
        "마이크로소프트": "MSFT",
        "테슬라": "TSLA",
        "구글": "GOOGL",
        "알파벳": "GOOGL",
        "아마존": "AMZN",
        "엔비디아": "NVDA",
    }
    if name in manual_map:
        return manual_map[name]
    return None

ticker_input = company_name_to_ticker(company_input)

if ticker_input:
    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=365 * 5)
        stock = yf.Ticker(ticker_input)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            st.warning("📉 데이터를 찾을 수 없습니다. 올바른 티커를 입력했는지 확인해보세요.")
        else:
            info = stock.info
            market_cap = info.get("marketCap", None)
            company_name = info.get("shortName", company_input)

            st.subheader(f"📊 {company_name} ({ticker_input}) 시가총액 및 주가 분석")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("💰 현재 시가총액", f"${market_cap/1e9:.2f}B" if market_cap else "N/A")
            with col2:
                st.metric("📅 분석기간", f"{start_date.date()} ~ {end_date.date()}")

            st.markdown("### 📉 주가 추이")
            fig = px.line(hist, x=hist.index, y='Close',
                          labels={'Close': '종가', 'index': '날짜'},
                          title="과거 주가")
            fig.update_layout(xaxis_title="날짜", yaxis_title="주가 ($)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            cagr = ((end_price / start_price) ** (1 / 5) - 1) * 100

            st.markdown("### 📈 성장 분석")
            st.success(f"📌 최근 5년 간 연평균 성장률(CAGR): **{cagr:.2f}%**")

            if market_cap:
                future_5y_cap = market_cap * ((1 + cagr / 100) ** 5)
                st.markdown("### 🔮 성장 예측")
                st.info(f"예상 5년 후 시가총액 (단순 예측): **${future_5y_cap/1e9:.2f}B**")

            st.markdown("### 🧐 그래서 이 주식을 사야 할까?")
            recommendation = "❓ 판단 보류"
            if cagr > 10:
                if market_cap and market_cap < 1e11:
                    recommendation = "✅ 매수 고려 가능 (고성장 + 중소형 시총)"
                else:
                    recommendation = "🟡 성장성은 좋지만 시총이 이미 큼 (안정적)"
            elif cagr > 0:
                recommendation = "⚠️ 성장은 있지만 제한적"
            else:
                recommendation = "❌ 최근 5년간 주가 하락 - 투자 신중 필요"
            st.subheader(recommendation)
            st.caption("※ 이 판단은 단순 참고용이며, 실제 투자 결정은 본인의 책임입니다.")

            st.markdown("### 🧐 주식 떡상 지표 분석 6가지 조건 비교 (점수화 포함)")
            tech_analysis_results, tech_score = analyze_technical_conditions_with_score(hist.tail(60))
            for line in tech_analysis_results[:-1]:
                st.write(line)

            st.progress(tech_score / 6)
            st.metric(label="종합 기술적 조건 점수", value=f"{tech_score} / 6")

            if tech_score >= 4:
                st.success(f"✅ 총 점수 {tech_score}점: 강한 상승 신호!")
            elif tech_score >= 2:
                st.warning(f"⚠️ 총 점수 {tech_score}점: 상승 가능성 있음")
            else:
                st.info(f"ℹ️ 총 점수 {tech_score}점: 신중한 관찰 필요")

    except Exception as e:
        st.error(f"에러가 발생했습니다: {e}")
else:
    st.error("해당 기업명을 티커로 변환할 수 없습니다. 다른 이름이나 영어명을 시도해보세요.")
