import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import json

# Configuration
API_URL = "http://localhost:8000/api/v1/analyze"

st.set_page_config(
    page_title="Financial Analyst AI",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Premium Product" Feel
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .advice-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .risk-low { border-left-color: #28a745; }
    .risk-medium { border-left-color: #ffc107; }
    .risk-high { border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# Application Header
st.title("💸 AI Financial Analyst: Virtual CFO")
st.markdown("---")

# Sidebar: Actions
with st.sidebar:
    st.header("📂 Data Input")
    uploaded_file = st.file_uploader("Upload Profit & Loss (CSV)", type=["csv"])
    
    st.markdown("### ⚙️ Controls")
    show_raw_data = st.checkbox("Show Raw Data", value=False)
    
    st.info("💡 Upload a CSV with columns: `date`, `revenue`, `expenses`.")

# Main Logic
if uploaded_file is not None:
    # Processing Spinner
    with st.spinner("🕵️ Detective Analyzing... 🔮 Oracle Predicting... 🎩 Advisor Thinking..."):
        try:
            # 1. Call API
            files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
            response = requests.post(API_URL, files=files)
            
            if response.status_code == 200:
                result = response.json()
                data = result["data"]
                
                # --- SECTION 1: EXECUTIVE DASHBOARD ---
                st.subheader("1️⃣ Executive Dashboard")
                metrics = data["financial_metrics"]
                
                # KPIs
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Revenue", f"${metrics['summary_revenue']:,.0f}")
                c2.metric("Total Profit", f"${metrics['summary_profit']:,.0f}")
                c3.metric("Avg Margin", f"{metrics['avg_margin']}%")
                
                # Detective Summary
                st.markdown(f"**🔍 Detective's Insight:** {data['detective']['summary']}")

                # Charts
                # Prepare Aggregated Data for Charts
                monthly_data = metrics["monthly_data"]
                dates = [m["month"] for m in monthly_data]
                rev = [m["revenue"] for m in monthly_data]
                exp = [m["expenses"] for m in monthly_data]
                profit = [m["net_profit"] for m in monthly_data]

                tab1, tab2 = st.tabs(["💰 Revenue & Expenses", "📉 Profit Trend"])
                
                with tab1:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name='Revenue', x=dates, y=rev, marker_color='#007bff'))
                    fig.add_trace(go.Bar(name='Expenses', x=dates, y=exp, marker_color='#dc3545'))
                    fig.update_layout(barmode='group', title="Monthly Financials")
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=dates, y=profit, mode='lines+markers', name='Net Profit', line=dict(color='#28a745', width=3)))
                    fig2.add_shape(type="line", x0=dates[0], y0=0, x1=dates[-1], y1=0, line=dict(color="gray", width=1, dash="dash"))
                    st.plotly_chart(fig2, use_container_width=True)

                # --- SECTION 2: FORECAST WAR ROOM ---
                st.markdown("---")
                st.subheader("2️⃣ Forecast War Room (Oracle)")
                
                forecast = data["forecast"]
                scenarios = forecast["scenarios"]
                
                # Scenario Selector
                selected_scenario_name = st.radio("Select Scenario:", ["Conservative", "Neutral", "Aggressive"], index=1, horizontal=True)
                
                # Find selected scenario data
                scenario_data = next((s for s in scenarios if s["scenario_name"] == selected_scenario_name), None)
                
                if scenario_data:
                    st.markdown(f"**Assumption:** {scenario_data['assumptions']['growth']} | **Volatility:** {scenario_data['assumptions']['volatility']}")
                    
                    # Plot Forecast
                    # We need to extend the dates. For MVP just using Month 1, 2, 3
                    future_dates = [f"Month +{i+1}" for i in range(len(scenario_data["predicted_revenue"]))]
                    
                    fig3 = go.Figure()
                    
                    # Confidence Band
                    fig3.add_trace(go.Scatter(
                        x=future_dates, y=scenario_data["confidence_band_upper"],
                        mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'
                    ))
                    fig3.add_trace(go.Scatter(
                        x=future_dates, y=scenario_data["confidence_band_lower"],
                        mode='lines', fill='tonexty', fillcolor='rgba(0,123,255,0.2)', line=dict(width=0),
                        name='Confidence Band'
                    ))
                    
                    # Main Line
                    fig3.add_trace(go.Scatter(
                        x=future_dates, y=scenario_data["predicted_revenue"],
                        mode='lines+markers', name='Forecast', line=dict(color='#007bff', width=4)
                    ))
                    
                    st.plotly_chart(fig3, use_container_width=True)

                # --- SECTION 3: VIRTUAL CFO ---
                st.markdown("---")
                st.subheader("3️⃣ Virtual CFO Strategy (Advisor)")
                
                advisor = data["advisor"]
                
                col1, col2 = st.columns(2)
                
                for i, card in enumerate(advisor["strategic_advice"]):
                    # Risk Color Coding
                    risk_class = f"risk-{card['risk'].lower()}"
                    
                    # Use columns to create a grid
                    with (col1 if i % 2 == 0 else col2):
                        st.markdown(f"""
                        <div class="advice-card {risk_class}">
                            <h3>📌 {card['decision']}</h3>
                            <p><strong>why:</strong> {card['reason']}</p>
                            <p><strong>Impact:</strong> {card['impact']}</p>
                            <p><small>Confidence: {int(card['confidence']*100)}% | Risk: {card['risk']}</small></p>
                        </div>
                        """, unsafe_allow_html=True)

            else:
                st.error(f"Error from API: {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("🚨 API Connection Failed. Is the FastAPI server running on port 8000?")
            st.code("uvicorn app.main:app --reload")

else:
    # Landing Page State
    st.info("👋 Welcome! Please upload a financial CSV file to begin your analysis.")
    
    # Generate Sample Data Button (to help user test)
    if st.button("Generate Sample CSV"):
        sample_csv = """date,revenue,expenses
2023-01-01,10000,8000
2023-02-01,12000,8500
2023-03-01,11000,9000
2023-04-01,15000,9500
2023-05-01,16000,10000
2023-06-01,14000,11000
2023-07-01,18000,12000
2023-08-01,19000,12500
2023-09-01,21000,13000
2023-10-01,20000,14000
"""
        st.download_button("Download Sample CSV", sample_csv, "financial_sample.csv", "text/csv")
