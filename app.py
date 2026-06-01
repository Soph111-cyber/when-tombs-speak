from __future__ import annotations

import io
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_TITLE = "When Tombs Speak"
APP_SUBTITLE = "A Digital Map of Power, Gender, Inequality, and Public Memory in Chinese Tomb Archaeology"
DATA_PATH = Path(__file__).parent / "data" / "museums.csv"

st.set_page_config(page_title=APP_TITLE, page_icon="🏺", layout="wide")

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
    .hero {
        padding: 1.2rem 1.4rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(112,66,20,.12), rgba(214,174,104,.20));
        border: 1px solid rgba(112,66,20,.18);
        margin-bottom: 1rem;
    }
    .hero h1 {margin-bottom: .15rem; font-size: 2.4rem;}
    .hero p {font-size: 1.05rem; margin: 0; color: #4f3b2a;}
    .metric-card {
        padding: 1rem;
        border-radius: 18px;
        border: 1px solid rgba(0,0,0,.08);
        background: rgba(250,250,250,.75);
    }
    .small-note {font-size: .88rem; color: #666;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Data utilities
# -----------------------------
REQUIRED_COLUMNS = [
    "id", "museum_name", "city", "province", "latitude", "longitude", "period", "tomb_type",
    "featured_site_or_artifact", "archaeological_truth", "museum_framing", "visitor_perception",
    "ethical_question", "possible_change", "power_narrative", "gender_perspective",
    "commoner_perspective", "labor_perspective", "reflective_narrative", "visitor_comments",
    "controversy_reflection", "photo_url", "official_url", "notes"
]

NUMERIC_COLUMNS = [
    "latitude", "longitude", "power_narrative", "gender_perspective", "commoner_perspective",
    "labor_perspective", "reflective_narrative", "visitor_comments", "controversy_reflection"
]

PERIOD_ORDER = ["新石器", "商周", "秦汉", "魏晋南北朝", "唐宋", "明清", "其他"]
TOMB_TYPES = ["帝王陵", "王侯墓", "贵族墓", "家族墓", "普通墓", "女性墓主", "儿童墓", "殉葬相关遗存", "祭祀坑/墓葬相关遗存", "壁画墓", "其他"]


def load_data() -> pd.DataFrame:
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
    else:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col not in NUMERIC_COLUMNS else 0
    return clean_and_score(df)


def clean_and_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in ["power_narrative", "gender_perspective", "commoner_perspective", "labor_perspective", "reflective_narrative", "controversy_reflection"]:
        df[col] = df[col].clip(0, 5)
    df["visitor_comments"] = df["visitor_comments"].clip(lower=0)
    # Tomb Inequality Index: high when elite power is emphasized and marginalized voices / reflection are weak.
    df["tomb_inequality_index"] = (
        0.30 * df["power_narrative"]
        + 0.20 * (5 - df["gender_perspective"])
        + 0.20 * (5 - df["commoner_perspective"])
        + 0.15 * (5 - df["labor_perspective"])
        + 0.15 * (5 - df["reflective_narrative"])
    ).round(2)
    df["public_reflection_score"] = (
        0.30 * df["gender_perspective"]
        + 0.25 * df["commoner_perspective"]
        + 0.20 * df["labor_perspective"]
        + 0.25 * df["reflective_narrative"]
    ).round(2)
    df["map_category"] = np.select(
        [
            (df["power_narrative"] >= 4) & (df["reflective_narrative"] <= 2),
            (df["reflective_narrative"] >= 4) & (df["public_reflection_score"] >= 3.2),
        ],
        ["红色：权力叙事强，反思不足", "绿色：较多呈现女性/普通人/社会差异"],
        default="黄色：文明叙事与部分反思并存",
    )
    df["marker_size"] = (df["tomb_inequality_index"] * 7 + df["visitor_comments"].clip(upper=1200) / 1200 * 18 + 8).round(1)
    df["hover_text"] = (
        df["museum_name"].astype(str) + "<br>" +
        df["province"].astype(str) + " · " + df["city"].astype(str) + "<br>" +
        "时代：" + df["period"].astype(str) + "<br>" +
        "墓葬类型：" + df["tomb_type"].astype(str) + "<br>" +
        "TII：" + df["tomb_inequality_index"].astype(str)
    )
    return df


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    output = io.StringIO()
    export_df = df[[c for c in REQUIRED_COLUMNS if c in df.columns]].copy()
    export_df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8-sig")


def get_filtered_data(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filters")
    periods = st.sidebar.multiselect("时代 Period", sorted(df["period"].dropna().unique()), default=sorted(df["period"].dropna().unique()))
    provinces = st.sidebar.multiselect("省份 Province", sorted(df["province"].dropna().unique()), default=sorted(df["province"].dropna().unique()))
    tii_range = st.sidebar.slider("Tomb Inequality Index", 0.0, 5.0, (0.0, 5.0), 0.1)
    keyword = st.sidebar.text_input("关键词搜索", placeholder="博物馆 / 展品 / 观察笔记")
    f = df[df["period"].isin(periods) & df["province"].isin(provinces)]
    f = f[(f["tomb_inequality_index"] >= tii_range[0]) & (f["tomb_inequality_index"] <= tii_range[1])]
    if keyword.strip():
        key = keyword.strip().lower()
        text_cols = ["museum_name", "city", "province", "featured_site_or_artifact", "archaeological_truth", "museum_framing", "visitor_perception", "ethical_question", "possible_change", "notes"]
        mask = pd.Series(False, index=f.index)
        for col in text_cols:
            mask = mask | f[col].astype(str).str.lower().str.contains(key, na=False)
        f = f[mask]
    return f


def make_map(df: pd.DataFrame):
    if df.empty:
        st.warning("当前筛选条件下没有数据。")
        return
    color_map = {
        "红色：权力叙事强，反思不足": "#d73027",
        "黄色：文明叙事与部分反思并存": "#fdae61",
        "绿色：较多呈现女性/普通人/社会差异": "#1a9850",
    }
    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        hover_name="museum_name",
        hover_data={
            "province": True,
            "city": True,
            "period": True,
            "tomb_type": True,
            "tomb_inequality_index": True,
            "public_reflection_score": True,
            "visitor_comments": True,
            "latitude": False,
            "longitude": False,
            "marker_size": False,
        },
        color="map_category",
        size="marker_size",
        color_discrete_map=color_map,
        zoom=3.1,
        center={"lat": 35.5, "lon": 104.0},
        height=680,
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="Map Meaning",
    )
    st.plotly_chart(fig, use_container_width=True)


def metric_row(df: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Museums", len(df))
    c2.metric("Avg. TII", f"{df['tomb_inequality_index'].mean():.2f}" if len(df) else "0")
    c3.metric("Avg. Public Reflection", f"{df['public_reflection_score'].mean():.2f}" if len(df) else "0")
    c4.metric("Visitor Comments", int(df["visitor_comments"].sum()) if len(df) else 0)


def make_analytics(df: pd.DataFrame):
    if df.empty:
        st.warning("没有可视化数据。")
        return

    st.subheader("1. 官方叙事与公共反思指标")
    chart_df = df.sort_values("tomb_inequality_index", ascending=False)
    fig1 = px.bar(
        chart_df,
        x="museum_name",
        y=["tomb_inequality_index", "public_reflection_score"],
        barmode="group",
        labels={"value": "Score", "museum_name": "Museum", "variable": "Metric"},
        height=430,
    )
    fig1.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("2. 不同时代的展陈叙事对比")
    period_df = df.groupby("period", as_index=False)[[
        "power_narrative", "gender_perspective", "commoner_perspective", "labor_perspective", "reflective_narrative", "tomb_inequality_index"
    ]].mean()
    period_df["period"] = pd.Categorical(period_df["period"], categories=PERIOD_ORDER, ordered=True)
    period_df = period_df.sort_values("period")
    fig2 = px.line(
        period_df,
        x="period",
        y=["power_narrative", "gender_perspective", "commoner_perspective", "labor_perspective", "reflective_narrative"],
        markers=True,
        labels={"value": "Average Score", "period": "Period", "variable": "Narrative Dimension"},
        height=430,
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("3. 权力叙事 vs 反思性叙事")
    fig3 = px.scatter(
        df,
        x="power_narrative",
        y="reflective_narrative",
        size="visitor_comments",
        color="period",
        hover_name="museum_name",
        hover_data=["province", "tomb_type", "tomb_inequality_index"],
        labels={"power_narrative": "Power Narrative Intensity", "reflective_narrative": "Reflective Narrative"},
        height=480,
    )
    fig3.add_shape(type="line", x0=0, y0=0, x1=5, y1=5, line=dict(dash="dash"))
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("4. 被忽略群体可见度热力图")
    heat_cols = ["gender_perspective", "commoner_perspective", "labor_perspective", "reflective_narrative"]
    heat_df = df.set_index("museum_name")[heat_cols].sort_values("reflective_narrative", ascending=False)
    fig4 = px.imshow(
        heat_df,
        text_auto=True,
        aspect="auto",
        labels={"x": "Dimension", "y": "Museum", "color": "Score"},
        height=max(420, 36 * len(heat_df)),
        zmin=0,
        zmax=5,
    )
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("5. 单馆五维雷达图")
    selected = st.selectbox("选择一个博物馆", df["museum_name"].tolist())
    row = df[df["museum_name"] == selected].iloc[0]
    radar_labels = ["权力叙事", "性别视角", "普通人视角", "劳动者视角", "反思叙事"]
    radar_values = [row["power_narrative"], row["gender_perspective"], row["commoner_perspective"], row["labor_perspective"], row["reflective_narrative"]]
    fig5 = go.Figure()
    fig5.add_trace(go.Scatterpolar(r=radar_values + [radar_values[0]], theta=radar_labels + [radar_labels[0]], fill="toself", name=selected))
    fig5.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), height=470)
    st.plotly_chart(fig5, use_container_width=True)


def make_detail_cards(df: pd.DataFrame):
    st.subheader("Museum Observation Cards")
    for _, row in df.sort_values("tomb_inequality_index", ascending=False).iterrows():
        with st.expander(f"🏺 {row['museum_name']} · TII {row['tomb_inequality_index']}"):
            c1, c2 = st.columns([1.05, 1.35])
            with c1:
                st.markdown(f"**地点：** {row['province']} · {row['city']}")
                st.markdown(f"**时代：** {row['period']}")
                st.markdown(f"**墓葬类型：** {row['tomb_type']}")
                st.markdown(f"**核心展品/遗址：** {row['featured_site_or_artifact']}")
                if str(row.get("official_url", "")).startswith("http"):
                    st.link_button("打开官方网站", row["official_url"])
            with c2:
                st.markdown("**Archaeological Truth / 考古真相**")
                st.write(row["archaeological_truth"])
                st.markdown("**Museum Framing / 博物馆叙事**")
                st.write(row["museum_framing"])
                st.markdown("**Visitor Perception / 观众理解**")
                st.write(row["visitor_perception"])
                st.markdown("**Ethical Question / 伦理问题**")
                st.write(row["ethical_question"])
                st.markdown("**Possible Change / 改变方向**")
                st.write(row["possible_change"])


def make_letter(df: pd.DataFrame):
    st.subheader("给博物馆的建议信生成器")
    if df.empty:
        st.warning("请先添加至少一个博物馆。")
        return
    selected = st.selectbox("选择要写信的博物馆", df["museum_name"].tolist(), key="letter_museum")
    row = df[df["museum_name"] == selected].iloc[0]
    student_name = st.text_input("署名", value="Sophie Zhou")
    tone = st.radio("语气", ["正式但真诚", "更学术", "更适合高中生项目"], horizontal=True)

    letter = f"""
尊敬的{row['museum_name']}展陈/公共教育部门老师：

您好！我是一名正在进行墓葬考古公共叙事研究的高中生。通过线上参观贵馆展览，我对“{row['featured_site_or_artifact']}”留下了非常深刻的印象。它不仅呈现了{row['period']}时期的物质文化与丧葬观念，也让我看到墓葬考古如何帮助现代观众理解古代社会中的权力、身份、性别与等级结构。

在整理观察笔记时，我注意到贵馆展陈非常有效地呈现了文物价值、历史背景与文明成就。同时，我也在思考：墓葬展品除了展示“文明辉煌”和“工艺成就”，是否也可以进一步引导观众看见这些文物背后的社会差异。例如，墓葬规模、陪葬品数量与材质往往反映了不同身份之间的资源差距；精美器物背后也有大量工匠、运输者和建造者的劳动，但这些普通人的名字往往没有被历史保留下来。

因此，我想提出几个小小的建议，供贵馆参考：

1. 在高等级墓葬或贵族陪葬品旁，增加与普通墓葬的对比说明，引导观众理解墓葬背后的社会分层。
2. 如果展品涉及女性墓主或女性形象，可以进一步呈现她们作为历史主体的身份，而不仅仅是家族、婚姻或礼制结构中的角色。
3. 在精美器物说明中适当加入工匠、材料来源和制作劳动的介绍，让观众看见文明成果背后的普通劳动者。
4. 增加面向青少年观众的互动问题，例如：“这座墓最想让后人记住什么？”“如果一个人的墓葬没有留下精美器物，他的生命是否就不重要？”

我目前正在制作一个名为“When Tombs Speak”的数字人文项目，尝试用互动地图和数据可视化比较不同博物馆如何呈现墓葬考古中的权力、性别、等级和死亡观。我真诚希望这个项目能够为博物馆公共教育提供一个青年观众的视角：我们不仅被古代文明震撼，也希望更完整地理解文明背后的复杂社会结构。

非常感谢贵馆在文物保护、研究与公共教育方面所做的重要工作。期待未来有机会继续学习贵馆的展览，也希望我的观察能为墓葬考古展陈提供一点小小的参考。

此致
敬礼！

{student_name}
""".strip()
    if tone == "更学术":
        letter = letter.replace("小小的建议", "基于公共考古与博物馆叙事视角的几点建议")
        letter = letter.replace("青年观众的视角", "来自青年研究者的公共人文视角")
    elif tone == "更适合高中生项目":
        letter = letter.replace("正在进行墓葬考古公共叙事研究的高中生", "对考古、博物馆教育和社会议题很感兴趣的高中生")

    st.text_area("生成的信件", value=letter, height=520)
    st.download_button("下载为 TXT", letter.encode("utf-8"), file_name=f"letter_to_{selected}.txt", mime="text/plain")


# -----------------------------
# Main App
# -----------------------------
st.markdown(
    f"""
    <div class="hero">
        <h1>🏺 {APP_TITLE}</h1>
        <p>{APP_SUBTITLE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("核心问题：当博物馆展示墓葬时，它是在展示文明，还是也在无意中美化权力？")

if "df" not in st.session_state:
    st.session_state.df = load_data()

uploaded = st.sidebar.file_uploader("上传你自己的 CSV 数据", type=["csv"])
if uploaded is not None:
    st.session_state.df = clean_and_score(pd.read_csv(uploaded))
    st.sidebar.success("已加载上传数据。")

filtered_df = get_filtered_data(st.session_state.df)
metric_row(filtered_df)

tab_map, tab_editor, tab_analytics, tab_cards, tab_letter, tab_method = st.tabs([
    "🗺️ Interactive Map", "✍️ Editable Database", "📊 Data Visualization", "🏛️ Observation Cards", "✉️ Museum Letter", "🧭 Methodology"
])

with tab_map:
    st.markdown("### 一张中国墓葬考古公共叙事地图")
    st.write("地图颜色代表展陈倾向，点大小综合体现 Tomb Inequality Index、观众评论量和争议/反思程度。")
    make_map(filtered_df)

with tab_editor:
    st.markdown("### 可编辑数据库")
    st.info("你可以直接在表格中修改数据。修改后点击下面的按钮保存到本地 CSV；部署到 Streamlit Cloud 时建议下载 CSV 后提交到 GitHub。")
    edited_df = st.data_editor(
        st.session_state.df[[c for c in REQUIRED_COLUMNS if c in st.session_state.df.columns]],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "latitude": st.column_config.NumberColumn("latitude", format="%.6f"),
            "longitude": st.column_config.NumberColumn("longitude", format="%.6f"),
            "period": st.column_config.SelectboxColumn("period", options=PERIOD_ORDER),
            "power_narrative": st.column_config.NumberColumn("power_narrative", min_value=0, max_value=5, step=1),
            "gender_perspective": st.column_config.NumberColumn("gender_perspective", min_value=0, max_value=5, step=1),
            "commoner_perspective": st.column_config.NumberColumn("commoner_perspective", min_value=0, max_value=5, step=1),
            "labor_perspective": st.column_config.NumberColumn("labor_perspective", min_value=0, max_value=5, step=1),
            "reflective_narrative": st.column_config.NumberColumn("reflective_narrative", min_value=0, max_value=5, step=1),
            "controversy_reflection": st.column_config.NumberColumn("controversy_reflection", min_value=0, max_value=5, step=1),
            "visitor_comments": st.column_config.NumberColumn("visitor_comments", min_value=0, step=1),
        },
        height=520,
    )
    col_save, col_download = st.columns([1, 1])
    with col_save:
        if st.button("💾 保存到 data/museums.csv", type="primary"):
            DATA_PATH.parent.mkdir(exist_ok=True)
            clean_and_score(edited_df)[REQUIRED_COLUMNS].to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
            st.session_state.df = clean_and_score(edited_df)
            st.success("已保存。")
    with col_download:
        st.download_button("⬇️ 下载 CSV", to_csv_bytes(clean_and_score(edited_df)), "museums.csv", "text/csv")

with tab_analytics:
    make_analytics(filtered_df)

with tab_cards:
    make_detail_cards(filtered_df)

with tab_letter:
    make_letter(filtered_df)

with tab_method:
    st.markdown("""
    ## Research Framework

    This project studies tomb archaeology not only as material culture, but also as public memory.

    ### Five-layer observation model

    1. **Archaeological Truth / 考古真相**：墓葬揭示了什么社会结构？
    2. **Museum Framing / 博物馆叙事**：博物馆如何解释它？强调辉煌、礼制、技术，还是社会差异？
    3. **Visitor Perception / 观众理解**：观众实际看到什么？震撼、审美、困惑，还是反思？
    4. **Ethical Question / 伦理问题**：这个真相带来什么现代问题？
    5. **Possible Change / 改变方向**：展陈、教育或公众讨论可以如何改进？

    ### Tomb Inequality Index

    The index is designed to capture whether a tomb display strongly centers elite power while underrepresenting women, common people, laborers, and reflective questions.

    ```text
    TII = 0.30 × Power Narrative
        + 0.20 × (5 - Gender Perspective)
        + 0.20 × (5 - Commoner Perspective)
        + 0.15 × (5 - Labor Perspective)
        + 0.15 × (5 - Reflective Narrative)
    ```

    A higher score does **not** mean the museum is “bad.” It means the exhibit may offer a useful case for asking how public history can move from displaying elite civilization toward presenting a fuller social memory.

    ### Data ethics

    - Visitor comments should be paraphrased or coded, not copied in large quantities.
    - Public comments should not include usernames or private information.
    - The scoring system is interpretive, so keep your coding notes transparent.
    - When sending suggestions to museums, use a constructive and respectful tone.
    """)
