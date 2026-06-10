"""AutoDesign-LLM 코어 패키지.

개발 순서(docs/02-DEV-PROCESS.md)에 따른 Phase 0 골격:
  ① spec            — 설계명세(DesignSpec) 스키마
  ② llm             — LLM 백엔드 추상화 (mock/local/cloud 교체 가능)
  ③ geometry        — 파라메트릭 형상 생성 (FreeCAD; 미설치 시 dry-run 해석)
  ④ validation      — 기하/구조 검증 게이트
  ⑤ orchestrator    — 생성→검증→자기교정 루프

FreeCAD/CalculiX 미설치 환경에서도 핵심 루프를 시연할 수 있도록
'dry-run'(해석적 추정) 경로를 제공한다. 실제 FEM은 Phase 2에서 연결.
"""
__version__ = "0.1.0"
