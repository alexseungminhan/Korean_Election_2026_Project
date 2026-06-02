# build_all.py
# 역할: 16개 광역단체을 분석 → 지역별 리포트 + 전국 지도 인덱스(index.html) 생성
#
# 실행: python build_all.py
# 결과: output/index.html (지도) + output/report_*.html (지역별)

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))

from regions import REGIONS
from main import analyze_region, OUTPUT_DIR

# 실제 지형 기반 SVG path (TopoJSON에서 변환, data/kr_paths.json)
import json as _json
_paths_file = os.path.join(os.path.dirname(__file__), "data", "kr_paths.json")
with open(_paths_file, encoding="utf-8") as _f:
    _KR_PATHS = _json.load(_f)

# region key → 지도 데이터의 영문명 매핑
KEY_TO_MAPNAME = {
    "seoul": "Seoul", "busan": "Busan", "daegu": "Daegu", "incheon": "Incheon",
    "daejeon": "Daejeon", "ulsan": "Ulsan", "sejong": "Sejongsi",
    "gyeonggi": "Gyeonggi-do", "gangwon": "Gangwon-do",
    "chungbuk": "Chungcheongbuk-do", "chungnam": "Chungcheongnam-do",
    "jeonbuk": "Jeollabuk-do", "gyeongbuk": "Gyeongsangbuk-do",
    "gyeongnam": "Gyeongsangnam-do", "jeju": "Jeju-do",
    # 통합특별시: 전남 + 광주를 둘 다 그림 (아래 build_map_svg에서 특별 처리)
    "gwangju_jeonnam": "Jeollanam-do",
}

# 라벨 표시명 (지도 위에 쓸 짧은 한글)
KEY_TO_LABEL = {
    "seoul": "서울", "busan": "부산", "daegu": "대구", "incheon": "인천",
    "daejeon": "대전", "ulsan": "울산", "sejong": "세종", "gyeonggi": "경기",
    "gangwon": "강원", "chungbuk": "충북", "chungnam": "충남", "jeonbuk": "전북",
    "gyeongbuk": "경북", "gyeongnam": "경남", "jeju": "제주",
    "gwangju_jeonnam": "전남·광주",
}

# 작은 지역은 라벨을 지도 밖으로 빼고 지시선으로 연결
# 새 좌표 기준 (x: 18~237, y: 95~464)
LABEL_OFFSET = {
    "seoul":   (45, 90),    # 서울: 위쪽 밖으로
    "incheon": (12, 135),   # 인천: 왼쪽 밖으로
    "sejong":  (35, 175),   # 세종: 왼쪽 위로
    "daejeon": (40, 235),   # 대전: 왼쪽으로
    "daegu":   (245, 250),  # 대구: 오른쪽 밖으로
    "ulsan":   (262, 285),  # 울산: 오른쪽 밖으로
    "busan":   (260, 320),  # 부산: 오른쪽 아래로
}


def color_for(result):
    """우세도에 따라 지도 색상 결정 (5단계)"""
    gap = result["A_확률"] - result["B_확률"]
    if gap >= 10:   return "#378ADD"   # A 강세
    if gap >= 5:    return "#85B7EB"   # A 약세
    if gap > -5:    return "#EF9F27"   # 경합
    if gap > -10:   return "#F09595"   # B 약세
    return "#E24B4A"                    # B 강세


def build_map_svg(summaries):
    """실제 지형 기반 클릭 가능 SVG 지도 생성 (작은 지역은 라벨을 밖으로)"""
    by_key = {s["key"]: s for s in summaries}
    region_parts = []
    label_parts = []   # 라벨은 영역 위에 그려야 하므로 따로 모음

    for key, mapname in KEY_TO_MAPNAME.items():
        s = by_key.get(key)
        fill = color_for(s["result"]) if s else "#ccc"
        file = s["file"] if s else "#"
        label = KEY_TO_LABEL[key]

        # path (통합특별시는 전남+광주 둘 다)
        path_d = _KR_PATHS[mapname]["path"]
        if key == "gwangju_jeonnam":
            path_d += " " + _KR_PATHS["Gwangju"]["path"]

        # 영역 (클릭 가능)
        region_parts.append(
            f'<a href="{file}"><path d="{path_d}" fill="{fill}" '
            f'stroke="#fff" stroke-width="1" class="region"/></a>'
        )

        # 라벨 위치 결정
        anchor_x, anchor_y = _KR_PATHS[mapname]["label"]  # 영역 중심(지시선 시작점)
        if key in LABEL_OFFSET:
            lx, ly = LABEL_OFFSET[key]
            # 지시선 (영역 중심 → 라벨)
            label_parts.append(
                f'<line x1="{anchor_x:.0f}" y1="{anchor_y:.0f}" x2="{lx}" y2="{ly}" '
                f'stroke="#999" stroke-width="0.6"/>'
            )
            tx, ty = lx, ly
            text_color = "#1a1a18"
        else:
            tx, ty = anchor_x, anchor_y
            text_color = "#1a1a18"   # 흰 테두리가 있어 어떤 배경에서도 보임

        # 라벨 (흰 테두리로 가독성 확보)
        label_parts.append(
            f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="10" '
            f'fill="{text_color}" font-weight="700" pointer-events="none" '
            f'style="paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round">{label}</text>'
        )

    return "\n".join(region_parts) + "\n" + "\n".join(label_parts)


def build_index_html(summaries):
    a_wins = sum(1 for s in summaries if s["result"]["우승자"] == "A" and s["result"]["판세"] != "경합")
    b_wins = sum(1 for s in summaries if s["result"]["우승자"] == "B" and s["result"]["판세"] != "경합")
    tight  = sum(1 for s in summaries if s["result"]["판세"] == "경합")

    svg = build_map_svg(summaries)

    # 지역 리스트 (지도 옆 목록)
    rows = ""
    for s in sorted(summaries, key=lambda x: -x["result"]["우승확률"]):
        r = s["result"]
        winner = s["a"] if r["우승자"] == "A" else s["b"]
        badge_color = "#185FA5" if r["우승자"] == "A" else "#A32D2D"
        if r["판세"] == "경합":
            badge_color = "#854F0B"
        rows += f"""
        <a href="{s['file']}" class="region-row">
          <span class="rr-name">{s['name']}</span>
          <span class="rr-winner" style="color:{badge_color}">{winner}</span>
          <span class="rr-prob">{r['우승확률']}%</span>
        </a>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>지선예측 2026 — 전국 판세</title>
<style>
  *,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif;
         background:#f5f4f0; color:#1a1a18; padding:32px 16px; }}
  .container {{ max-width:900px; margin:0 auto; }}
  .header {{ background:#fff; border:1px solid rgba(0,0,0,.1); border-radius:12px; padding:20px 24px; margin-bottom:16px; }}
  .eyebrow {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:#9a9892; margin-bottom:6px; }}
  .title {{ font-size:22px; font-weight:700; letter-spacing:-.5px; }}
  .summary {{ display:flex; gap:20px; margin-top:14px; font-size:13px; }}
  .sm-item {{ display:flex; align-items:center; gap:6px; }}
  .dot {{ width:10px; height:10px; border-radius:2px; }}
  .layout {{ display:grid; grid-template-columns:1fr 280px; gap:16px; }}
  @media(max-width:680px){{.layout{{grid-template-columns:1fr}}}}
  .map-card, .list-card {{ background:#fff; border:1px solid rgba(0,0,0,.1); border-radius:12px; padding:16px; }}
  .region {{ cursor:pointer; transition:opacity .15s; }}
  .region:hover {{ opacity:.72; }}
  .legend {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; font-size:10px; color:#5a5a56; }}
  .lg {{ display:flex; align-items:center; gap:4px; }}
  .lg-sw {{ width:12px; height:9px; border-radius:2px; }}
  .list-title {{ font-size:12px; font-weight:600; color:#5a5a56; margin-bottom:10px; }}
  .region-row {{ display:flex; align-items:center; padding:8px 6px; border-bottom:.5px solid rgba(0,0,0,.06);
                text-decoration:none; transition:background .12s; }}
  .region-row:hover {{ background:#faf9f6; }}
  .rr-name {{ flex:1; font-size:12px; color:#1a1a18; }}
  .rr-winner {{ font-size:11px; font-weight:600; margin-right:8px; }}
  .rr-prob {{ font-size:11px; color:#9a9892; min-width:38px; text-align:right; }}
  .footer {{ font-size:10px; color:#9a9892; text-align:center; padding:14px 0; line-height:1.6; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="eyebrow">지선예측 2026 · 여론 기반 분석 (유튜브 댓글 + 네이버 뉴스)</div>
    <div class="title">전국 광역단체장 선거 판세</div>
    <div class="summary">
      <div class="sm-item"><div class="dot" style="background:#378ADD"></div>더불어민주당 우세 {a_wins}곳</div>
      <div class="sm-item"><div class="dot" style="background:#E24B4A"></div>국민의힘 우세 {b_wins}곳</div>
      <div class="sm-item"><div class="dot" style="background:#EF9F27"></div>경합 {tight}곳</div>
    </div>
  </div>

  <div class="layout">
    <div class="map-card">
      <svg width="100%" viewBox="0 80 285 400" xmlns="http://www.w3.org/2000/svg">
        {svg}
        <text x="142" y="475" text-anchor="middle" font-size="7" fill="#aaa">※ 지역을 클릭하면 상세 분석으로 이동</text>
      </svg>
      <div class="legend">
        <div class="lg"><div class="lg-sw" style="background:#378ADD"></div>A 강세</div>
        <div class="lg"><div class="lg-sw" style="background:#85B7EB"></div>A 약세</div>
        <div class="lg"><div class="lg-sw" style="background:#EF9F27"></div>경합</div>
        <div class="lg"><div class="lg-sw" style="background:#F09595"></div>B 약세</div>
        <div class="lg"><div class="lg-sw" style="background:#E24B4A"></div>B 강세</div>
      </div>
    </div>

    <div class="list-card">
      <div class="list-title">우세 확률 순</div>
      {rows}
    </div>
  </div>

  <div class="footer">
    지선예측 2026 · 생성 {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
    ⚠ 여론(댓글·뉴스) 기반 분석은 플랫폼 편향이 있어 실제 득표율과 다를 수 있습니다.
  </div>

</div>
</body>
</html>"""


def main():
    print(f"\n{'#'*52}")
    print(f"  전국 16개 지역 분석 시작")
    print(f"{'#'*52}")
    print("  ※ 유튜브 API는 검색 1회당 100유닛 소비 (무료 한도 10,000/일)")
    print("  ※ 첫 빌드 후 6시간 동안은 .cache로 재사용되어 할당량 0")

    summaries = []
    for i, (key, info) in enumerate(REGIONS.items(), 1):
        print(f"\n[{i}/16] {info['name']}", end="")
        summary = analyze_region(key, info["name"], info["a"], info["b"], quiet=True)
        r = summary["result"]
        winner = info["a"] if r["우승자"] == "A" else info["b"]
        print(f"  → {winner} {r['우승확률']}% ({r['판세']})")
        summaries.append(summary)

    # 지도 인덱스 생성
    print(f"\n[ 인덱스 ] 전국 지도 생성 중...")
    index_html = build_index_html(summaries)
    index_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"\n{'='*52}")
    print(f"  완료! 총 {len(summaries)}개 지역 + 지도 1개")
    print(f"  메인 화면 열기: open {index_path}")
    print(f"{'='*52}\n")


if __name__ == "__main__":
    main()