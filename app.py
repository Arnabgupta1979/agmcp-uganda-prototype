import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Configuration
st.set_page_config(
    page_title="AgMCP Uganda - Agricultural Advisory",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DISTRICTS DATABASE
DISTRICTS = {
    'Wakiso': {
        'region': 'Lake Victoria Crescent',
        'lat': 0.4040,
        'lon': 32.4590,
        'rainfall_pattern': 'bimodal',
        'main_crops': ['maize', 'beans', 'groundnuts'],
        'description': 'Central Uganda - Two rainy seasons per year'
    },
    'Gulu': {
        'region': 'Northern Lango/Acholi', 
        'lat': 2.7796,
        'lon': 32.2997,
        'rainfall_pattern': 'unimodal',
        'main_crops': ['maize', 'beans', 'sorghum'],
        'description': 'Northern Uganda - Single long rainy season'
    },
    'Kabale': {
        'region': 'Southwestern Highlands',
        'lat': -1.2411,
        'lon': 29.9914,
        'rainfall_pattern': 'highland_bimodal',
        'main_crops': ['beans', 'irish_potato', 'climbing_beans'],
        'description': 'Highland region - Cool climate, two seasons'
    }
}

# ALERT RULES FROM UGANDA CROP CALENDAR
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
        'district': 'gulu',
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
    },
    {
        'crop': 'maize',
        'district': 'gulu', 
        'season': 1,
        'stage': 'pest_control',
        'start_date': '04-01',
        'end_date': '05-30',
        'weather_conditions': {'temperature': 25, 'humidity': 70},
        'alert_type': 'warning',
        'priority': 'medium',
        'title': 'Fall Armyworm Risk Period',
        'message': 'Weather conditions favor Fall Armyworm development. Scout fields regularly.',
        'actions': [
            'Check plants every 2-3 days',
            'Look for whorl damage',
            'Apply biocontrol if available',
            'Use recommended insecticide if severe'
        ]
    }
]

# WEATHER FUNCTIONS
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

# ALERT ENGINE
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

# CROP INFORMATION
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
    # Header
    st.markdown("""
    # 🌾 AgMCP Uganda
    ### Agricultural Management & Climate Prediction System
    *Prototype v0.1 - Real-time crop advisory for Uganda farmers*
    """)
    
    # Sidebar
    with st.sidebar:
        st.header("📍 Farm Details")
        
        district = st.selectbox(
            "Select District:",
            list(DISTRICTS.keys()),
            help="Choose your district"
        )
        
        district_info = DISTRICTS[district]
        
        st.info(f"""
        **{district_info['region']}**
        📍 {district_info['description']}
        """)
        
        crop = st.selectbox(
            "Select Crop:",
            district_info['main_crops'],
            help="Choose your current crop"
        )
        
        st.markdown(f"📅 **Date:** {datetime.now().strftime('%B %d, %Y')}")
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(f"🎯 Advisory: {crop.title()} in {district}")
        
        forecast = get_weather_forecast(district_info['lat'], district_info['lon'])
        
        if forecast:
            weather_analysis = analyze_weather_conditions(forecast)
            current_date = datetime.now()
            
            alerts = check_alerts(district, crop, current_date, weather_analysis)
            
            if alerts:
                st.subheader("⚠️ Active Alerts")
                
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
                        
                        st.caption(f"Crop stage: {rule['stage'].replace('_', ' ').title()} | Priority: {rule['priority'].title()}")
            else:
                st.success("✅ No critical alerts at this time")
                st.info("Continue with normal farming activities. Check daily for updates.")
            
            st.subheader("🌦️ 7-Day Weather Forecast")
            
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
        else:
            st.error("Unable to load weather data. Please check your connection and try again.")
    
    with col2:
        st.header("📊 Summary")
        
        if forecast:
            total_rain = sum(day['rainfall_mm'] for day in forecast)
            avg_temp = sum(day['temp_max'] for day in forecast) / len(forecast)
            rainy_days = len([d for d in forecast if d['rainfall_mm'] > 1])
            
            st.metric("7-Day Rain Total", f"{total_rain:.1f} mm")
            st.metric("Avg Max Temp", f"{avg_temp:.1f}°C") 
            st.metric("Rainy Days", f"{rainy_days} days")
        
        st.subheader("🌱 Crop Info")
        guidance = get_crop_guidance(crop, district)
        
        if guidance:
            st.markdown(f"**Season:** {guidance['season']}")
            st.markdown(f"**Stages:** {guidance['key_stages']}")
            st.markdown(f"**Watch for:** {guidance['critical_periods']}")
            st.info(f"💡 **Tip:** {guidance['tips']}")
        
        st.subheader("ℹ️ About")
        st.markdown("""
        This system uses:
        - Uganda crop calendar data
        - Real-time weather forecasts
        - Agricultural best practices
        - Location-specific timing
        
        **Data Sources:**
        - Open-Meteo Weather API
        - NARO Extension Guidelines
        - Uganda Ministry of Agriculture
        """)

if __name__ == "__main__":
    main()
