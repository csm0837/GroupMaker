# 수련회 조 배정 시스템

수련회 조 배정을 위한 Streamlit 웹 애플리케이션입니다. 조장/헬퍼 명단과 조원 명단을 업로드하면 자동으로 조를 배정하고 결과를 확인할 수 있습니다.

## 🚀 주요 기능

### 필수 조건
- **의대 24/25학번 분리**: 의대 24학번과 25학번은 같은 조에 배정되지 않습니다
- **같은 학교 금지**: 같은 학교 학생은 같은 조에 배정되지 않습니다
- **나이 조건**: 조원들은 헬퍼보다 어리거나 37세 조장 예외 조건을 만족합니다

### 최적화 조건
- **성비 균형**: 남녀 성비가 전체 성비와 비슷하게 유지됩니다
- **학과 분포**: 의대, 치대, 한의대, 간호대는 각 조에 2명 이상씩 배정됩니다
- **지역 다양성**: 최대한 다양한 지역의 학생들로 조를 구성합니다

### 추가 기능
- **인원 범위 설정**: 각 조의 최소/최대 인원을 설정할 수 있습니다
- **실시간 결과 표시**: 조 배정 결과를 즉시 확인할 수 있습니다
- **결과 다운로드**: 조 배정 결과와 요약 보고서를 CSV로 다운로드할 수 있습니다

## 📋 요구사항

- Python 3.8 이상
- Streamlit
- pandas
- openpyxl

## 🛠️ 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/camp-group-assignment.git
cd camp-group-assignment
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. Streamlit 앱 실행
```bash
streamlit run streamlit_app.py
```

### 4. 웹 브라우저에서 접속
```
http://localhost:8501
```

## 🌐 Streamlit Cloud 배포

### 1. GitHub에 코드 푸시
```bash
git add .
git commit -m "Add Streamlit app"
git push origin main
```

### 2. Streamlit Cloud에서 배포
1. [share.streamlit.io](https://share.streamlit.io)에 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. 저장소 선택: `yourusername/camp-group-assignment`
5. Main file path: `streamlit_app.py`
6. "Deploy!" 클릭

### 3. 배포 완료
- 앱이 자동으로 배포됩니다
- URL이 생성되어 공유 가능합니다

## 📁 파일 구조

```
camp-group-assignment/
├── streamlit_app.py                 # Streamlit 메인 앱
├── camp_group_assignment.py         # 조 배정 핵심 로직
├── create_real_sample_data.py       # 샘플 데이터 생성
├── requirements.txt                 # Python 의존성
├── README.md                        # 프로젝트 설명
├── .streamlit/                      # Streamlit 설정
│   └── config.toml                  # Streamlit 테마 및 설정
├── sample_data/                     # 샘플 데이터
│   ├── real_leaders.xlsx            # 조장/헬퍼 샘플 데이터
│   └── real_members.xlsx            # 조원 샘플 데이터
└── templates/                       # Flask 템플릿 (참고용)
    ├── index.html
    └── results.html
```

## 📊 사용법

### 1. 파일 준비
- **조장/헬퍼 명단**: Excel 파일 (.xlsx) - Sheet1에 다음 컬럼 포함
  - 조 숫자, 학교/학년, 이름, 학과, 성별, 조장or헬퍼, 나이, 연락처
- **조원 명단**: Excel 파일 (.xlsx) - "등록 데이터" 시트에 다음 컬럼 포함
  - 번호, 이름, 성별, 지역, 캠퍼스, 트랙, 참가유형, 학과, 학년, 학번, 졸업년도, 나이, 연락처 등

### 2. Streamlit 앱 사용
1. 웹 브라우저에서 앱 접속
2. 사이드바에서 조원 범위 설정 (최소/최대 인원)
3. 조장/헬퍼 명단과 조원 명단 파일 업로드
4. "조 배정 시작" 버튼 클릭
5. 결과 페이지에서 조 배정 결과 확인
6. 필요시 CSV 파일로 결과 다운로드

### 3. CLI 사용 (선택사항)
```bash
python camp_group_assignment.py --leaders leaders.xlsx --members members.xlsx --out result.csv --min-members 6 --max-members 8
```

## 🎯 조 배정 조건 상세

### 필수 조건
1. **의대 24/25학번 분리**: 의대 24학번과 25학번이 같은 조에 배정되지 않음
2. **같은 학교 금지**: 같은 학교 학생이 같은 조에 배정되지 않음
3. **나이 조건**: 조원들이 헬퍼보다 어리거나 37세 조장 예외 조건 만족

### 최적화 조건
1. **성비 균형**: 남녀 성비가 전체 성비와 비슷하게 유지 (차이 2명 이하)
2. **학과 분포**: 의대, 치대, 한의대, 간호대는 각 조에 2명 이상씩 배정
3. **지역 다양성**: 최소 3개 이상의 다양한 지역에서 온 학생들로 구성

## 🔧 설정 옵션

### 인원 범위 설정
- **최소 인원**: 3-10명 (조장/헬퍼 제외)
- **최대 인원**: 5-12명 (조장/헬퍼 제외)
- **기본값**: 최소 6명, 최대 8명

### 파일 형식
- **지원 형식**: .xlsx, .xls
- **인코딩**: UTF-8
- **시트명**: 조장/헬퍼는 "Sheet1", 조원은 "등록 데이터"

## 📈 결과 확인

### 배정 요약
- 총 조 수, 총 조원 수, 조원 범위, 평균 조원 수
- 조별 요약 통계 테이블
- 조건별 만족 현황 (퍼센트)

### 조별 상세 정보
- 각 조의 조장, 헬퍼, 조원 목록
- 조별 통계 (총 인원, 남성/여성 수)
- 조건 만족 여부 (✅/❌)

### 다운로드 가능한 파일
- **조 배정 결과**: 전체 조원 배정 결과 (CSV)
- **요약 보고서**: 조별 통계 및 조건 만족 여부 (CSV)

## 🐛 문제 해결

### 자주 발생하는 오류
1. **파일 형식 오류**: Excel 파일(.xlsx, .xls)만 지원
2. **컬럼명 오류**: 정확한 컬럼명으로 파일 준비 필요
3. **시트명 오류**: 조장/헬퍼는 "Sheet1", 조원은 "등록 데이터" 시트 사용

### 로그 확인
- Streamlit 앱에서 오류 메시지 직접 확인 가능
- 조 배정 과정과 경고 메시지 출력

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해 주세요.

---

**개발자**: [Your Name]  
**버전**: 1.0.0  
**최종 업데이트**: 2025년 7월  
**배포 플랫폼**: [Streamlit Cloud](https://share.streamlit.io) 