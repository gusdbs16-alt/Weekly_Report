# Weekly Weather & AI Report Generator

이 프로젝트는 Gemini AI를 사용하여 기상 레이더, 구름 물리, 최신 AI 트렌드를 분석하고 주간 리포트를 생성하여 이메일로 발송하는 자동화 도구입니다.

## 주요 기능
- Gemini API 기반 최신 논문 및 뉴스 검색 및 요약
- 생성된 모든 URL의 유효성 확인
- HTML 형식의 리포트
- GitHub Actions 연동하여 매주 정해진 시간에 자동 발송

## 설정 방법 (GitHub Secrets)
이 프로젝트를 실행하려면 다음 비밀값(Secrets)을 GitHub Repository 설정에 등록해야 합니다.

1. `GEMINI_API_KEY`: Google AI Studio에서 발급받은 API 키
2. `EMAIL_USER`: 발신용 이메일 주소 (예: example@gmail.com)
3. `EMAIL_PASSWORD`: 이메일 앱 비밀번호
4. `EMAIL_RECIPIENT`: 기본 수신자 이메일
5. `EMAIL_CC`: 참조 수신자 이메일 (선택 사항)

## 로컬 실행
```bash
pip install -r requirements.txt
python weekly_report_generator.py
```
