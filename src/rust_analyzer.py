"""
철 녹 정도 분석 모듈
- Vision API를 활용한 외관 분석
- 녹 정도 등급 판별 (정상/경미/보통/심각)
- 다중 이미지 상대 비교
"""

import json
import re
from dataclasses import dataclass
from typing import Optional
from src.vision_api import VisionAPIBase


@dataclass
class RustAnalysisResult:
    """철 녹 분석 결과"""
    is_metal_rod: bool
    rust_grade: Optional[str] = None  # 정상, 경미, 보통, 심각
    rust_percentage: Optional[str] = None  # 예: "10~20%"
    rust_score: Optional[int] = None  # 0-100 (높을수록 녹이 많음)
    confidence_score: Optional[int] = None  # 1-100
    rank: Optional[int] = None  # 순위 (다중 비교 시)
    analysis_reason: Optional[str] = None  # 분석 근거
    color_analysis: Optional[str] = None  # 색상 분석
    surface_analysis: Optional[str] = None  # 표면 상태
    corrosion_analysis: Optional[str] = None  # 부식 분석
    error_message: Optional[str] = None


# 단일 이미지 분석용 프롬프트
SINGLE_ANALYSIS_PROMPT = """당신은 금속 부식/녹 감별 전문가입니다. 철 막대의 녹 정도를 분석해주세요.

## 분석 대상
- 얇고 기다란 철 막대 (쇠)
- 코팅이 있거나 없을 수 있음
- 녹(rust)의 정도를 판별

## 평가 기준 (각 항목 0-100점, 점수가 높을수록 녹이 심함)

### 1. 색상 변화 점수 (40% 비중)
- 90-100: 전체가 짙은 갈색/적갈색 녹으로 덮임
- 70-89: 대부분 녹 색상, 원래 금속색 거의 안 보임
- 50-69: 녹 색상이 상당 부분 차지
- 30-49: 부분적 녹 색상, 원래 색상 많이 보임
- 10-29: 약간의 변색만 있음
- 0-9: 녹 색상 거의 없음, 깨끗한 금속색

### 2. 녹 범위 점수 (35% 비중)
- 90-100: 표면 90% 이상 녹
- 70-89: 표면 60-90% 녹
- 50-69: 표면 30-60% 녹
- 30-49: 표면 10-30% 녹
- 10-29: 표면 5-10% 녹
- 0-9: 표면 5% 미만 녹

### 3. 부식 상태 점수 (25% 비중)
- 90-100: 심한 부식, 표면 손상, 구멍/박리 있음
- 70-89: 상당한 부식, 표면 거칠어짐
- 50-69: 중간 부식, 질감 변화 있음
- 30-49: 경미한 부식, 약간의 질감 변화
- 10-29: 매우 경미한 표면 변화
- 0-9: 부식 없음, 매끈한 표면

## 녹 등급 기준 (총점 기준) - 반드시 4단계만 사용
- **심각** (rust_percentage: 70~100%): 총점 75점 이상
- **보통** (rust_percentage: 30~70%): 총점 50-74점
- **경미** (rust_percentage: 10~30%): 총점 25-49점
- **정상** (rust_percentage: 0~10%): 총점 25점 미만

## 응답 형식 (JSON만 출력)
```json
{
  "is_metal_rod": true,
  "color_score": 0-100,
  "coverage_score": 0-100,
  "corrosion_score": 0-100,
  "rust_score": 0-100,
  "rust_grade": "정상" 또는 "경미" 또는 "보통" 또는 "심각",
  "rust_percentage_min": 숫자,
  "rust_percentage_max": 숫자,
  "confidence_score": 0-100,
  "color_analysis": "색상 분석 (구체적 근거)",
  "surface_analysis": "표면 상태 분석 (구체적 근거)",
  "corrosion_analysis": "부식 정도 분석 (구체적 근거)",
  "analysis_reason": "종합 판단 (왜 이 등급인지)"
}
```

**중요**:
- rust_grade는 반드시 "정상", "경미", "보통", "심각" 중 하나만 사용하세요.
- 다른 표현 절대 금지!
- 철 막대가 아니면 is_metal_rod: false로 응답
- 코팅이 벗겨진 부분도 녹으로 간주할 수 있음

이미지를 분석해주세요."""


# 다중 이미지 상대 비교용 프롬프트
MULTI_COMPARISON_PROMPT = """당신은 금속 부식/녹 감별 전문가입니다.
{count}장의 철 막대 이미지를 비교하여 녹이 심한 순서대로 순위를 매겨주세요.

## 비교 기준
1. **색상 변화**: 갈색/적갈색 녹 색상이 많을수록 녹이 심함
2. **녹 범위**: 표면에서 녹이 차지하는 비율
3. **부식 정도**: 표면 손상, 질감 변화 정도

## 중요 지침
- 이미지 간 **상대적 차이**를 반드시 구분하세요
- 아무리 비슷해 보여도 미세한 차이를 찾아 순위를 명확히 매기세요
- 동점 없이 1위(가장 녹이 심함)부터 {count}위(가장 깨끗함)까지 모두 다른 순위를 부여하세요
- 각 이미지의 rust_score는 최소 5점 이상 차이나게 해주세요

## 녹 등급 기준 - 반드시 4단계만 사용
- **심각** (70~100%): 총점 75점 이상
- **보통** (30~70%): 총점 50-74점
- **경미** (10~30%): 총점 25-49점
- **정상** (0~10%): 총점 25점 미만

## 응답 형식 (JSON 배열로 출력, 녹이 심한 순)
```json
[
  {{
    "image_index": 1,
    "rank": 1,
    "rust_score": 85,
    "rust_grade": "심각",
    "rust_percentage_min": 70,
    "rust_percentage_max": 100,
    "confidence_score": 85,
    "color_analysis": "색상 분석",
    "surface_analysis": "표면 분석",
    "corrosion_analysis": "부식 분석",
    "analysis_reason": "왜 이 순위인지 다른 이미지와 비교하여 설명",
    "comparison_note": "다른 이미지 대비 어떤 점이 더 녹이 심한지/덜한지"
  }},
  ...
]
```

**중요**: rust_grade는 반드시 "정상", "경미", "보통", "심각" 중 하나만 사용!

{count}장의 이미지를 순서대로 분석하고, 녹이 심한 순으로 순위를 매겨주세요.
첫 번째 이미지가 image_index: 1, 두 번째가 image_index: 2 입니다."""


class RustAnalyzer:
    """철 녹 정도 분석기"""

    def __init__(self, vision_api: VisionAPIBase):
        self.vision_api = vision_api

    def analyze(self, image_data: bytes) -> RustAnalysisResult:
        """단일 철 막대 이미지 분석"""
        try:
            response = self.vision_api.analyze_image(
                image_data=image_data,
                prompt=SINGLE_ANALYSIS_PROMPT
            )
            return self._parse_single_response(response)

        except Exception as e:
            return RustAnalysisResult(
                is_metal_rod=False,
                error_message=f"분석 중 오류 발생: {str(e)}"
            )

    def _parse_single_response(self, response: str) -> RustAnalysisResult:
        """단일 분석 API 응답 파싱"""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            data = json.loads(json_str)

            if not data.get("is_metal_rod", False):
                return RustAnalysisResult(
                    is_metal_rod=False,
                    error_message="철 막대가 아닌 이미지입니다. 철 막대 사진을 업로드해주세요."
                )

            rust_min = data.get("rust_percentage_min")
            rust_max = data.get("rust_percentage_max")
            rust_percentage = f"{rust_min}~{rust_max}%" if rust_min is not None and rust_max is not None else None

            return RustAnalysisResult(
                is_metal_rod=True,
                rust_grade=data.get("rust_grade"),
                rust_percentage=rust_percentage,
                rust_score=data.get("rust_score"),
                confidence_score=data.get("confidence_score"),
                analysis_reason=data.get("analysis_reason"),
                color_analysis=data.get("color_analysis"),
                surface_analysis=data.get("surface_analysis"),
                corrosion_analysis=data.get("corrosion_analysis"),
            )

        except json.JSONDecodeError:
            return RustAnalysisResult(
                is_metal_rod=False,
                error_message="분석 결과를 파싱할 수 없습니다. 다시 시도해주세요."
            )

    def analyze_multiple(self, images: list[tuple[str, bytes]]) -> list[tuple[str, RustAnalysisResult]]:
        """
        여러 철 막대 이미지 상대 비교 분석
        - 모든 이미지를 한 번에 Vision API로 전송
        - AI가 직접 상대 비교하여 순위 결정 (녹이 심한 순)
        """
        if len(images) == 1:
            # 단일 이미지는 기존 방식
            filename, image_data = images[0]
            result = self.analyze(image_data)
            result.rank = 1
            return [(filename, result)]

        try:
            # 다중 이미지 비교 분석
            prompt = MULTI_COMPARISON_PROMPT.format(count=len(images))
            response = self.vision_api.analyze_multiple_images(
                images_data=[img_data for _, img_data in images],
                prompt=prompt
            )

            results = self._parse_multi_response(response, images)
            return results

        except Exception as e:
            # 다중 분석 실패 시 개별 분석으로 폴백
            return self._fallback_individual_analysis(images, str(e))

    def _parse_multi_response(self, response: str, images: list[tuple[str, bytes]]) -> list[tuple[str, RustAnalysisResult]]:
        """다중 비교 응답 파싱"""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            data_list = json.loads(json_str)

            results = []
            for data in data_list:
                img_idx = data.get("image_index", 1) - 1
                if 0 <= img_idx < len(images):
                    filename = images[img_idx][0]

                    rust_min = data.get("rust_percentage_min")
                    rust_max = data.get("rust_percentage_max")
                    rust_percentage = f"{rust_min}~{rust_max}%" if rust_min is not None and rust_max is not None else None

                    comparison_note = data.get("comparison_note", "")
                    analysis_reason = data.get("analysis_reason", "")
                    if comparison_note:
                        analysis_reason = f"{analysis_reason} ({comparison_note})"

                    result = RustAnalysisResult(
                        is_metal_rod=True,
                        rust_grade=data.get("rust_grade"),
                        rust_percentage=rust_percentage,
                        rust_score=data.get("rust_score"),
                        confidence_score=data.get("confidence_score"),
                        rank=data.get("rank"),
                        analysis_reason=analysis_reason,
                        color_analysis=data.get("color_analysis"),
                        surface_analysis=data.get("surface_analysis"),
                        corrosion_analysis=data.get("corrosion_analysis"),
                    )
                    results.append((filename, result))

            # 순위 기준 정렬
            results.sort(key=lambda x: x[1].rank if x[1].rank else 999)
            return results

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # 파싱 실패 시 개별 분석으로 폴백
            return self._fallback_individual_analysis(images, str(e))

    def _fallback_individual_analysis(self, images: list[tuple[str, bytes]], error_msg: str = "") -> list[tuple[str, RustAnalysisResult]]:
        """개별 분석 폴백 (다중 비교 실패 시)"""
        results = []

        for filename, image_data in images:
            result = self.analyze(image_data)
            results.append((filename, result))

        # rust_score 기준 정렬 (높은 순 = 녹이 심한 순)
        def sort_key(item):
            _, result = item
            if not result.is_metal_rod:
                return -1
            return result.rust_score or 0

        results.sort(key=sort_key, reverse=True)

        # 순위 부여
        for rank, (filename, result) in enumerate(results, 1):
            result.rank = rank

        return results
