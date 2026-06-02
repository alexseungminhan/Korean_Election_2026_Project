# main.py
# 역할: 전체 파이프라인 실행 → output/report.html 생성
#
# 실행 예시:
#   python main.py
#   python main.py --region 부산광역시 --candidate-a 홍길동 --candidate-b 김철수

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))

from output.collector import get_youtube_comments, get_news_articles
from output.analyzer  import analyze_comments, analyze_news, calculate_dominance, extract_keywords


# ── 설정 ──────────────────────────────────────────────
def _arg(flag, default=""):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
# ─────────────────────────────────────────────────────


def analyze_region(region_key, region_name, cand_a, cand_b, quiet=False):
    """
    한 지역을 분석해 HTML 리포트를 만들고, 결과 요약을 반환합니다.
    반환: {"key", "name", "a", "b", "result", "file"} — 지도 인덱스에서 사용
    """
    if not quiet:
        print(f"\n{'='*52}")
        print(f"  {region_name} — {cand_a} vs {cand_b}")
        print(f"{'='*52}")

    # 1. 수집
    comments_a = get_youtube_comments(cand_a)
    comments_b = get_youtube_comments(cand_b)
    news_a     = get_news_articles(cand_a)
    news_b     = get_news_articles(cand_b)

    # 2. 분석
    a_data = {"comments": analyze_comments(comments_a), "news": analyze_news(news_a)}
    b_data = {"comments": analyze_comments(comments_b), "news": analyze_news(news_b)}

    # 3. 종합
    result = calculate_dominance(a_data, b_data)
    winner_name = cand_a if result["우승자"] == "A" else cand_b
    if not quiet:
        print(f"  → {winner_name} {result['우승확률']}% 우세 ({result['판세']})")

    # 키워드
    kw_a = extract_keywords([c["text"] for c in comments_a], candidate=cand_a, top_n=8)
    kw_b = extract_keywords([c["text"] for c in comments_b], candidate=cand_b, top_n=8)

    # HTML 저장 (지역별 파일명: report_seoul.html 등)
    html = build_html(region_name, cand_a, cand_b, a_data, b_data, result, kw_a, kw_b)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_name = f"report_{region_key}.html"
    with open(os.path.join(OUTPUT_DIR, file_name), "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "key":    region_key,
        "name":   region_name,
        "a":      cand_a,
        "b":      cand_b,
        "result": result,
        "file":   file_name,
    }


def run():
    """단일 지역 실행 (커맨드라인 인자 기반)"""
    from regions import REGIONS

    region_arg = _arg("--region", "서울특별시")
    # 한글명으로 들어오면 key 찾기
    region_key = None
    for k, v in REGIONS.items():
        if v["name"] == region_arg or k == region_arg:
            region_key = k
            break
    if region_key is None:
        region_key, region_arg = "seoul", "서울특별시"

    info = REGIONS[region_key]
    cand_a = _arg("--candidate-a", info["a"])
    cand_b = _arg("--candidate-b", info["b"])

    summary = analyze_region(region_key, info["name"], cand_a, cand_b)
    path = os.path.join(OUTPUT_DIR, summary["file"])
    print(f"\n브라우저에서 열기: open {path}\n")


def build_html(region, ca, cb, a, b, res, kw_a, kw_b):
    winner_name = ca if res["우승자"] == "A" else cb

    def bias_label(score):  # 조사 "이/가" 자동
        last = winner_name[-1]
        code = (ord(last) - 0xAC00) % 28
        return "이" if code else "가"

    summary = f"{winner_name}{bias_label(0)} {res['우승확률']}% 확률로 우세합니다."

    def keyword_chips(kw_list):
        if not kw_list:
            return '<span style="font-size:11px;color:#9a9892">키워드 없음</span>'
        chips = ""
        for word, cnt in kw_list:
            size = 11 + min(cnt // 3, 8)
            chips += f'<span style="font-size:{size}px;padding:3px 9px;background:#f0eeea;border-radius:12px;color:#5a5a56;margin:2px;display:inline-block">{word}</span>'
        return chips

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>지선예측 2026 — {region}</title>
<style>
  *,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif;
         background:#f5f4f0; color:#1a1a18; padding:32px 16px; }}
  .container {{ max-width:860px; margin:0 auto; display:flex; flex-direction:column; gap:16px; }}
  .header {{ background:#fff; border:1px solid rgba(0,0,0,.1); border-radius:12px; padding:20px 24px; }}
  .eyebrow {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:#9a9892; margin-bottom:6px; }}
  .title {{ font-size:22px; font-weight:700; margin-bottom:4px; letter-spacing:-.5px; }}
  .subtitle {{ font-size:13px; color:#5a5a56; margin-bottom:16px; }}
  .prob-bar {{ height:32px; border-radius:6px; overflow:hidden; display:flex; margin-bottom:8px; }}
  .seg-a {{ background:#378ADD; color:#E6F1FB; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; }}
  .seg-b {{ background:#E24B4A; color:#FCEBEB; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; }}
  .prob-labels {{ display:flex; justify-content:space-between; font-size:11px; color:#9a9892; margin-bottom:14px; }}
  .pred-box {{ padding:12px 16px; border-radius:8px; background:#EAF3DE; border-left:3px solid #639922;
              font-size:14px; font-weight:600; color:#27500A; }}
  .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
  @media(max-width:600px){{.metrics{{grid-template-columns:repeat(2,1fr)}}}}
  .mcard {{ background:#fff; border:1px solid rgba(0,0,0,.1); border-radius:10px; padding:14px 16px; }}
  .mc-label {{ font-size:11px; color:#9a9892; margin-bottom:5px; }}
  .mc-value {{ font-size:20px; font-weight:700; letter-spacing:-.5px; line-height:1; }}
  .mc-sub {{ font-size:10px; color:#5a5a56; margin-top:3px; }}
  .card {{ background:#fff; border:1px solid rgba(0,0,0,.1); border-radius:12px; overflow:hidden; }}
  .card-head {{ padding:12px 20px; border-bottom:.5px solid rgba(0,0,0,.08); font-size:12px;
               font-weight:600; color:#5a5a56; background:#faf9f6; display:flex; justify-content:space-between; }}
  .card-body {{ padding:16px 20px; }}
  .tag {{ font-size:9px; padding:2px 7px; border-radius:10px; background:#f0eeea; color:#9a9892; }}
  .two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
  @media(max-width:600px){{.two-col{{grid-template-columns:1fr}}}}
  .sent-row {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }}
  .sent-name {{ font-size:12px; font-weight:600; min-width:60px; }}
  .sent-track {{ flex:1; height:10px; background:#f0eeea; border-radius:5px; overflow:hidden; display:flex; }}
  .sent-pos {{ background:#639922; height:100%; }}
  .sent-neg {{ background:#E24B4A; height:100%; }}
  .sent-pct {{ font-size:11px; color:#9a9892; min-width:36px; text-align:right; }}
  .footer {{ font-size:10px; color:#9a9892; text-align:center; padding:8px 0; line-height:1.6; }}
  .vs-row {{ display:flex; align-items:center; gap:8px; font-size:11px; color:#5a5a56; margin-bottom:6px; }}
  .vs-label {{ min-width:70px; color:#9a9892; }}
  .vs-track {{ flex:1; height:8px; background:#f0eeea; border-radius:4px; overflow:hidden; display:flex; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <a href="index.html" style="font-size:11px;color:#378ADD;text-decoration:none;display:inline-block;margin-bottom:8px">← 전국 지도로 돌아가기</a>
    <div class="eyebrow">지선예측 2026 · 여론 기반 분석 (언급량 + 감성)</div>
    <div class="title">{region} 광역단체장 선거</div>
    <div class="subtitle">{ca} vs {cb} · 유튜브 공중파 댓글 + 네이버 뉴스 기반</div>

    <div class="prob-bar">
      <div class="seg-a" style="width:{res['A_확률']}%">{ca} {res['A_확률']}%</div>
      <div class="seg-b" style="width:{res['B_확률']}%">{cb} {res['B_확률']}%</div>
    </div>
    <div class="prob-labels">
      <span>← {ca} 우세</span><span>{cb} 우세 →</span>
    </div>
    <div class="pred-box">📊 {summary}</div>
  </div>

  <div class="metrics">
    <div class="mcard">
      <div class="mc-label">댓글 언급량</div>
      <div class="mc-value">{a['comments']['총댓글']} : {b['comments']['총댓글']}</div>
      <div class="mc-sub">{ca} : {cb}</div>
    </div>
    <div class="mcard">
      <div class="mc-label">뉴스 기사수</div>
      <div class="mc-value">{a['news']['기사수']} : {b['news']['기사수']}</div>
      <div class="mc-sub">{ca} : {cb}</div>
    </div>
    <div class="mcard">
      <div class="mc-label">댓글 긍정률 ({ca})</div>
      <div class="mc-value" style="color:#3B6D11">{a['comments']['긍정비율']}%</div>
      <div class="mc-sub">유튜브 공중파</div>
    </div>
    <div class="mcard">
      <div class="mc-label">판세</div>
      <div class="mc-value" style="font-size:16px">{res['판세']}</div>
      <div class="mc-sub">격차 {abs(res['A_확률']-res['B_확률']):.1f}%p</div>
    </div>
  </div>

  <div class="two-col">
    <div class="card">
      <div class="card-head">유튜브 댓글 감성 <span class="tag">공중파 채널</span></div>
      <div class="card-body">
        <div class="sent-row">
          <div class="sent-name" style="color:#185FA5">{ca}</div>
          <div class="sent-track">
            <div class="sent-pos" style="width:{a['comments']['긍정비율']}%"></div>
            <div class="sent-neg" style="width:{a['comments']['부정비율']}%"></div>
          </div>
          <div class="sent-pct">{a['comments']['긍정비율']}%</div>
        </div>
        <div class="sent-row">
          <div class="sent-name" style="color:#A32D2D">{cb}</div>
          <div class="sent-track">
            <div class="sent-pos" style="width:{b['comments']['긍정비율']}%"></div>
            <div class="sent-neg" style="width:{b['comments']['부정비율']}%"></div>
          </div>
          <div class="sent-pct">{b['comments']['긍정비율']}%</div>
        </div>
        <div style="font-size:10px;color:#9a9892;margin-top:8px">
          채널 가중치 + 좋아요 수 반영
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-head">뉴스 감성 <span class="tag">네이버 뉴스</span></div>
      <div class="card-body">
        <div class="sent-row">
          <div class="sent-name" style="color:#185FA5">{ca}</div>
          <div class="sent-track">
            <div class="sent-pos" style="width:{a['news']['긍정비율']}%"></div>
            <div class="sent-neg" style="width:{a['news']['부정비율']}%"></div>
          </div>
          <div class="sent-pct">{a['news']['긍정비율']}%</div>
        </div>
        <div class="sent-row">
          <div class="sent-name" style="color:#A32D2D">{cb}</div>
          <div class="sent-track">
            <div class="sent-pos" style="width:{b['news']['긍정비율']}%"></div>
            <div class="sent-neg" style="width:{b['news']['부정비율']}%"></div>
          </div>
          <div class="sent-pct">{b['news']['긍정비율']}%</div>
        </div>
        <div style="font-size:10px;color:#9a9892;margin-top:8px">
          {ca} 추세 {a['news']['추세']:+.2f} · {cb} 추세 {b['news']['추세']:+.2f}
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-head">가중치 구성 <span class="tag">종합 점수 모델</span></div>
    <div class="card-body">
      <div class="vs-row"><div class="vs-label">댓글 감성</div><div class="vs-track"><div style="width:35%;background:#7F77DD;height:100%"></div></div><span style="font-size:10px;color:#9a9892">35%</span></div>
      <div class="vs-row"><div class="vs-label">뉴스 감성</div><div class="vs-track"><div style="width:30%;background:#7F77DD;height:100%"></div></div><span style="font-size:10px;color:#9a9892">30%</span></div>
      <div class="vs-row"><div class="vs-label">언급량</div><div class="vs-track"><div style="width:20%;background:#7F77DD;height:100%"></div></div><span style="font-size:10px;color:#9a9892">20%</span></div>
      <div class="vs-row"><div class="vs-label">뉴스 추세</div><div class="vs-track"><div style="width:15%;background:#7F77DD;height:100%"></div></div><span style="font-size:10px;color:#9a9892">15%</span></div>
    </div>
  </div>

  <div class="two-col">
    <div class="card">
      <div class="card-head">{ca} 키워드</div>
      <div class="card-body" style="line-height:2">{keyword_chips(kw_a)}</div>
    </div>
    <div class="card">
      <div class="card-head">{cb} 키워드</div>
      <div class="card-body" style="line-height:2">{keyword_chips(kw_b)}</div>
    </div>
  </div>

  <div class="footer">
    지선예측 2026 · 생성 {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
    ⚠ 여론(댓글·뉴스) 기반 분석은 플랫폼 사용자층 편향이 있어 실제 득표율과 다를 수 있습니다.
  </div>

</div>
</body>
</html>"""


if __name__ == "__main__":
    run()