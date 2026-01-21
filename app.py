"""
Rust Detection AI - Streamlit App
"""

import streamlit as st
from PIL import Image
import io

from src.vision_api import get_vision_api
from src.rust_analyzer import RustAnalyzer, RustAnalysisResult


# Page config
st.set_page_config(
    page_title="Rust Detection AI",
    page_icon="🔧",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #8B4513;
        margin-bottom: 10px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 16px;
        margin-bottom: 30px;
    }
    .rank-badge {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
        padding: 10px;
    }
    .rank-1 { color: #8B0000; }
    .rank-2 { color: #CD853F; }
    .rank-3 { color: #DAA520; }
    .rank-other { color: #888; }
    .score-display {
        font-size: 36px;
        font-weight: bold;
        text-align: center;
    }
    .grade-severe {
        color: #8B0000;
        background: linear-gradient(135deg, #FFE4E1 0%, #FFC0CB 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #8B0000;
    }
    .grade-moderate {
        color: #CD853F;
        background: linear-gradient(135deg, #FFECD2 0%, #FCB69F 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #CD853F;
    }
    .grade-mild {
        color: #DAA520;
        background: linear-gradient(135deg, #FFF8DC 0%, #FFFACD 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #DAA520;
    }
    .grade-normal {
        color: #228B22;
        background: linear-gradient(135deg, #F0FFF0 0%, #98FB98 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #228B22;
    }
    .disclaimer {
        font-size: 12px;
        color: #888;
        text-align: center;
        margin-top: 20px;
    }
    .worst-banner {
        background: linear-gradient(135deg, #8B0000 0%, #CD5C5C 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 25px;
        text-align: center;
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)


def get_rank_emoji(rank: int, total: int) -> str:
    """Return emoji based on rank (most rusted first)"""
    if rank == 1:
        return "🔴"  # Most rusted
    elif rank == total:
        return "🟢"  # Cleanest
    else:
        return f"#{rank}"


def get_grade_class(grade: str) -> str:
    """Return CSS class based on grade"""
    grade_map = {
        "심각": "grade-severe",
        "보통": "grade-moderate",
        "경미": "grade-mild",
        "정상": "grade-normal",
        "Severe": "grade-severe",
        "Moderate": "grade-moderate",
        "Mild": "grade-mild",
        "Normal": "grade-normal"
    }
    return grade_map.get(grade, "grade-moderate")


def get_grade_emoji(grade: str) -> str:
    """Return emoji based on grade"""
    emoji_map = {
        "심각": "🔴",
        "보통": "🟠",
        "경미": "🟡",
        "정상": "🟢",
        "Severe": "🔴",
        "Moderate": "🟠",
        "Mild": "🟡",
        "Normal": "🟢"
    }
    return emoji_map.get(grade, "⚪")


def translate_grade(grade: str) -> str:
    """Translate Korean grade to English"""
    translations = {"심각": "Severe", "보통": "Moderate", "경미": "Mild", "정상": "Normal"}
    return translations.get(grade, grade)


def display_single_result(result: RustAnalysisResult, image=None, rank: int = None, total: int = 1):
    """Display single analysis result"""

    if not result.is_metal_rod:
        st.error(result.error_message or "This image does not appear to be a metal rod.")
        return

    grade_class = get_grade_class(result.rust_grade)
    grade_emoji = get_grade_emoji(result.rust_grade)
    display_grade = translate_grade(result.rust_grade)

    # Rank display (only for multiple images)
    if rank and total > 1:
        if rank == 1:
            st.markdown('<div class="worst-banner">🔴 Most Rusted 🔴</div>', unsafe_allow_html=True)
        elif rank == total:
            st.markdown('<div style="background: linear-gradient(135deg, #228B22 0%, #32CD32 100%); color: white; padding: 10px 20px; border-radius: 25px; text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 15px;">🟢 Cleanest 🟢</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        if image:
            st.image(image, use_container_width=True)
        if rank and total > 1:
            rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
            st.markdown(f'<div class="rank-badge {rank_class}">{get_rank_emoji(rank, total)}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="{grade_class}">
            <div style="font-size: 14px; margin-bottom: 5px;">Rust Grade</div>
            <div style="font-size: 32px; font-weight: bold;">{grade_emoji} {display_grade}</div>
            <div style="font-size: 24px; margin-top: 10px;">Rust Coverage: {result.rust_percentage or "Analyzing"}</div>
        </div>
        """, unsafe_allow_html=True)

        # Score display
        if result.rust_score is not None:
            st.markdown(f"""
            <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <span style="font-size: 14px;">Rust Score:</span>
                <span style="font-size: 28px; font-weight: bold; color: #8B4513;"> {result.rust_score}</span>
                <span style="font-size: 12px; color: #888;"> / 100 (higher = more rust)</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"**Confidence:** {result.confidence_score}%")

    # Detailed analysis
    with st.expander("📊 View Detailed Analysis", expanded=(rank == 1 if rank else True)):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**🎨 Color Change**")
            st.caption(result.color_analysis)
        with col_b:
            st.markdown("**✨ Surface Condition**")
            st.caption(result.surface_analysis)
        with col_c:
            st.markdown("**🔧 Corrosion Level**")
            st.caption(result.corrosion_analysis)

        st.markdown("---")
        st.markdown(f"**💡 Summary:** {result.analysis_reason}")


def main():
    # Header
    st.markdown("<h1 class='main-title'>🔧 Rust Detection AI</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Upload metal rod photos and AI will analyze rust levels</p>", unsafe_allow_html=True)

    # Sidebar - API settings
    with st.sidebar:
        st.header("⚙️ API Settings")

        api_provider = st.selectbox(
            "Select AI Model",
            options=["claude", "openai"],
            format_func=lambda x: "Claude (Anthropic) - Recommended" if x == "claude" else "GPT-4o (OpenAI)",
            index=0
        )

        api_key = st.text_input(
            "Enter API Key",
            type="password",
            help="Enter your API key for the selected AI service."
        )

        # API key guide
        with st.expander("🔑 How to Get API Key"):
            if api_provider == "openai":
                st.markdown("""
                **OpenAI (GPT-4)**
                1. Visit [platform.openai.com](https://platform.openai.com/)
                2. Sign up or log in
                3. Go to API Keys → Create new key
                4. Add credits
                """)
            else:
                st.markdown("""
                **Anthropic (Claude)**
                1. Visit [console.anthropic.com](https://console.anthropic.com/)
                2. Sign up or log in
                3. Go to API Keys → Create new key
                4. Add credits (minimum $5)
                """)

        st.divider()

        # Usage guide
        st.header("📖 How to Use")
        st.markdown("""
        1. Enter API key
        2. Upload metal rod photos (up to 5)
        3. Click 'Analyze'
        4. View results!

        **Multiple Images**
        AI will compare all images and rank them by rust severity.
        """)

        st.divider()

        # Grade guide
        st.header("📋 Grade Criteria")
        st.markdown("""
        - 🟢 **Normal**: Little to no rust (0-10%)
        - 🟡 **Mild**: Light rust (10-30%)
        - 🟠 **Moderate**: Significant rust (30-70%)
        - 🔴 **Severe**: Heavy rust/corrosion (70-100%)
        """)

        st.divider()
        st.caption("""
        ⚠️ **Note**
        - AI-based visual analysis
        - Actual corrosion may vary
        - For reference only
        """)

    # Main area - Image upload
    st.subheader("📤 Upload Metal Rod Photos")

    uploaded_files = st.file_uploader(
        "Select images (up to 5)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Supports JPG, PNG, WEBP. Under 10MB recommended."
    )

    # Limit uploaded files
    if uploaded_files and len(uploaded_files) > 5:
        st.warning("⚠️ Maximum 5 images allowed. Only first 5 will be analyzed.")
        uploaded_files = uploaded_files[:5]

    # Preview uploaded images
    if uploaded_files:
        st.markdown(f"**Uploaded: {len(uploaded_files)} image(s)**")
        cols = st.columns(min(len(uploaded_files), 5))
        for idx, (col, file) in enumerate(zip(cols, uploaded_files)):
            with col:
                img = Image.open(file)
                st.image(img, caption=f"#{idx+1}", use_container_width=True)

    # Analyze button
    st.divider()

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        analyze_btn = st.button(
            "🔍 Analyze",
            type="primary",
            use_container_width=True,
            disabled=not (api_key and uploaded_files)
        )

    if not api_key:
        st.info("👈 Please enter your API key in the sidebar.")
    elif not uploaded_files:
        st.info("📤 Please upload metal rod photos.")

    # Run analysis
    if analyze_btn and api_key and uploaded_files:
        try:
            # Initialize Vision API
            vision_api = get_vision_api(api_provider, api_key)
            analyzer = RustAnalyzer(vision_api)

            with st.spinner("🔧 AI is analyzing the metal rods..."):
                if len(uploaded_files) == 1:
                    # Single image analysis
                    file = uploaded_files[0]
                    file.seek(0)
                    image_data = file.read()
                    result = analyzer.analyze(image_data)

                    st.subheader("📋 Analysis Result")
                    file.seek(0)
                    img = Image.open(file)
                    display_single_result(result, image=img)

                else:
                    # Multiple image comparison
                    images = []
                    image_objects = {}

                    for file in uploaded_files:
                        file.seek(0)
                        image_data = file.read()
                        images.append((file.name, image_data))

                        file.seek(0)
                        image_objects[file.name] = Image.open(file)

                    results = analyzer.analyze_multiple(images)

                    st.subheader("🔍 Results (Ranked by Rust Severity)")
                    st.markdown("AI compared all images and ranked them.")

                    for filename, result in results:
                        st.markdown("---")
                        display_single_result(
                            result,
                            image=image_objects.get(filename),
                            rank=result.rank,
                            total=len(results)
                        )

        except Exception as e:
            error_msg = str(e)
            if "credit" in error_msg.lower() or "balance" in error_msg.lower():
                st.error("❌ Insufficient API credits")
                st.info("""
                **How to fix:**
                - **Claude**: [console.anthropic.com](https://console.anthropic.com) → Plans & Billing → Add credits
                - **OpenAI**: [platform.openai.com](https://platform.openai.com) → Billing → Add credits

                Please add credits and try again.
                """)
            elif "api_key" in error_msg.lower() or "invalid" in error_msg.lower() or "authentication" in error_msg.lower():
                st.error("❌ Invalid API key")
                st.info("Please check your API key. Keys start with 'sk-' or 'sk-ant-'.")
            elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                st.error("❌ API rate limit exceeded")
                st.info("Please wait a moment and try again.")
            else:
                st.error(f"❌ An error occurred during analysis")
                st.caption(f"Details: {error_msg[:200]}")

    # Footer
    st.divider()
    st.markdown("""
    <div class='disclaimer'>
    This service uses AI to <b>estimate</b> rust levels based on visual analysis.<br>
    Actual corrosion may differ. For <b>reference only</b>.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
