"""검토보고서 빌더.

입력·사전검토 근거·검증 이력·최종 결과·안전 고지를 담은 보고서를 생성.
- HTML: 의존성 없음(항상 생성). 브라우저에서 PDF 인쇄 가능.
- PDF : reportlab 설치 시 생성(한글 폰트 등록). 미설치 시 건너뜀.
"""
from __future__ import annotations

import datetime
import html
import os
from typing import Optional

from ..orchestrator.loop import LoopResult

_KR_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
]


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _final_checks(out: LoopResult):
    return out.iterations[-1].result if out.iterations else None


# ----------------------------------------------------------------- HTML
def build_html(out: LoopResult, prereview: str = "") -> str:
    spec = out.spec
    fin = _final_checks(out)
    rows_hist = "".join(
        f"<tr><td>{it.n}</td><td>{it.params.get('thickness_mm','')} mm</td>"
        f"<td>{'✅' if it.result.passed else '❌'}</td>"
        f"<td>{html.escape(it.result.feedback())}</td></tr>"
        for it in out.iterations
    )
    rows_check = ""
    if fin:
        for c in fin.checks:
            rows_check += (
                f"<tr><td>{'✅' if c.passed else '❌'}</td><td>{html.escape(c.name)}</td>"
                f"<td>{c.value:.3g}</td><td>{html.escape(c.target)}</td>"
                f"<td>{html.escape(c.detail)}</td></tr>"
            )
    status = "수렴(모든 검증 통과)" if out.converged else "미수렴(최대 반복 도달)"
    pre_html = html.escape(prereview).replace("\n", "<br>")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>AutoDesign-LLM 검토보고서 — {html.escape(spec.part_type)}</title>
<style>
 body{{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;margin:32px;color:#202124;line-height:1.5}}
 h1{{color:#0B2545}} h2{{color:#1A73E8;border-bottom:2px solid #E8F0FE;padding-bottom:4px;margin-top:28px}}
 table{{border-collapse:collapse;width:100%;margin:8px 0;font-size:14px}}
 th,td{{border:1px solid #ccc;padding:6px 8px;text-align:left}} th{{background:#0B2545;color:#fff}}
 tr:nth-child(even) td{{background:#F4F6F8}}
 .status{{font-size:18px;font-weight:bold;padding:8px 12px;border-radius:6px;display:inline-block;
   background:{'#E6F4EA' if out.converged else '#FCE8E6'};color:{'#188038' if out.converged else '#D93025'}}}
 .warn{{background:#FEF7E0;border-left:4px solid #F9AB00;padding:10px;margin:12px 0}}
 .pre{{background:#F8F9FA;border:1px solid #eee;padding:12px;border-radius:6px;font-size:13px}}
</style></head><body>
<h1>AutoDesign-LLM 검토보고서</h1>
<p>부품: <b>{html.escape(spec.part_type)}</b> · 재료: <b>{html.escape(spec.material)}</b> · 생성: {_now()}</p>
<p class="status">결과: {status} (반복 {out.n_iter}회)</p>

<h2>1. 설계 요구사항</h2>
<table>
 <tr><th>항목</th><th>값</th></tr>
 <tr><td>대표하중</td><td>{spec.total_load_N():.0f} N</td></tr>
 <tr><td>모멘트암</td><td>{spec.arm_length_mm} mm</td></tr>
 <tr><td>목표 안전계수</td><td>{spec.targets.safety_factor}</td></tr>
 <tr><td>1차 고유진동수</td><td>{spec.targets.min_natural_freq_hz or '-'} Hz</td></tr>
 <tr><td>피로 목표</td><td>{(f"{spec.targets.min_fatigue_cycles:.0e} cyc") if spec.targets.min_fatigue_cycles else '-'}</td></tr>
</table>

<h2>2. 사전 검토 (RAG 근거)</h2>
<div class="pre">{pre_html or '(없음)'}</div>

<h2>3. 자기교정 이력</h2>
<table><tr><th>반복</th><th>두께</th><th>통과</th><th>피드백</th></tr>{rows_hist}</table>

<h2>4. 최종 검증 결과</h2>
<table><tr><th></th><th>항목</th><th>값</th><th>목표</th><th>상세</th></tr>{rows_check}</table>
{(f'<p>최종: 두께 <b>{out.model.thickness_mm:.2f}mm</b>, 질량 <b>{out.model.mass_kg()*1000:.0f}g</b>, SF <b>{out.model.safety_factor():.2f}</b></p>') if out.model else ''}

<div class="warn">⚠️ <b>안전 고지</b>: 본 보고서의 물성값은 자리표시자일 수 있으며, 구조·모달·피로는
해석적 근사다. 시스템은 설계 보조 도구이며, 최종 양산 판정은 정식 CAE 및 실물시험을 거쳐야 한다.</div>
</body></html>"""


# ----------------------------------------------------------------- PDF
def build_pdf(out: LoopResult, path: str, prereview: str = "") -> Optional[str]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                        TableStyle)
    except Exception:
        return None

    font_path = next((p for p in _KR_FONT_CANDIDATES if os.path.exists(p)), None)
    if font_path:
        pdfmetrics.registerFont(TTFont("KR", font_path))
        base = "KR"
    else:
        base = "Helvetica"  # 한글 깨질 수 있음

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName=base, fontSize=18, textColor=colors.HexColor("#0B2545"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=base, fontSize=13, textColor=colors.HexColor("#1A73E8"))
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=base, fontSize=9.5, leading=14)

    spec = out.spec
    fin = _final_checks(out)
    E = []
    E.append(Paragraph("AutoDesign-LLM 검토보고서", h1))
    E.append(Paragraph(f"부품: {spec.part_type} · 재료: {spec.material} · 생성: {_now()}", body))
    status = "수렴(모든 검증 통과)" if out.converged else "미수렴"
    E.append(Paragraph(f"결과: <b>{status}</b> (반복 {out.n_iter}회)", body))
    E.append(Spacer(1, 6 * mm))

    def tbl(data, widths):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), base), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
        ]))
        return t

    E.append(Paragraph("1. 설계 요구사항", h2))
    E.append(tbl([
        ["항목", "값"],
        ["대표하중", f"{spec.total_load_N():.0f} N"],
        ["모멘트암", f"{spec.arm_length_mm} mm"],
        ["목표 SF", f"{spec.targets.safety_factor}"],
        ["고유진동수", f"{spec.targets.min_natural_freq_hz or '-'} Hz"],
        ["피로 목표", (f"{spec.targets.min_fatigue_cycles:.0e} cyc") if spec.targets.min_fatigue_cycles else "-"],
    ], [60 * mm, 90 * mm]))

    E.append(Paragraph("2. 사전 검토 (RAG 근거)", h2))
    for line in (prereview or "(없음)").split("\n"):
        E.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;") or "&nbsp;", body))

    E.append(Spacer(1, 3 * mm))
    E.append(Paragraph("3. 자기교정 이력", h2))
    hist = [["반복", "두께", "통과", "피드백"]]
    for it in out.iterations:
        hist.append([str(it.n), f"{it.params.get('thickness_mm','')}mm",
                     "OK" if it.result.passed else "X", it.result.feedback()[:60]])
    E.append(tbl(hist, [14 * mm, 22 * mm, 16 * mm, 98 * mm]))

    E.append(Paragraph("4. 최종 검증 결과", h2))
    if fin:
        cd = [["", "항목", "값", "목표"]]
        for c in fin.checks:
            cd.append(["OK" if c.passed else "X", c.name, f"{c.value:.3g}", c.target])
        E.append(tbl(cd, [12 * mm, 40 * mm, 35 * mm, 63 * mm]))

    E.append(Spacer(1, 4 * mm))
    E.append(Paragraph("⚠️ 안전 고지: 물성은 자리표시자일 수 있고 구조·모달·피로는 해석적 근사다. "
                       "시스템은 보조 도구이며 최종 양산 판정은 정식 CAE·실물시험 필수.", body))

    SimpleDocTemplate(path, pagesize=A4,
                      topMargin=18 * mm, bottomMargin=18 * mm,
                      leftMargin=18 * mm, rightMargin=18 * mm).build(E)
    return path


# ----------------------------------------------------------------- 통합
def build_report(out: LoopResult, prereview: str = "", out_dir: str = ".",
                 basename: str = "review_report") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, basename + ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(out, prereview))
    result = {"html": html_path}
    pdf_path = build_pdf(out, os.path.join(out_dir, basename + ".pdf"), prereview)
    if pdf_path:
        result["pdf"] = pdf_path
    return result
