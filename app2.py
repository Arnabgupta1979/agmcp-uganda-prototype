import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

# Configuration
st.set_page_config(
    page_title="AgMCP Uganda - Agricultural Advisory",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DISTRICTS DATABASE (Enhanced with more details)
DISTRICTS = {
    'Wakiso': {
        'region': 'Lake Victoria Crescent',
        'lat': 0.4040,
        'lon': 32.4590,
        'rainfall_pattern': 'bimodal',
        'main_crops': ['maize', 'beans', 'groundnuts'],
        'description': 'Central Uganda - Two rainy seasons per year',
        'population': '2.1M',
        'elevation': '1200m',
        'soil_type': 'Ferralsols'
    },
    'Gulu': {
        'region': 'Northern Lango/Acholi', 
        'lat': 2.7796,
        'lon': 32.2997,
        'rainfall_pattern': 'unimodal',
        'main_crops': ['maize', 'beans', 'sorghum'],
        'description': 'Northern Uganda - Single long rainy season',
        'population': '195K',
        'elevation': '1100m',
        'soil_type': 'Lixisols'
    },
    'Kabale': {
        'region': 'Southwestern Highlands',
        'lat': -1.2411,
        'lon': 29.9914,
        'rainfall_pattern': 'highland_bimodal',
        'main_crops': ['beans', 'irish_potato', 'climbing_beans'],
        'description': 'Highland region - Cool climate, two seasons',
        'population': '601K',
        'elevation': '2000m',
        'soil_type': 'Nitisols'
    },
    'Soroti': {
        'region': 'Eastern Savannah',
        'lat': 1.7111,
        'lon': 33.6111,
        'rainfall_pattern': 'bimodal',
        'main_crops': ['maize', 'groundnuts', 'rice'],
        'description': 'Eastern Uganda - Rice and groundnut hub',
        'population': '463K',
        'elevation': '1100m',
        'soil_type': 'Acrisols'
    },
    'Mbarara': {
        'region': 'Western Rangelands',
        'lat': -0.6063,
        'lon': 30.6474,
        'rainfall_pattern': 'bimodal',
        'main_crops': ['maize', 'beans', 'bananas'],
        'description': 'Cattle corridor - Mixed farming systems',
        'population': '472K',
        'elevation': '1400m',
        'soil_type': 'Ferralsols'
    }
}

# ALERT RULES (same as before)
ALERT_RULES = [
    {
        'crop': 'maize',
        'district': 'wakiso',
        'season': 1,
        'stage': 'fertilizer_top_dress',
        'start_date': '04-15',
        'end_date': '05-15',
        'weather_conditions': {'rainfall_24h': 30, 'humidity': 85},
        'alert_type': 'delay',
        'priority': 'high',
        'title': 'Delay Nitrogen Top-Dressing',
        'message': 'Heavy rain expected during fertilizer application window. Delay to avoid nutrient loss.',
        'actions': [
            'Wait for 2 consecutive dry days',
            'Apply urea or CAN after soil drains',
            'Check field for waterlogging',
            'Scout for weeds while waiting'
        ]
    },
    {
        'crop': 'beans',
        'district': 'all',
        'season': 1,
        'stage': 'harvest',
        'start_date': '06-15',
        'end_date': '07-15',
        'weather_conditions': {'rainfall_72h': 20},
        'alert_type': 'urgent',
        'priority': 'critical',
        'title': 'Harvest Beans Immediately',
        'message': 'Rain forecast will cause pod rot and grain quality loss. Harvest mature pods now.',
        'actions': [
            'Harvest all mature pods today',
            'Dry beans on tarpaulins under cover',
            'Check pods for brown/dry appearance', 
            'Store in ventilated bags'
        ]
    },
    {
        'crop': 'groundnuts',
        'district': 'all',
        'season': 1,
        'stage': 'planting',
        'start_date': '04-01',
        'end_date': '05-15',
        'weather_conditions': {'rainfall_forecast': 'adequate'},
        'alert_type': 'timing',
        'priority': 'medium',
        'title': 'Optimal Groundnut Planting Time',
        'message': 'Current conditions ideal for groundnut planting. Act within 48 hours.',
        'actions': [
            'Plant immediately after steady rain',
            'Use fresh, tested seed',
            'Ensure proper row spacing',
            'Plan for earthing-up at 6 weeks'
        ]
    }
]

# MARKET PRICES (Mock data for demonstration)
MARKET_PRICES = {
    'maize': {'price_ugx': 2500, 'trend': '↗️', 'change': '+5%'},
    'beans': {'price_ugx': 4200, 'trend': '↘️', 'change': '-2%'},
    'groundnuts': {'price_ugx': 6800, 'trend': '↗️', 'change': '+8%'},
    'sorghum': {'price_ugx': 2200, 'trend': '→', 'change': '0%'},
    'irish_potato': {'price_ugx': 3500, 'trend': '↗️', 'change': '+12%'}
}

# MAP FUNCTIONS
def create_uganda_map(selected_district=None, weather_data=None):
    """Create interactive map of Uganda with district markers"""
    
    # Center map on Uganda
    m = folium.Map(
        location=[1.3733, 32.2903], 
        zoom_start=7,
        tiles='OpenStreetMap'
    )
    
    # Add custom CSS styling
    folium.plugins.Fullscreen().add_to(m)
    
    # Add district markers
    for district_name, info in DISTRICTS.items():
        # Get weather for this district if available
        district_weather = ""
        if weather_data and district_name.lower() in weather_data:
            weather = weather_data[district_name.lower()]
            district_weather = f"""
            <br><b>Weather Today:</b>
            <br>🌧️ Rain: {weather.get('rainfall', 0):.1f}mm
            <br>🌡️ Temp: {weather.get('temp_max', 'N/A')}°C
            <br>💧 Humidity: {weather.get('humidity', 'N/A')}%
            """
        
        # Create popup content
        popup_content = f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="color: #2E7D32; margin-bottom: 10px;">🏛️ {district_name}</h4>
            <b>Region:</b> {info['region']}<br>
            <b>Population:</b> {info['population']}<br>
            <b>Elevation:</b> {info['elevation']}<br>
            <b>Rainfall:</b> {info['rainfall_pattern']}<br>
            <b>Main Crops:</b> {', '.join(info['main_crops'][:2])}<br>
            <b>Soil:</b> {info['soil_type']}
            {district_weather}
        </div>
        """
        
        # Choose marker color based on selection and alerts
        if district_name == selected_district:
            icon_color = 'red'
            icon_symbol = 'star'
        else:
            icon_color = 'green'
            icon_symbol = 'leaf'
        
        # Add marker
        folium.Marker(
            location=[info['lat'], info['lon']],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=f"Click for {district_name} details",
            icon=folium.Icon(
                color=icon_color, 
                icon=icon_symbol,
                prefix='fa'
            )
        ).add_to(m)
    
    # Add title
    title_html = '''
    <h3 align="center" style="font-size:20px; color: #2E7D32;">
        <b>🌾 Uganda Agricultural Districts</b>
    </h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    return m

def create_weather_trend_chart(forecast_data, district_name):
    """Create weather trend visualization"""
    if not forecast_data:
        return None
    
    df = pd.DataFrame(forecast_data)
    df['date'] = pd.to_datetime(df['date'])
    df['day'] = df['date'].dt.strftime('%a %m/%d')
    
    # Create subplot with rainfall and temperature
    fig = go.Figure()
    
    # Add rainfall bars
    fig.add_trace(go.Bar(
        x=df['day'],
        y=df['rainfall_mm'],
        name='Rainfall (mm)',
        marker_color='lightblue',
        yaxis='y'
    ))
    
    # Add temperature line
    fig.add_trace(go.Scatter(
        x=df['day'],
        y=df['temp_max'],
        mode='lines+markers',
        name='Max Temp (°C)',
        line=dict(color='red', width=3),
        yaxis='y2'
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Weather Forecast - {district_name}',
        xaxis_title='Date',
        yaxis=dict(title='Rainfall (mm)', side='left'),
        yaxis2=dict(title='Temperature (°C)', side='right', overlaying='y'),
        hovermode='x unified',
        height=400
    )
    
    return fig

# WEATHER FUNCTIONS (same as before)
@st.cache_data(ttl=3600)
def get_weather_forecast(lat, lon, days=7):
    """Fetch weather forecast from Open-Meteo API"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'precipitation_sum,temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean',
        'timezone': 'Africa/Nairobi',
        'forecast_days': days
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        forecast = []
        daily = data['daily']
        for i in range(len(daily['time'])):
            forecast.append({
                'date': daily['time'][i],
                'rainfall_mm': daily['precipitation_sum'][i] or 0,
                'temp_max': daily['temperature_2m_max'][i],
                'temp_min': daily['temperature_2m_min'][i],
                'humidity': daily['relative_humidity_2m_mean'][i] or 0
            })
        
        return forecast
    except Exception as e:
        st.error(f"Unable to fetch weather data: {str(e)}")
        return []

def analyze_weather_conditions(forecast):
    """Analyze weather for alert triggers"""
    if not forecast:
        return {}
    
    analysis = {
        'next_24h_rain': forecast[0]['rainfall_mm'],
        'next_72h_rain': sum(day['rainfall_mm'] for day in forecast[:3]),
        'avg_humidity': sum(day['humidity'] for day in forecast[:3]) / 3,
        'avg_temp': sum(day['temp_max'] for day in forecast[:3]) / 3,
        'rainy_days_ahead': len([d for d in forecast[:7] if d['rainfall_mm'] > 1])
    }
    
    return analysis

# ALERT ENGINE (same as before)
def check_alerts(district, crop, current_date, weather_analysis):
    """Check for active alerts based on crop calendar and weather"""
    active_alerts = []
    current_date_str = current_date.strftime('%m-%d')
    
    for rule in ALERT_RULES:
        if rule['district'] != 'all' and rule['district'] != district.lower():
            continue
        if rule['crop'] != crop:
            continue
        
        if rule['start_date'] <= current_date_str <= rule['end_date']:
            weather_triggered = check_weather_trigger(rule['weather_conditions'], weather_analysis)
            
            if weather_triggered:
                active_alerts.append({
                    'rule': rule,
                    'severity': get_alert_severity(rule['priority']),
                    'weather_context': weather_triggered
                })
    
    return active_alerts

def check_weather_trigger(conditions, analysis):
    """Check if weather conditions trigger an alert"""
    triggers = []
    
    if 'rainfall_24h' in conditions and analysis.get('next_24h_rain', 0) > conditions['rainfall_24h']:
        triggers.append(f"Heavy rain expected: {analysis['next_24h_rain']:.1f}mm in 24h")
    
    if 'rainfall_72h' in conditions and analysis.get('next_72h_rain', 0) > conditions['rainfall_72h']:
        triggers.append(f"Total rain forecast: {analysis['next_72h_rain']:.1f}mm in 3 days")
    
    if 'humidity' in conditions and analysis.get('avg_humidity', 0) > conditions['humidity']:
        triggers.append(f"High humidity: {analysis['avg_humidity']:.0f}%")
    
    if 'rainfall_forecast' in conditions and analysis.get('rainy_days_ahead', 0) >= 3:
        triggers.append("Adequate rainfall expected")
    
    return triggers

def get_alert_severity(priority):
    """Map priority to display severity"""
    severity_map = {
        'critical': {'icon': '🔴', 'level': 'CRITICAL', 'color': 'red'},
        'high': {'icon': '🟡', 'level': 'HIGH', 'color': 'orange'},
        'medium': {'icon': '🟢', 'level': 'ADVISORY', 'color': 'green'},
        'low': {'icon': '🔵', 'level': 'INFO', 'color': 'blue'}
    }
    return severity_map.get(priority, severity_map['low'])

def get_crop_guidance(crop, district):
    """Get general crop guidance"""
    guidance = {
        'maize': {
            'season': 'Mar-Jul (Season 1), Aug-Dec (Season 2)',
            'key_stages': 'Planting → Top-dress (4-6 weeks) → Harvest',
            'critical_periods': 'Fertilizer application, Fall Armyworm scouting',
            'tips': 'Plant at rain onset for nitrogen flush benefit'
        },
        'beans': {
            'season': 'Mar-Jul (Season 1), Aug-Dec (Season 2)', 
            'key_stages': 'Planting → Weeding (2,5 weeks) → Harvest',
            'critical_periods': 'Early weeding, harvest timing',
            'tips': 'Harvest before heavy rains to prevent pod rot'
        },
        'groundnuts': {
            'season': 'Feb-Mar, Aug-Sep planting',
            'key_stages': 'Planting → Earthing-up → Harvest (90-110 days)',
            'critical_periods': 'Rain-onset planting, pegging stage',
            'tips': 'Must plant early in season for proper pod filling'
        },
        'sorghum': {
            'season': 'Mar-Aug (single season in north)',
            'key_stages': 'Planting → Weeding → Bird scaring → Harvest',
            'critical_periods': 'Early weeding, grain filling (bird damage)',
            'tips': 'Very drought tolerant, good for marginal areas'
        },
        'irish_potato': {
            'season': 'Mar-Jul, Sep-Jan (highlands)',
            'key_stages': 'Planting → Earthing-up → Harvest',
            'critical_periods': 'Cool weather establishment, blight control',
            'tips': 'Harvest before heavy rains, store in cool dry place'
        }
    }
    return guidance.get(crop, {})

# MAIN APPLICATION
def main():
    # Custom CSS for styling
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #4CAF50, #2E7D32);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    .district-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 10px;
    }
    .metric-card {
        background: #e8f5e8;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin-bottom: 10px;">🌾 AgMCP Uganda Dashboard</h1>
        <p style="color: white; margin: 0;">Real-time Agricultural Intelligence & Climate Prediction</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for district selection
    if 'selected_district' not in st.session_state:
        st.session_state.selected_district = 'Wakiso'
    
    # Create two main columns
    map_col, sidebar_col = st.columns([3, 1])
    
    with map_col:
        st.subheader("🗺️ Interactive Uganda Agricultural Map")
        
        # Get weather data for map markers
        weather_for_map = {}
        for district_name, info in DISTRICTS.items():
            forecast = get_weather_forecast(info['lat'], info['lon'], 1)
            if forecast:
                weather_for_map[district_name.lower()] = {
                    'rainfall': forecast[0]['rainfall_mm'],
                    'temp_max': forecast[0]['temp_max'],
                    'humidity': forecast[0]['humidity']
                }
        
        # Create and display map
        uganda_map = create_uganda_map(
            selected_district=st.session_state.selected_district,
            weather_data=weather_for_map
        )
        
        map_data = st_folium(uganda_map, width=700, height=400)
        
        # Handle map clicks
        if map_data['last_object_clicked_popup']:
            clicked_popup = map_data['last_object_clicked_popup']
            # Extract district name from popup content
            for district_name in DISTRICTS.keys():
                if district_name in str(clicked_popup):
                    st.session_state.selected_district = district_name
                    st.rerun()
    
    with sidebar_col:
        st.header("📍 Farm Details")
        
        # District selection dropdown (synced with map)
        district = st.selectbox(
            "Select District:",
            list(DISTRICTS.keys()),
            index=list(DISTRICTS.keys()).index(st.session_state.selected_district),
            help="Choose your district or click on the map"
        )
        
        # Update session state if dropdown changes
        if district != st.session_state.selected_district:
            st.session_state.selected_district = district
            st.rerun()
        
        district_info = DISTRICTS[district]
        
        # District info card
        st.markdown(f"""
        <div class="district-card">
            <h4>🏛️ {district}</h4>
            <b>Region:</b> {district_info['region']}<br>
            <b>Population:</b> {district_info['population']}<br>
            <b>Elevation:</b> {district_info['elevation']}<br>
            <b>Rainfall:</b> {district_info['rainfall_pattern']}<br>
            <b>Soil Type:</b> {district_info['soil_type']}
        </div>
        """, unsafe_allow_html=True)
        
        # Crop selection
        crop = st.selectbox(
            "Select Crop:",
            district_info['main_crops'],
            help="Choose your current crop"
        )
        
        # Current date
        st.markdown(f"📅 **Date:** {datetime.now().strftime('%B %d, %Y')}")
        
        # Market price card
        if crop in MARKET_PRICES:
            price_info = MARKET_PRICES[crop]
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 {crop.title()} Price</h4>
                <h3>UGX {price_info['price_ugx']:,}/kg</h3>
                <p>{price_info['trend']} {price_info['change']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Main content area
    st.markdown("---")
    
    # Get weather data for selected district
    forecast = get_weather_forecast(district_info['lat'], district_info['lon'])
    
    if forecast:
        # Create two columns for main content
        alert_col, chart_col = st.columns([1, 1])
        
        with alert_col:
            st.subheader(f"⚠️ Alerts: {crop.title()} in {district}")
            
            weather_analysis = analyze_weather_conditions(forecast)
            current_date = datetime.now()
            alerts = check_alerts(district, crop, current_date, weather_analysis)
            
            if alerts:
                for alert in alerts:
                    rule = alert['rule']
                    severity = alert['severity']
                    
                    with st.expander(f"{severity['icon']} {severity['level']}: {rule['title']}", expanded=True):
                        st.markdown(f"**{rule['message']}**")
                        
                        if alert['weather_context']:
                            st.info("Weather triggers: " + ", ".join(alert['weather_context']))
                        
                        st.markdown("**Recommended Actions:**")
                        for action in rule['actions']:
                            st.markdown(f"• {action}")
                        
                        st.caption(f"Stage: {rule['stage'].replace('_', ' ').title()}")
            else:
                st.success("✅ No critical alerts at this time")
                st.info("Continue with normal farming activities.")
        
        with chart_col:
            st.subheader("📈 Weather Trends")
            
            # Create and display weather trend chart
            weather_chart = create_weather_trend_chart(forecast, district)
            if weather_chart:
                st.plotly_chart(weather_chart, use_container_width=True)
        
        # Weather summary metrics
        st.subheader("🌦️ Weather Summary")
        
        total_rain = sum(day['rainfall_mm'] for day in forecast)
        avg_temp = sum(day['temp_max'] for day in forecast) / len(forecast)
        rainy_days = len([d for d in forecast if d['rainfall_mm'] > 1])
        max_temp_day = max(forecast, key=lambda x: x['temp_max'])
        
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("7-Day Rain Total", f"{total_rain:.1f} mm")
        with metric_col2:
            st.metric("Avg Max Temp", f"{avg_temp:.1f}°C")
        with metric_col3:
            st.metric("Rainy Days", f"{rainy_days} days")
        with metric_col4:
            st.metric("Hottest Day", f"{max_temp_day['temp_max']:.1f}°C")
        
        # Detailed weather table
        st.subheader("📊 Detailed 7-Day Forecast")
        
        df = pd.DataFrame(forecast)
        df['Date'] = pd.to_datetime(df['date']).dt.strftime('%a %m/%d')
        df['Rain (mm)'] = df['rainfall_mm'].round(1)
        df['Max (°C)'] = df['temp_max'].round(1)
        df['Min (°C)'] = df['temp_min'].round(1)
        df['Humidity (%)'] = df['humidity'].round(0).astype(int)
        
        st.dataframe(
            df[['Date', 'Rain (mm)', 'Max (°C)', 'Min (°C)', 'Humidity (%)']],
            use_container_width=True,
            hide_index=True
        )
        
        # Crop guidance section
        st.subheader("🌱 Crop Management Guide")
        guidance = get_crop_guidance(crop, district)
        
        if guidance:
            guide_col1, guide_col2 = st.columns(2)
            
            with guide_col1:
                st.markdown(f"**Growing Season:** {guidance['season']}")
                st.markdown(f"**Key Stages:** {guidance['key_stages']}")
            
            with guide_col2:
                st.markdown(f"**Critical Periods:** {guidance['critical_periods']}")
                st.info(f"💡 **Pro Tip:** {guidance['tips']}")
    
    else:
        st.error("Unable to load weather data. Please check your connection and try again.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p><b>AgMCP Uganda v0.2</b> - Powered by Open-Meteo Weather API • NARO Agricultural Guidelines • Uganda Ministry of Agriculture</p>
        <p>🌾 Empowering farmers with real-time agricultural intelligence</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
