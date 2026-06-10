"""외형 개념 형상 — 텍스트로 차 스타일을 묘사하는 파라메트릭 컨셉.

자연어에서 차종·루프라인·비례·스탠스·휠을 읽어 ConceptSpec에 채운다.
이 파라미터들이 mesh.build_car_mesh에서 실제 3D 실루엣으로 반영된다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace


@dataclass
class ConceptSpec:
    name: str
    length_mm: float = 4500.0
    width_mm: float = 1850.0
    height_mm: float = 1400.0
    streamline: float = 0.5          # 0(둔함)~1(매끈) — 공력 형상 지표
    target_cd: float = 0.30          # 목표 항력계수

    # --- 스타일 파라미터 (텍스트로 제어) ---
    body_type: str = "coupe"         # coupe|sedan|suv|hatch|wagon|pickup
    roofline: str = "fastback"       # fastback|notchback|suv|wagon
    hood_frac: float = 0.42          # 전장 대비 보닛 길이(롱노즈↑)
    cab_frac: float = 0.34           # 캐빈(루프) 길이 비율
    ride_height_mm: float = 150.0    # 지상고(낮음~SUV 높음)
    wheel_dia_mm: float = 660.0      # 휠 외경(대구경↑)
    overhang: float = 0.5            # 0(짧은 오버행/롱휠베이스)~1(긴 오버행)

    def frontal_area_m2(self) -> float:
        return (self.width_mm * 1e-3) * (self.height_mm * 1e-3) * 0.85


# 차종별 기본 프리셋(텍스트 키워드로 선택)
_PRESETS = {
    "supercar": dict(body_type="coupe", roofline="fastback", length_mm=4550, width_mm=2000,
                     height_mm=1180, streamline=0.85, hood_frac=0.30, cab_frac=0.40,
                     ride_height_mm=110, wheel_dia_mm=700, overhang=0.25, target_cd=0.32),
    "coupe":   dict(body_type="coupe", roofline="fastback", height_mm=1330, streamline=0.70,
                    hood_frac=0.46, cab_frac=0.32, ride_height_mm=140, wheel_dia_mm=680),
    "sedan":   dict(body_type="sedan", roofline="notchback", height_mm=1460, streamline=0.45,
                    hood_frac=0.40, cab_frac=0.40, ride_height_mm=150, wheel_dia_mm=650),
    "hatch":   dict(body_type="hatch", roofline="fastback", length_mm=4100, height_mm=1450,
                    streamline=0.40, hood_frac=0.34, cab_frac=0.42, ride_height_mm=150),
    "wagon":   dict(body_type="wagon", roofline="wagon", height_mm=1480, streamline=0.42,
                    hood_frac=0.38, cab_frac=0.48, ride_height_mm=160),
    "suv":     dict(body_type="suv", roofline="suv", length_mm=4700, width_mm=1920,
                    height_mm=1720, streamline=0.30, hood_frac=0.34, cab_frac=0.48,
                    ride_height_mm=300, wheel_dia_mm=760, target_cd=0.34),
    "pickup":  dict(body_type="pickup", roofline="suv", length_mm=5300, width_mm=1980,
                    height_mm=1820, streamline=0.28, hood_frac=0.34, cab_frac=0.34,
                    ride_height_mm=330, wheel_dia_mm=800, target_cd=0.40),
}


class MockConceptGenerator:
    """자연어 → 개념 형상. 차종 프리셋 + 스타일 수식어 파싱.

    (고품질·사진 기반은 mesh.get_concept_mesh_generator의 AI 어댑터로 교체)
    """

    def generate(self, natural_language: str) -> ConceptSpec:
        t = natural_language
        tl = t.lower()

        # 1) 차종 프리셋 선택
        preset = "coupe"
        if re.search(r"슈퍼카|하이퍼카|미드십|supercar|hypercar", tl): preset = "supercar"
        elif re.search(r"suv|크로스오버|crossover", tl): preset = "suv"
        elif re.search(r"픽업|트럭|pickup|truck", tl): preset = "pickup"
        elif re.search(r"세단|saloon|sedan", tl): preset = "sedan"
        elif re.search(r"왜건|에스테이트|wagon|estate", tl): preset = "wagon"
        elif re.search(r"해치백|하치백|hatch", tl): preset = "hatch"
        elif re.search(r"쿠페|스포츠|coupe|sports", tl): preset = "coupe"
        spec = ConceptSpec(name="car_body_concept", **_PRESETS[preset])

        # 2) 루프라인 수식어
        if re.search(r"패스트백|fastback|쿠페형", tl): spec.roofline = "fastback"
        elif re.search(r"노치백|notchback|트렁크|trunk", tl): spec.roofline = "notchback"
        elif re.search(r"박스|각진|boxy|박시", tl): spec.roofline = "suv"

        # 3) 비례/스탠스 수식어 (가산 조정)
        if re.search(r"롱노즈|롱후드|long\s*hood|긴\s*보닛", tl):
            spec.hood_frac = min(spec.hood_frac + 0.10, 0.55)
        if re.search(r"캡포워드|cab[-\s]?forward|짧은\s*보닛", tl):
            spec.hood_frac = max(spec.hood_frac - 0.10, 0.22)
        if re.search(r"낮은|로우|슬램|low|slammed", tl):
            spec.height_mm -= 90; spec.ride_height_mm = max(90, spec.ride_height_mm - 50)
            spec.streamline = min(spec.streamline + 0.08, 1.0)
        if re.search(r"높은|키큰|tall|raised|리프트", tl):
            spec.height_mm += 90; spec.ride_height_mm += 60
        if re.search(r"와이드|넓은|wide", tl): spec.width_mm += 90
        if re.search(r"좁은|narrow", tl): spec.width_mm -= 80
        if re.search(r"롱휠베이스|long\s*wheelbase|짧은\s*오버행", tl):
            spec.overhang = max(0.2, spec.overhang - 0.2)
        if re.search(r"큰\s*휠|대구경|big\s*wheels|large\s*wheels|22|23|24", tl):
            spec.wheel_dia_mm += 80
        if re.search(r"유선형|매끈|sleek|streamlin", tl):
            spec.streamline = min(spec.streamline + 0.10, 1.0)

        # 4) 치수/목표 직접 명시 파싱
        m = re.search(r"Cd\s*([\d.]+)", t, re.I)
        if m: spec.target_cd = float(m.group(1))
        m = re.search(r"전장\s*([\d]{3,5})|length\s*([\d]{3,5})", tl)
        if m: spec.length_mm = float(next(g for g in m.groups() if g))
        m = re.search(r"전폭\s*([\d]{3,5})|width\s*([\d]{3,5})", tl)
        if m: spec.width_mm = float(next(g for g in m.groups() if g))
        m = re.search(r"전고\s*([\d]{3,5})|height\s*([\d]{3,5})", tl)
        if m: spec.height_mm = float(next(g for g in m.groups() if g))
        return spec

    def restyle(self, concept: ConceptSpec, delta_streamline: float) -> ConceptSpec:
        return replace(concept, streamline=min(concept.streamline + delta_streamline, 1.0))
