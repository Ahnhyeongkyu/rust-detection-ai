"""
철 녹 정도 판별 AI - Streamlit 앱
"""

import streamlit as st
from PIL import Image
import io

from src.vision_api import get_vision_api
from src.rust_analyzer import RustAnalyzer, RustAnalysisResult


# 페이지 설정
st.set_page_config(
    page_title="철 녹 정도 판별 AI",
    page_icon="🔧",
    layout="centered"
)

# 커스텀 CSS
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
    """순위에 따른 이모지 반환 (녹이 심한 순)"""
    if rank == 1:
        return "🔴"  # 가장 녹이 심함
    elif rank == total:
        return "🟢"  # 가장 깨끗함
    else:
        return f"{rank}위"


def get_grade_class(grade: str) -> str:
    """등급에 따른 CSS 클래스 반환"""
    grade_map = {
        "심각": "grade-severe",
        "보통": "grade-moderate",
        "경미": "grade-mild",
        "정상": "grade-normal"
    }
    return grade_map.get(grade, "grade-moderate")


def get_grade_emoji(grade: str) -> str:
    """등급에 따른 이모지 반환"""
    emoji_map = {
        "심각": "🔴",
        "보통": "🟠",
        "경미": "🟡",
        "정상": "🟢"
    }
    return emoji_map.get(grade, "⚪")


def display_single_result(result: RustAnalysisResult, image=None, rank: int = None, total: int = 1):
    """단일 분석 결과 표시"""

    if not result.is_metal_rod:
        st.error(result.error_message or "철 막대가 아닌 이미지입니다.")
        return

    grade_class = get_grade_class(result.rust_grade)
    grade_emoji = get_grade_emoji(result.rust_grade)

    # 순위 표시 (다중 이미지일 때만)
    if rank and total > 1:
        if rank == 1:
            st.markdown('<div class="worst-banner">🔴 가장 녹이 심함 🔴</div>', unsafe_allow_html=True)
        elif rank == total:
            st.markdown('<div style="background: linear-gradient(135deg, #228B22 0%, #32CD32 100%); color: white; padding: 10px 20px; border-radius: 25px; text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 15px;">🟢 가장 깨끗함 🟢</div>', unsafe_allow_html=True)

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
            <div style="font-size: 14px; margin-bottom: 5px;">녹 등급</div>
            <div style="font-size: 32px; font-weight: bold;">{grade_emoji} {result.rust_grade}</div>
            <div style="font-size: 24px; margin-top: 10px;">녹 범위: {result.rust_percentage or "분석 중"}</div>
        </div>
        """, unsafe_allow_html=True)

        # 점수 표시
        if result.rust_score is not None:
            st.markdown(f"""
            <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <span style="font-size: 14px;">녹 점수:</span>
                <span style="font-size: 28px; font-weight: bold; color: #8B4513;"> {result.rust_score}점</span>
                <span style="font-size: 12px; color: #888;"> / 100 (높을수록 녹이 심함)</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"**신뢰도:** {result.confidence_score}%")

    # 상세 분석
    with st.expander("📊 상세 분석 보기", expanded=(rank == 1 if rank else True)):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**🎨 색상 변화**")
            st.caption(result.color_analysis)
        with col_b:
            st.markdown("**✨ 표면 상태**")
            st.caption(result.surface_analysis)
        with col_c:
            st.markdown("**🔧 부식 정도**")
            st.caption(result.corrosion_analysis)

        st.markdown("---")
        st.markdown(f"**💡 종합 판단:** {result.analysis_reason}")


def main():
    # 헤더
    st.markdown("<h1 class='main-title'>🔧 철 녹 정도 판별 AI</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>철 막대 사진을 업로드하면 AI가 녹 정도를 분석합니다</p>", unsafe_allow_html=True)

    # 사이드바 - API 설정
    with st.sidebar:
        st.header("⚙️ API 설정")

        api_provider = st.selectbox(
            "AI 모델 선택",
            options=["claude", "openai"],
            format_func=lambda x: "Claude (Anthropic) - 추천" if x == "claude" else "GPT-4o (OpenAI)",
            index=0
        )

        api_key = st.text_input(
            "API Key 입력",
            type="password",
            help="선택한 AI 서비스의 API 키를 입력하세요."
        )

        # API 키 발급 안내
        with st.expander("🔑 API 키 발급 방법"):
            if api_provider == "openai":
                st.markdown("""
                **OpenAI (GPT-4)**
                1. [platform.openai.com](https://platform.openai.com/) 접속
                2. 회원가입 또는 로그인
                3. API Keys 메뉴 → 새 키 생성
                4. 크레딧 충전 필요
                """)
            else:
                st.markdown("""
                **Anthropic (Claude)**
                1. [console.anthropic.com](https://console.anthropic.com/) 접속
                2. 회원가입 또는 로그인
                3. API Keys 메뉴 → 새 키 생성
                4. 크레딧 충전 필요 (최소 $5)
                """)

        st.divider()

        # 사용 안내
        st.header("📖 사용 방법")
        st.markdown("""
        1. API 키 입력
        2. 철 막대 사진 업로드 (최대 5장)
        3. '분석하기' 클릭
        4. 결과 확인!

        **여러 장 업로드 시**
        AI가 직접 비교하여 녹이 심한 순서대로 순위를 매깁니다.
        """)

        st.divider()

        # 등급 안내
        st.header("📋 등급 기준")
        st.markdown("""
        - 🟢 **정상**: 녹 거의 없음 (0~10%)
        - 🟡 **경미**: 약간의 녹 (10~30%)
        - 🟠 **보통**: 상당한 녹 (30~70%)
        - 🔴 **심각**: 심한 녹/부식 (70~100%)
        """)

        st.divider()
        st.caption("""
        ⚠️ **주의사항**
        - AI 기반 외관 분석입니다
        - 실제 부식 정도와 차이가 있을 수 있습니다
        - 참고용으로만 사용해주세요
        """)

    # 메인 영역 - 이미지 업로드
    st.subheader("📤 철 막대 사진 업로드")

    uploaded_files = st.file_uploader(
        "이미지를 선택하세요 (최대 5장)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="JPG, PNG, WEBP 형식 지원. 10MB 이하 권장."
    )

    # 업로드된 파일 수 제한
    if uploaded_files and len(uploaded_files) > 5:
        st.warning("⚠️ 최대 5장까지 업로드 가능합니다. 처음 5장만 분석합니다.")
        uploaded_files = uploaded_files[:5]

    # 업로드된 이미지 미리보기
    if uploaded_files:
        st.markdown(f"**업로드된 이미지: {len(uploaded_files)}장**")
        cols = st.columns(min(len(uploaded_files), 5))
        for idx, (col, file) in enumerate(zip(cols, uploaded_files)):
            with col:
                img = Image.open(file)
                st.image(img, caption=f"#{idx+1}", use_container_width=True)

    # 분석 버튼
    st.divider()

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        analyze_btn = st.button(
            "🔍 분석하기",
            type="primary",
            use_container_width=True,
            disabled=not (api_key and uploaded_files)
        )

    if not api_key:
        st.info("👈 사이드바에서 API 키를 입력해주세요.")
    elif not uploaded_files:
        st.info("📤 철 막대 사진을 업로드해주세요.")

    # 분석 실행
    if analyze_btn and api_key and uploaded_files:
        try:
            # Vision API 초기화
            vision_api = get_vision_api(api_provider, api_key)
            analyzer = RustAnalyzer(vision_api)

            with st.spinner("🔧 AI가 철 막대를 분석하고 있습니다..."):
                if len(uploaded_files) == 1:
                    # 단일 이미지 분석
                    file = uploaded_files[0]
                    file.seek(0)
                    image_data = file.read()
                    result = analyzer.analyze(image_data)

                    st.subheader("📋 분석 결과")
                    file.seek(0)
                    img = Image.open(file)
                    display_single_result(result, image=img)

                else:
                    # 다중 이미지 비교 분석
                    images = []
                    image_objects = {}

                    for file in uploaded_files:
                        file.seek(0)
                        image_data = file.read()
                        images.append((file.name, image_data))

                        file.seek(0)
                        image_objects[file.name] = Image.open(file)

                    results = analyzer.analyze_multiple(images)

                    st.subheader("🔍 분석 결과 (녹이 심한 순)")
                    st.markdown("AI가 모든 이미지를 직접 비교하여 순위를 매겼습니다.")

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
                st.error("❌ API 크레딧이 부족합니다")
                st.info("""
                **해결 방법:**
                - **Claude**: [console.anthropic.com](https://console.anthropic.com) → Plans & Billing → 크레딧 충전
                - **OpenAI**: [platform.openai.com](https://platform.openai.com) → Billing → 크레딧 충전

                크레딧 충전 후 다시 시도해주세요.
                """)
            elif "api_key" in error_msg.lower() or "invalid" in error_msg.lower() or "authentication" in error_msg.lower():
                st.error("❌ API 키가 올바르지 않습니다")
                st.info("API 키를 다시 확인해주세요. 키는 'sk-' 또는 'sk-ant-'로 시작합니다.")
            elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                st.error("❌ API 요청 한도 초과")
                st.info("잠시 후 다시 시도해주세요.")
            else:
                st.error(f"❌ 분석 중 오류가 발생했습니다")
                st.caption(f"상세: {error_msg[:200]}")

    # 푸터
    st.divider()
    st.markdown("""
    <div class='disclaimer'>
    이 서비스는 철 막대의 외관을 AI로 분석하여 녹 정도를 <b>추정</b>합니다.<br>
    실제 부식 정도와는 차이가 있을 수 있으며, <b>참고용</b>으로만 사용해주세요.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
