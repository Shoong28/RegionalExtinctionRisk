######### 라이브러리 로드 #######################################
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import plotly.express as px
import altair as alt

######### 데이터 로드 및 전처리 ####################################
### 지도 데이터 ###
korea_sido = gpd.read_file('map_sido_Geo.geojson')
korea_gu = gpd.read_file('gdf_korea_2024.json')

### 지방소멸위험지수 데이터 (시도) ###
extinction_risk = pd.read_excel('(붙임1)지방소멸위험지수(2302).xlsx', sheet_name="시도_'2302")

### 지방소멸위험지수 데이터 (시군구) ###
extinction_risk_gu = pd.read_excel('(붙임1)지방소멸위험지수(2302).xlsx', sheet_name="시군구-'2302")
extinction_risk_gu = extinction_risk_gu[['시군구', '지방소멸위험지수', '지방소멸위험분류']]
extinction_risk_gu['시군구'] = extinction_risk_gu['시군구'].str.strip()# 공백 제거
jeju_row = extinction_risk_gu[extinction_risk_gu['시군구'] == '제주도'] # 제주도 행 찾기
extinction_risk_gu = extinction_risk_gu[extinction_risk_gu['시군구'] != '제주도']# 제주도 행 제거
# 제주시와 서귀포시 행 추가
jeju_city = jeju_row.copy()
jeju_city['시군구'] = '제주시'
seogwipo_city = jeju_row.copy()
seogwipo_city['시군구'] = '서귀포시'
extinction_risk_gu = pd.concat([extinction_risk_gu, jeju_city, seogwipo_city], ignore_index=True)

### 시도별 청년 비율 ###
sido_youth_rate = pd.read_csv('인구총조사_청년인구비율_시도_시_군_구__20241212040441.csv', encoding='UTF-8')
sido_youth_rate = sido_youth_rate[['행정구역별(1)', '2023']] # 필요한 컬럼만 선택
sido_youth_rate.columns = ['시도', '청년인구비율'] # 컬럼명 변경
sido_youth_rate = sido_youth_rate.iloc[3:] # 필요없는 행 제거
sido_youth_rate = sido_youth_rate.sort_values(by='청년인구비율', ascending=False) # 청년인구비율 높은 순으로 데이터 정렬

### 전입사유별 이동건수 ###
move = pd.read_csv('시도_연령_전입사유별_1인이동건수_20241215035929.csv', encoding='UTF-8')
move = move[move['행정구역(시도)별'] != '전국'] # 행정구역 컬럼이 '전국'인 데이터 제외
move = move[move['전입사유별'] != '계'] # 전입사유가 '계'인 데이터 제외
youth_move = move.query('연령별 == "20대" or 연령별 == "30대"') # 20대와 30대 데이터만 선택
youth_move.columns = ['시도', '연령대', '전입사유', '이동건수']
# 수도권과 비수도권으로 구분하는 새로운 열 생성
youth_move['지역구분'] = youth_move['시도'].apply(
    lambda x: '수도권' if x in ['서울특별시', '인천광역시', '경기도'] else '비수도권')
# 수도권과 비수도권으로 그룹화 및 이동건수 합산
region_grouped = (
    youth_move.groupby(['지역구분', '전입사유', '연령대'], as_index=False)
    .agg({'이동건수': 'sum'}))

### 시도별 규모별 산업체 개수 ###
sido_company = pd.read_excel('시도별__산업별__규모별__사업체수_및_종사자수_성별__20241216042548.xlsx')
sido_company = sido_company[['시도별(17개)', '규모별', '2022']] # 필요한 컬럼만 선택
sido_company.columns = ['시도', '규모', '산업체수'] # 컬럼명 변경
sido_company = sido_company[1:].reset_index(drop=True) # 첫 행 제거
# NaN 값을 앞 행의 값으로 채우기 (시도명이 NaN인 경우)
sido_company['시도'] = sido_company['시도'].fillna(method='ffill')
# '시도' 기준으로 산업체수 합산 (규모 구분 제거)
sido_company = (
    sido_company.groupby('시도', as_index=False)
    .agg({'산업체수': 'sum'})
)
sido_company = sido_company[sido_company['시도'] != '전국'] # '전국' 데이터 제외

### 시도별 대학교 개수 ###
sido_univ = pd.read_csv('대학교_수_시도_시_군_구__20241215031858.csv', encoding='UTF-8')
sido_univ = sido_univ[['행정구역별', '2023.1', '2023.3']] # 필요한 컬럼만 선택
sido_univ.columns = ['시도', '일반대', '교육대'] # 컬럼명 변경
sido_univ = sido_univ.iloc[2:].reset_index(drop=True)# 첫 두 행 제거
# 지도데이터와 이름 통일
sido_univ['시도'] = sido_univ['시도'].replace('전북특별자치도', '전라북도')
sido_univ['시도'] = sido_univ['시도'].replace('강원특별자치도', '강원도')
# 교육대 컬럼의 - 문자를 0으로 변환
sido_univ['교육대'] = sido_univ['교육대'].replace('-', 0)
# '일반대'와 '교육대' 열을 숫자형으로 변환
sido_univ['일반대'] = pd.to_numeric(sido_univ['일반대'])
sido_univ['교육대'] = pd.to_numeric(sido_univ['교육대'])
# 일반대와 교육대 합산
sido_univ['일반대 및 교대'] = sido_univ['일반대'] + sido_univ['교육대']

### 시도별 상위20위 대학 개수 ###
top_univ_2024 =pd.read_csv('중앙일보_대학평가_2024.csv', encoding='UTF-8')
top_univ_grouped = top_univ_2024.groupby('시도').size().reset_index(name='대학수')# 시도별 상위 20개 대학교 개수 계산

########## 시각화 ################################################
### 지방소멸위험지수 지도시각화 (시도/시군구) ###
def generate_map(level):
    bins = [0, 0.2, 0.5, 1.0, 1.5, 2.0] # 지방소멸위험분류 범주 설정
    map_location = [36.3504119, 127.3845475]
    base_map = folium.Map(location=map_location, zoom_start=7, tiles="cartodbpositron")

    if level == "시도":
        folium.Choropleth(
            geo_data=korea_sido,
            data=extinction_risk,
            columns=['시도', '지방소멸위험지수'],
            key_on='feature.properties.NAME',
            fill_color='RdYlGn',
            fill_opacity=0.7,
            line_opacity=0.5,
            bins=bins,
            legend_name="지방소멸위험지수"
        ).add_to(base_map)
    elif level == "시군구":
        folium.Choropleth(
            geo_data=korea_gu,
            data=extinction_risk_gu,
            columns=['시군구', '지방소멸위험지수'],
            key_on='feature.properties.NAME',
            fill_color='RdYlGn',
            fill_opacity=0.7,
            line_opacity=0.5,
            bins=bins,
            legend_name="지방소멸위험지수"
        ).add_to(base_map)

    return base_map

### 지방소멸위험분류 파이차트 (시도) ###
# 지방소멸위험분류 문자열 매핑
risk_labels = {
    1: '소멸위험 낮음',
    2: '소멸위험 보통',
    3: '소멸위험 주의',
    4: '소멸위험 진입',
    5: '소멸위험 높음'
}
# 색상 매핑
color_map = {
    '소멸위험 낮음': 'green',
    '소멸위험 보통': 'lightgreen',
    '소멸위험 주의': 'yellow',
    '소멸위험 진입': 'orange',
    '소멸위험 높음': 'red'
}

extinction_risk['지방소멸위험분류_라벨'] = extinction_risk['지방소멸위험분류'].map(risk_labels)

# 각 분류 단계에 속하는 시도 리스트 생성
risk_grouped = extinction_risk.groupby('지방소멸위험분류_라벨')['시도'].apply(lambda x: ', '.join(x)).reset_index()
risk_grouped['count'] = extinction_risk['지방소멸위험분류_라벨'].value_counts().sort_index().values

# 파이차트 생성
risk_sido_pie = px.pie(risk_grouped,
             names='지방소멸위험분류_라벨',
             values='count',
             title='지방소멸위험분류 (시도)',
             hover_data=['시도'],
             color='지방소멸위험분류_라벨',
             color_discrete_map=color_map,
             width = 500, height = 400)

risk_sido_pie.update_traces(textposition='inside',
                  textinfo='percent+label') # 텍스트 위치와 표시할 정보 설정

### 지방소멸위험분류 파이차트 (시군구) ###
extinction_risk_gu['지방소멸위험분류_라벨'] = extinction_risk_gu['지방소멸위험분류'].map(risk_labels)

# 각 분류 단계에 속하는 시도 리스트 생성
grouped_gu = extinction_risk_gu.groupby('지방소멸위험분류_라벨')['시군구'].apply(lambda x: ', '.join(x)).reset_index()
grouped_gu['count'] = extinction_risk_gu['지방소멸위험분류_라벨'].value_counts().sort_index().values

# 파이차트 생성
risk_gu_pie = px.pie(grouped_gu,
             names='지방소멸위험분류_라벨',
             values='count',
             title='지방소멸위험분류 (시군구)',
             color='지방소멸위험분류_라벨',
             color_discrete_map=color_map,
             width = 500, height = 400)

risk_gu_pie.update_traces(textposition='inside',
                  textinfo='percent+label') # 텍스트 위치와 표시할 정보 설정

### 청년인구비율 시각화 ###
youth_bar = alt.Chart(sido_youth_rate).mark_bar().encode(
    x=alt.X('청년인구비율:Q', axis=alt.Axis(title='청년인구비율(%)')),
    y=alt.Y('시도:N', sort = '-x', axis=alt.Axis(title='시도')), # 시도명을 청년인구비율 순으로 정렬
    color=alt.Color('청년인구비율:Q'),
    tooltip=['시도', '청년인구비율']
).properties(
    title='2023 시도별 청년 인구 비율',
    width=500,
    height=600
)

### 청년세대 수도권 전입사유별 이동건수 막대그래프 ###
capital_move = region_grouped[region_grouped['지역구분'] == '수도권']
cap_move_bar = px.bar(capital_move, 
             x='전입사유', 
             y='이동건수', 
             color='연령대',  # 색상으로 연령대 구분
             barmode='group',  # 그룹화된 막대그래프
            #  title='수도권 전입사유별 이동건수 (20대 vs 30대)'
            )

### 일자리 품질 지도시각화 ###
title = "시도별 규모 300인 이상 산업체수"
daejeon = [36.3504119, 127.3845475]

# 기본 지도 생성
job_map = folium.Map(
    location = daejeon,
    zoom_start = 6.5,
    tiles = 'cartodbpositron'
)

threshold_scale = [0, 100, 200, 300, 500, 800, 1100, sido_company['산업체수'].max()]

# Choropleth 지도 그리기
folium.Choropleth(
    geo_data = korea_sido,
    data = sido_company,
    columns = ('시도', '산업체수'),
    key_on = 'feature.properties.NAME',
    fill_color = 'BuPu',
    fill_opacity = 0.7,
    line_opacity = 0.5,
    legend_name = '산업체수',
    threshold_scale=threshold_scale
).add_to(job_map)
folium.GeoJson(
    korea_sido,
    tooltip=folium.GeoJsonTooltip(fields=['NAME'], aliases=['지역명:']),
    style_function=lambda x: {
        'color': 'transparent',  # 경계선 색상 투명으로 설정
        'weight': 0  # 경계선 두께 0으로 설정
    }
).add_to(job_map)

### 일자리 품질 파이차트 ###
# sido_company에 '지역구분' 컬럼 추가
sido_company['지역구분'] = sido_company['시도'].apply(
    lambda x: '수도권' if x in ['서울특별시', '인천광역시', '경기도'] else '비수도권'
)

# 수도권과 비수도권으로 그룹화 및 산업체수 합산
company_grouped = (
    sido_company.groupby('지역구분', as_index=False)
    .agg({'산업체수': 'sum'})
)

# 파이차트 생성
job_pie = px.pie(company_grouped, 
             names='지역구분', 
             values='산업체수', 
             title='수도권 vs 비수도권 규모 300인 이상 산업체수 개수',
             width = 500, height = 330
            )
job_pie.update_traces(textposition='inside',
                  textinfo='percent+label') 

### 대학교 개수 지도시각화 ###
title = "시도별 일반대 및 교육대 개수"

# 기본 지도 생성
univ_map = folium.Map(
    location = daejeon,
    zoom_start = 6.5,
    tiles = 'cartodbpositron'
)

# Choropleth 지도 그리기
folium.Choropleth(
    geo_data = korea_sido,
    data = sido_univ,
    columns = ('시도', '일반대 및 교대'),
    key_on = 'feature.properties.NAME',
    fill_color = 'BuPu',
    fill_opacity = 0.7,
    line_opacity = 0.5,
    legend_name = '대학교 수'
).add_to(univ_map)

folium.GeoJson(
    korea_sido,
    tooltip=folium.GeoJsonTooltip(fields=['NAME'], aliases=['지역명:']),
    style_function=lambda x: {
        'color': 'transparent',  # 경계선 색상 투명으로 설정
        'weight': 0  # 경계선 두께 0으로 설정
    }
).add_to(univ_map)

### 상위20위 대학 개수 파이차트 ###
# 파이차트 생성
top_univ_pie = px.pie(top_univ_grouped,
                      names='시도',
                      values='대학수',
                      title='시도별 상위 20위 대학 개수',
                      width=500, height=330)
top_univ_pie.update_traces(textposition='inside',
                           textinfo='percent+label')

############ Streamlit 페이지 구성 ########################################
st.set_page_config(page_title="📊지방소멸위험 대시보드", layout="wide")

## Sidebar생성
st.sidebar.title('📊지방소멸위험 대시보드')
st.sidebar.write('지방 소멸 위험 현황을 파악하고, 원인을 분석해봅시다 🚀')
page = st.sidebar.selectbox("페이지 선택", ["현황 파악", "원인 분석"]) # 페이지 셀렉트박스

## 페이지1 : 현황 파악
if page == "현황 파악":
    st.title("🔎 지방소멸위험 현황")

    # 컬럼 구성
    col1, col2 = st.columns([6,4])

    # 첫 번째 열: 지도 시각화, 파이차트
    with col1:
        map_level = st.selectbox("지도 단위:", ["시도", "시군구"])
        st.subheader(f"지방소멸위험지수 ({map_level})")
        selected_map = generate_map(map_level)
        st_folium(selected_map, width=800, height=500)
        # 지도 아래에 파이 차트 추가
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            # st.subheader("지방소멸위험분류 (시도)")
            st.plotly_chart(risk_sido_pie, use_container_width=True)
        with sub_col2:
            # st.subheader("지방소멸위험분류 (시군구)")
            st.plotly_chart(risk_gu_pie, use_container_width=True)

    # 두 번째 열: 청년 인구 비율, 텍스트박스
    with col2:
        st.header("") # 간격을 위해 빈 공간 추가
        st.write("")
        st.subheader("시도별 청년 인구 비율")
        youth_bar = alt.Chart(sido_youth_rate).mark_bar().encode(
            x=alt.X('청년인구비율:Q', axis=alt.Axis(title='청년인구비율(%)')),
            y=alt.Y('시도:N', sort='-x', axis=alt.Axis(title='시도')),
            color=alt.Color('청년인구비율:Q'),
            tooltip=['시도', '청년인구비율']
        ).properties(
            title='2023 시도별 청년 인구 비율',
            width=400,
            height=500
        )
        st.altair_chart(youth_bar, use_container_width=True)

        st.header("") # 간격 추가
    
        st.text_area(
            "지방소멸위험분류",
            """
            지방소멸위험 지수 1.5 이상 : 소멸위험 낮음
            지방소멸위험 지수 1.0 ~ 1.5 미만 : 소멸위험 보통
            지방소멸위험 지수 0.5 ~ 1.0 미만 : 소멸위험 주의
            지방소멸위험 지수 0.2 ~ 0.5 미만 : 소멸위험 진입
            지방소멸위험 지수 0.2 미만 : 소멸위험 높음
            """,
            height=200
        )

## 페이지2 : 원인 분석
if page == "원인 분석":
    st.title("💡 청년 수도권 쏠림 현상 원인 분석")
    # 청년세대 수도권 전입사유별 이동건수 막대그래프
    st.subheader("청년세대 수도권 전입사유별 이동건수")
    st.plotly_chart(cap_move_bar, use_container_width=True)

    # 하단 컬럼 설정
    col1, col2, col3 = st.columns(3)

    # 첫번째 컬럼 : 일자리 품질 지도시각화
    with col1:
        st.subheader("시도별 규모 300인 이상 산업체 개수")
        st_folium(job_map, width=400, height=600)

    # 두번째 컬럼 : 파이차트
    with col2:
        st.write("")
        st.write("")
        st.plotly_chart(job_pie)
        st.plotly_chart(top_univ_pie)

    # 세번째 컬럼 : 대학교 개수 지도시각화
    with col3:
        st.subheader("시도별 일반대 및 교육대 개수")
        st_folium(univ_map, width=400, height=600)