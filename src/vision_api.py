"""
Vision API 연동 모듈
- Claude Vision API (기본)
- OpenAI GPT-4 Vision (대안)
- 다중 이미지 비교 분석 지원
"""

import base64
from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image
import io


class VisionAPIBase(ABC):
    """Vision API 추상 베이스 클래스"""

    @abstractmethod
    def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """단일 이미지 분석 요청"""
        pass

    @abstractmethod
    def analyze_multiple_images(self, images_data: list[bytes], prompt: str) -> str:
        """다중 이미지 비교 분석 요청"""
        pass

    @staticmethod
    def encode_image_to_base64(image_data: bytes) -> str:
        """이미지를 base64로 인코딩"""
        return base64.standard_b64encode(image_data).decode("utf-8")

    @staticmethod
    def get_image_media_type(image_data: bytes) -> str:
        """이미지 MIME 타입 감지"""
        img = Image.open(io.BytesIO(image_data))
        format_map = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "GIF": "image/gif",
            "WEBP": "image/webp"
        }
        return format_map.get(img.format, "image/jpeg")


class ClaudeVisionAPI(VisionAPIBase):
    """Claude Vision API 구현"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "claude-sonnet-4-20250514"

    def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """Claude Vision으로 단일 이미지 분석"""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        image_base64 = self.encode_image_to_base64(image_data)
        media_type = self.get_image_media_type(image_data)

        message = client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0,  # 일관된 결과를 위해 0으로 설정
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        return message.content[0].text

    def analyze_multiple_images(self, images_data: list[bytes], prompt: str) -> str:
        """Claude Vision으로 다중 이미지 비교 분석"""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        # 여러 이미지를 하나의 메시지에 포함
        content = []
        for idx, image_data in enumerate(images_data, 1):
            image_base64 = self.encode_image_to_base64(image_data)
            media_type = self.get_image_media_type(image_data)

            # 이미지 번호 표시
            content.append({
                "type": "text",
                "text": f"[이미지 {idx}]"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_base64,
                },
            })

        # 프롬프트 추가
        content.append({
            "type": "text",
            "text": prompt
        })

        message = client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=0,  # 일관된 결과를 위해 0으로 설정
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )

        return message.content[0].text


class OpenAIVisionAPI(VisionAPIBase):
    """OpenAI GPT-4 Vision API 구현"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4o"

    def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """GPT-4 Vision으로 단일 이미지 분석"""
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        image_base64 = self.encode_image_to_base64(image_data)
        media_type = self.get_image_media_type(image_data)

        response = client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            temperature=0,  # 일관된 결과를 위해 0으로 설정
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        return response.choices[0].message.content

    def analyze_multiple_images(self, images_data: list[bytes], prompt: str) -> str:
        """GPT-4 Vision으로 다중 이미지 비교 분석"""
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        # 여러 이미지를 하나의 메시지에 포함
        content = []
        for idx, image_data in enumerate(images_data, 1):
            image_base64 = self.encode_image_to_base64(image_data)
            media_type = self.get_image_media_type(image_data)

            # 이미지 번호 표시
            content.append({
                "type": "text",
                "text": f"[이미지 {idx}]"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_base64}"
                }
            })

        # 프롬프트 추가
        content.append({
            "type": "text",
            "text": prompt
        })

        response = client.chat.completions.create(
            model=self.model,
            max_tokens=8192,
            temperature=0,  # 일관된 결과를 위해 0으로 설정
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )

        return response.choices[0].message.content


def get_vision_api(provider: str, api_key: str) -> VisionAPIBase:
    """Vision API 인스턴스 팩토리"""
    providers = {
        "claude": ClaudeVisionAPI,
        "openai": OpenAIVisionAPI,
    }

    if provider not in providers:
        raise ValueError(f"지원하지 않는 API: {provider}. 사용 가능: {list(providers.keys())}")

    return providers[provider](api_key)
