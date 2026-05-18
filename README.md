# gyotong
도로교통공사 공모전

## 파트별 실행

```bash
python src/preprocess_ktx.py
python src/features.py
python src/model.py
python src/part1_aggregate.py
python src/prophet_model.py
```

- `src/part1_aggregate.py`: 파트 1 노선·역별 집계 CSV 생성
- `src/part1_dashboard.py`: 파트 1 Streamlit 대시보드
- `src/dashboard_static.html`: 흰색 계기판 스타일 정적 대시보드 (`http://127.0.0.1:8765/src/dashboard_static.html`)
- `src/prophet_model.py`: 파트 4 노선별 Prophet 공실률 예측 및 실제값 비교

## 통합 대시보드

```bash
cd dashboard
npm install
npm run dev -- -p 3001
```

- `dashboard/`: Next.js + React + Tailwind CSS 통합 대시보드
- 탭 구성: 탭 1 파트 1 노선·역 현황, 탭 2 파트 2 시간·계절 패턴, 탭 3 파트 3-A/B 예측 모델, 탭 4 파트 5 외부 변수 해석
- 실행 주소: `http://localhost:3001`
