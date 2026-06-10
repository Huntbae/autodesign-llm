#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AutoDesign-LLM 시스템 구성도 생성 (matplotlib, 한글 폰트)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager as fm
import os

FONT = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
fp = fm.FontProperties(fname=FONT)
fm.fontManager.addfont(FONT)
plt.rcParams["font.family"] = fp.get_name()
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.dirname(os.path.abspath(__file__))

# 색상 팔레트
C = {
    "in":   "#E8F0FE",  # 입력
    "llm":  "#FCE8E6",  # LLM
    "rag":  "#FEF7E0",  # 지식/RAG
    "gen":  "#E6F4EA",  # 생성
    "val":  "#E0F7FA",  # 검증
    "opt":  "#F3E8FD",  # 최적화
    "out":  "#FFF0E6",  # 산출물
    "cloud":"#EAF2FF",
    "edge": "#5F6368",
}

def box(ax, x, y, w, h, text, color, fs=11, bold=False, ec="#9AA0A6"):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                       linewidth=1.3, edgecolor=ec, facecolor=color, zorder=2)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal",
            fontproperties=fp, zorder=3, color="#202124")
    return (x + w/2, y + h/2, x, y, w, h)

def arrow(ax, p1, p2, color="#5F6368", style="-|>", lw=1.6, ls="-", rad=0.0):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=14,
                        lw=lw, color=color, linestyle=ls,
                        connectionstyle=f"arc3,rad={rad}", zorder=1)
    ax.add_patch(a)

def setup(w=12, h=8):
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax

def title(ax, t):
    ax.text(50, 97, t, ha="center", va="center", fontsize=16,
            fontweight="bold", fontproperties=fp, color="#1A73E8")

def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white", dpi=150)
    plt.close(fig)
    print("wrote", path)

# ---------------------------------------------------------------- 1) 전체 구성도
def d_overview():
    fig, ax = setup(11, 9)
    title(ax, "AutoDesign-LLM 전체 시스템 구성도")
    cx, w, h = 28, 44, 7.5
    ys = [84, 74, 64, 54, 44, 34, 22, 10]
    b1 = box(ax, cx, ys[0], w, h, "① 사용자 자연어 입력\n(하중·장착점·재질·목표)", C["in"], bold=True)
    b2 = box(ax, cx, ys[1], w, h, "② 요구사항 파서 → 설계명세(JSON)", C["llm"])
    b3 = box(ax, cx, ys[2], w, h, "③ RAG 지식 조회\n(표준·논문·재료물성)", C["rag"])
    b4 = box(ax, cx, ys[3], w, h, "④ 사전 검토 리포트 (LLM)", C["rag"])
    b5 = box(ax, cx, ys[4], w, h, "⑤ 형상 생성: LLM → FreeCAD Python", C["gen"], bold=True)
    b6 = box(ax, cx, ys[5], w, h, "⑥ 검증 파이프라인\n기하·강도(FEM)·모달·피로·DFM", C["val"], bold=True)
    b7 = box(ax, cx, ys[6], w, h, "⑦ 위상최적화 경량화", C["opt"])
    b8 = box(ax, cx, ys[7], w, h, "⑧ 산출물: STEP/FCStd + 검토보고서(PDF)", C["out"], bold=True)
    chain = [b1, b2, b3, b4, b5, b6, b7, b8]
    for a, b in zip(chain, chain[1:]):
        arrow(ax, (a[0], a[3]), (b[0], b[3] + b[5]))
    # 자기교정 루프 (⑥ → ⑤)
    arrow(ax, (b6[2] + b6[4], b6[1]), (b5[2] + b5[4], b5[1]),
          color="#D93025", lw=1.8, rad=-0.55)
    ax.text(86, 39, "자기교정\n루프\n(미달 시)", ha="center", va="center",
            fontsize=10, color="#D93025", fontproperties=fp, fontweight="bold")
    # 검증→최적화 통과 라벨
    ax.text(72, ys[5]-1.5, "통과", ha="left", fontsize=9, color="#188038", fontproperties=fp)
    save(fig, "diagram_system_overview.png")

# ---------------------------------------------------------------- 2) 세 버전 관계
def d_variants():
    fig, ax = setup(12, 6)
    title(ax, "세 가지 배포 버전의 진화 관계")
    y, w, h = 50, 26, 20
    v1 = box(ax, 4, y, w, h, "v1 로컬 LLM\n\n· 온프레미스/에어갭\n· IP보안·오프라인\n· 기반 엔진", C["llm"], fs=11, bold=True)
    v2 = box(ax, 37, y, w, h, "v2 로컬+RAG 하이브리드\n★주력\n· 보안 + 도메인 정확도\n· 사내 설계자산 활용", C["rag"], fs=11, bold=True)
    v3 = box(ax, 70, y, w, h, "v3 클라우드\n\n· 최고 모델 품질\n· 대규모 시뮬 확장\n· 빠른 개발", C["cloud"], fs=11, bold=True)
    arrow(ax, (v1[2]+v1[4], y+h/2), (v2[2], y+h/2), lw=2)
    arrow(ax, (v2[2]+v2[4], y+h/2), (v3[2], y+h/2), lw=2)
    ax.text(33.5, y+h/2+3, "RAG\n지식레이어\n추가", ha="center", fontsize=9, color=C["edge"], fontproperties=fp)
    ax.text(66.5, y+h/2+3, "백엔드\n클라우드\n전환", ha="center", fontsize=9, color=C["edge"], fontproperties=fp)
    box(ax, 20, 14, 60, 14, "공통 코어 (생성 + 검증 파이프라인) — 세 버전이 공유\nLLM/지식/연산 백엔드만 인터페이스 뒤에서 교체", "#F1F3F4", fs=11, ec="#BDC1C6")
    for v in (v1, v2, v3):
        arrow(ax, (v[0], y), (v[0], 28), color="#9AA0A6", ls="--", style="-")
    save(fig, "diagram_variants.png")

# ---------------------------------------------------------------- 공통 변형 레이아웃
def variant(ax, label, llm_text, llm_color, with_rag, cloud_compute):
    title(ax, label)
    # 경계 박스
    bx = FancyBboxPatch((4, 6), 92, 80, boxstyle="round,pad=0.3,rounding_size=1",
                        linewidth=1.6, edgecolor="#1A73E8", facecolor="#FAFBFF",
                        linestyle="--", zorder=0)
    ax.add_patch(bx)
    user = box(ax, 38, 76, 24, 7, "사용자 / 앱", C["in"], bold=True)
    orch = box(ax, 36, 64, 28, 7, "오케스트레이터", "#F1F3F4")
    llm = box(ax, 8, 50, 34, 8, llm_text, llm_color, bold=True)
    arrow(ax, (user[0], 76), (orch[0], 71))
    arrow(ax, (orch[2], orch[1]+3), (llm[2]+llm[4], llm[1]+4))
    arrow(ax, (llm[2]+llm[4], llm[1]+2), (orch[2], orch[1]+1), rad=0.3)
    if with_rag:
        rag = box(ax, 58, 50, 34, 8, "RAG 검색\n→ 벡터DB(표준·논문·물성)", C["rag"], fs=10)
        arrow(ax, (orch[0]+6, 64), (rag[0], rag[1]+rag[5]))
        arrow(ax, (rag[2], rag[1]+2), (llm[2]+llm[4], llm[1]+6), color="#9AA0A6", rad=0.0)
        ax.text(75, 47, "근거 주입", ha="center", fontsize=8, color=C["edge"], fontproperties=fp)
    fem = box(ax, 18, 34, 64, 8, "FreeCAD(headless) → CalculiX(FEM) → 검증·자기교정 루프", C["val"], fs=10, bold=True)
    arrow(ax, (llm[0], llm[1]), (40, fem[1]+fem[5]))
    out = box(ax, 24, 20, 52, 7, "산출물: STEP / FCStd / 검토보고서(PDF)", C["out"], fs=10)
    arrow(ax, (fem[0], fem[1]), (out[0], out[1]+out[5]))
    if cloud_compute:
        cc = box(ax, 60, 9.5, 32, 6.5, "오토스케일 연산 워커\n(CFD/위상최적화 병렬)", C["cloud"], fs=9)
        arrow(ax, (fem[2]+fem[4], fem[1]+2), (cc[0], cc[1]+cc[5]), color="#9AA0A6", ls="--", style="-|>")

def d_v1():
    fig, ax = setup(11, 8.5)
    variant(ax, "v1 로컬 LLM — 온프레미스(폐쇄망)", "로컬 LLM 추론\n(GPU · vLLM/Ollama)", C["llm"], False, False)
    ax.text(50, 3.5, "※ 외부 네트워크 연결 없음 (에어갭 가능)", ha="center", fontsize=10,
            color="#D93025", fontproperties=fp, fontweight="bold")
    save(fig, "diagram_v1_local.png")

def d_v2():
    fig, ax = setup(11, 8.5)
    variant(ax, "v2 로컬+RAG 하이브리드 (★주력)", "로컬 LLM 추론\n(GPU · vLLM/Ollama)", C["llm"], True, False)
    ax.text(50, 3.5, "※ 온프레미스 보안 유지 + RAG로 도메인 정확도 향상", ha="center", fontsize=10,
            color="#188038", fontproperties=fp, fontweight="bold")
    save(fig, "diagram_v2_hybrid.png")

def d_v3():
    fig, ax = setup(11, 8.5)
    variant(ax, "v3 클라우드 시스템", "Claude API (Opus)\n+ 비전 피드백", C["cloud"], True, True)
    ax.text(50, 3.5, "※ 최고 품질·확장성 / 데이터 외부 전송 → IP 민감 고객 주의", ha="center", fontsize=10,
            color="#D93025", fontproperties=fp, fontweight="bold")
    save(fig, "diagram_v3_cloud.png")

if __name__ == "__main__":
    d_overview(); d_variants(); d_v1(); d_v2(); d_v3()
    print("ALL DIAGRAMS DONE")
