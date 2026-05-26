"""
Streamlit Cloud 배포 entrypoint (경로 고정: dashboard_v3.py)

Cloud 앱은 생성 시 entrypoint가 dashboard_v3.py 로 고정되어 있어,
이 파일은 v4 본문(dashboard_v4.py)을 실행만 합니다.
로컬/개발 시 v4만 수정하면 배포에도 반영됩니다.
"""

from __future__ import annotations

from pathlib import Path
import runpy

_V4 = Path(__file__).resolve().parent / "dashboard_v4.py"

if not _V4.is_file():
    raise FileNotFoundError(f"dashboard_v4.py 를 찾을 수 없습니다: {_V4}")

runpy.run_path(str(_V4), run_name="__main__")
