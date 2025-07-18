# Streamlit Cloud 배포 가이드

이 문서는 수련회 조 배정 시스템을 Streamlit Cloud에 배포하는 방법을 설명합니다.

## 🚀 Streamlit Cloud 배포

### 1. GitHub 저장소 준비
1. GitHub.com에 로그인
2. "New repository" 클릭
3. 저장소 이름 입력 (예: `camp-group-assignment`)
4. Public 또는 Private 선택
5. "Create repository" 클릭

### 2. 로컬 저장소를 GitHub에 연결
```bash
# 원격 저장소 추가 (YOUR_USERNAME과 REPO_NAME을 실제 값으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 브랜치 이름을 main으로 변경 (선택사항)
git branch -M main

# GitHub에 푸시
git push -u origin main
```

### 3. Streamlit Cloud 배포
1. [share.streamlit.io](https://share.streamlit.io)에 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. 다음 정보 입력:
   - **Repository**: `yourusername/camp-group-assignment`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
5. "Deploy!" 클릭

### 4. 배포 완료
- 앱이 자동으로 배포됩니다
- URL이 생성되어 공유 가능합니다 (예: `https://your-app-name.streamlit.app`)

## 🔧 로컬 개발 환경

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 로컬 실행
```bash
streamlit run streamlit_app.py
```

### 3. 브라우저에서 확인
```
http://localhost:8501
```

## 📁 필수 파일 구조

```
camp-group-assignment/
├── streamlit_app.py                 # 메인 Streamlit 앱
├── camp_group_assignment.py         # 조 배정 로직
├── requirements.txt                 # Python 의존성
├── .streamlit/                      # Streamlit 설정
│   └── config.toml                  # 테마 및 설정
├── sample_data/                     # 샘플 데이터
│   ├── real_leaders.xlsx
│   └── real_members.xlsx
└── README.md                        # 프로젝트 설명
```

## ⚙️ Streamlit 설정

### .streamlit/config.toml
```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
```

## 🔒 보안 고려사항

### 파일 업로드 보안
- Excel 파일만 허용 (.xlsx, .xls)
- 파일 크기 제한 (Streamlit 기본: 200MB)
- 임시 파일 자동 삭제

### 환경 변수
```python
import os

# 민감한 정보는 환경 변수로 관리
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
```

## 🚨 문제 해결

### 일반적인 문제들

1. **의존성 문제**
   ```bash
   # requirements.txt 업데이트
   pip freeze > requirements.txt
   ```

2. **파일 경로 문제**
   - 모든 파일이 올바른 위치에 있는지 확인
   - 파일명과 경로가 정확한지 확인

3. **메모리 부족**
   - 대용량 파일 처리 시 청크 단위 처리
   - 불필요한 데이터 즉시 삭제

### 배포 실패 시 확인사항
1. **requirements.txt**에 모든 의존성이 포함되어 있는지 확인
2. **streamlit_app.py**가 올바른 경로에 있는지 확인
3. **GitHub 저장소**가 Public이거나 Streamlit Cloud에 접근 권한이 있는지 확인

### 로그 확인
```bash
# 로컬 실행 시 로그
streamlit run streamlit_app.py --logger.level debug

# Streamlit Cloud에서는 웹 인터페이스에서 로그 확인 가능
```

## 📈 성능 최적화

### 파일 처리 최적화
- 임시 파일 즉시 삭제
- 메모리 효율적인 데이터 처리
- 대용량 파일 청크 단위 처리

### UI/UX 최적화
- 로딩 스피너 추가
- 진행률 표시
- 사용자 친화적인 오류 메시지

## 🔄 지속적 배포 (CI/CD)

### GitHub Actions 설정
`.github/workflows/deploy.yml` 파일 생성:

```yaml
name: Deploy to Streamlit Cloud

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Test Streamlit app
      run: |
        streamlit run streamlit_app.py --server.headless true --server.port 8501 &
        sleep 10
        curl http://localhost:8501
```

## 📊 모니터링

### Streamlit Cloud 대시보드
- 앱 사용량 통계
- 오류 로그
- 성능 메트릭

### 사용자 피드백
- GitHub Issues 활용
- 사용자 가이드 제공

## 🎯 배포 후 확인사항

1. **기본 기능 테스트**
   - 파일 업로드
   - 조 배정 실행
   - 결과 다운로드

2. **UI/UX 확인**
   - 반응형 디자인
   - 모바일 호환성
   - 사용자 경험

3. **성능 테스트**
   - 대용량 파일 처리
   - 동시 사용자 처리
   - 응답 시간

## 📞 지원

배포 중 문제가 발생하면:
1. [Streamlit Community](https://discuss.streamlit.io/)에서 도움 요청
2. GitHub Issues 생성
3. 문서 재검토

---

**배포 완료 후**: `https://your-app-name.streamlit.app`로 접속하여 앱이 정상 작동하는지 확인하세요.

## 🔗 유용한 링크

- [Streamlit Cloud](https://share.streamlit.io)
- [Streamlit 문서](https://docs.streamlit.io)
- [Streamlit Community](https://discuss.streamlit.io)
- [GitHub](https://github.com) 