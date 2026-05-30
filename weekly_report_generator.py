import datetime
import os
import json
import sys
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
# Look for .env in current directory, then in project root
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

# Environment Variables
api_key = os.getenv("GEMINI_API_KEY")
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
email_recipient = os.getenv("EMAIL_RECIPIENT", "gusdbs16@knu.ac.kr")
email_cc = os.getenv("EMAIL_CC", "dance3414@naver.com")

if not api_key:
    print("Error: GEMINI_API_KEY not found. Please set it in your environment or .env file.")
    client = None
else:
    client = genai.Client(api_key=api_key)

def validate_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.head(url, timeout=5, headers=headers, allow_redirects=True)
        if response.status_code < 400:
            return True
        response = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

def get_automated_content(max_retries=3):
    if not client:
        print("Error: GenAI client not initialized.")
        return None

    today = datetime.date.today()
    model_name = 'gemini-2.5-flash'
    print(f"Using model: {model_name}")

    prompt = f"""
    당신은 기상 레이더, 구름 물리, 그리고 최신 AI 기술을 융합하여 분석하는 전문 수석 연구원입니다.
    구글 검색을 활용하여 {today} 기준, **해당 주간에 가장 주목받는 최신 논문(2020년 이후 발행)**과 메인 뉴스를 중심으로 리포트를 생성하세요.
    
    내용 구성 원칙:
    1. **섹션 1 (radar_papers):** 반드시 **2020년 이후 발행된 최신 학술 논문**을 중심으로 기상 레이더 및 구름 물리 분야의 연구 성과를 2개 선정하세요. 물리적 관측 원리, 이중편파 변수 분석, 구름 미세물리 관측 등의 학술적 내용을 깊이 있게 다루세요.
    2. **섹션 2 (ai_papers):** 반드시 **2020년 이후 발행된 최신 학술 논문** 중 기상/대기 과학에 적용된 AI 및 통계 모델링 연구를 1개 선정하세요. 
    3. **섹션 3 (news):** 이번 주 경제, 외교, 사회, 금융 각 분야에서 가장 비중 있게 다뤄진 메인 뉴스들을 선정하여 요약하세요. 
    
    필수 조건:
    - 섹션 1과 2의 논문은 반드시 **2020년 이후**의 것이어야 하며, 가능하면 이번 주 혹은 최근에 화제가 된 연구를 우선하세요.
    - 모든 링크는 실제로 존재하는 URL(DOI, ArXiv, 또는 학술지 링크)이어야 합니다.
    - 답변은 반드시 아래 JSON 구조를 지키며, 다른 설명은 하지 마세요.
    
    {{
      "keywords": "이번 주를 관통하는 핵심 키워드 3-5개",
      "radar_papers": [
        {{
          "title_ko": "최신 기상 레이더/기상학 논문 제목(한국어)",
          "title_en": "Original English Title",
          "authors": "저자 정보 및 학술지 이름",
          "summary": "논문의 핵심 연구 방법과 물리적 의의 요약 (2-3문장)",
          "link": "공식 논문 URL"
        }},
        ... (2개 생성)
      ],
      "ai_papers": [
        {{
          "title_ko": "최신 AI/통계 기상 응용 논문 제목(한국어)",
          "title_en": "Original English Title",
          "authors": "저자 정보 및 학술지 이름",
          "summary": "사용한 AI 알고리즘과 연구 결과의 혁신성 요약 (2-3문장)",
          "link": "공식 논문 URL"
        }}
      ],
      "news": [
        {{
          "category": "경제/외교/사회/금융 중 하나",
          "title": "주간 주요 뉴스 제목",
          "summary": "뉴스 핵심 내용 요약",
          "link": "URL"
        }},
        ... (4개 생성)
      ]
    }}
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.7
                )
            )

            if not response or not response.text:
                print(f"Error: Empty response from Gemini API. Response object: {response}")
                return None

            content_text = response.text.strip()

            if content_text.startswith("```json"):
                content_text = content_text[7:-3].strip()
            elif content_text.startswith("```"):
                content_text = content_text[3:-3].strip()

            data = json.loads(content_text)

            print(f"[{datetime.datetime.now()}] Validating generated links...")
            sections = ['radar_papers', 'ai_papers', 'news']
            for section in sections:
                for item in data[section]:
                    if not validate_url(item['link']):
                        search_title = item.get('title') or item.get('title_ko') or item.get('title_en') or "weather radar ai"
                        item['link'] = "https://www.google.com/search?q=" + search_title.replace(" ", "+")

            return data

        except Exception as e:
            print(f"[Attempt {attempt}/{max_retries}] Error generating content: {e}")
            if attempt < max_retries:
                wait_sec = 30 * (2 ** (attempt - 1))  # 30s → 60s → 120s
                print(f"Retrying in {wait_sec} seconds...")
                time.sleep(wait_sec)

    print(f"All {max_retries} attempts failed. Giving up.")
    return None

def send_email_via_smtp(recipient, subject, html_body, cc_recipient=None):
    if not email_user or not email_password:
        print("Error: EMAIL_USER or EMAIL_PASSWORD not set.")
        return False

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = recipient
    if cc_recipient:
        msg['Cc'] = cc_recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, email_password)
        
        recipients = [recipient]
        if cc_recipient:
            # Support multiple CC emails separated by commas
            cc_list = [email.strip() for email in cc_recipient.split(',') if email.strip()]
            recipients.extend(cc_list)
            
        server.sendmail(email_user, recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email via SMTP: {e}")
        return False

def generate_report_html(data):
    today = datetime.date.today()
    report_date = today.strftime("%Y-%m-%d")
    
    radar_papers_html = ""
    for idx, paper in enumerate(data['radar_papers']):
        radar_papers_html += f"""
            <div style="margin-bottom: 35px; padding: 20px; border: 1px solid #e1e1e1; border-radius: 8px; background-color: #ffffff;">
                <strong style="font-size: 1.2em; color: #2c3e50;">{'①' if idx==0 else '②'} {paper['title_ko']}</strong><br>
                <span style="color: #7f8c8d; font-size: 0.9em;">
                    <strong>Original Title:</strong> {paper['title_en']}<br>
                    <strong>Authors:</strong> {paper['authors']}
                </span>
                <p style="margin: 15px 0; text-align: justify;">
                    <strong>상세 요약:</strong> {paper['summary']}
                </p>
                <p style="margin-bottom: 0px;"><strong>공식 레퍼런스:</strong> <a href="{paper['link']}" style="color: #3498db; text-decoration: none; font-weight: bold;">[Link] &rarr;</a></p>
            </div>
        """

    ai_papers_html = ""
    for paper in data['ai_papers']:
        ai_papers_html += f"""
            <div style="margin-bottom: 35px; padding: 20px; border: 1px solid #e1e1e1; border-radius: 8px; background-color: #ffffff;">
                <strong style="font-size: 1.2em; color: #2c3e50;">① {paper['title_ko']}</strong><br>
                <span style="color: #7f8c8d; font-size: 0.9em;">
                    <strong>Original Title:</strong> {paper['title_en']}<br>
                    <strong>Authors:</strong> {paper['authors']}
                </span>
                <p style="margin: 15px 0; text-align: justify;">
                    <strong>상세 요약:</strong> {paper['summary']}
                </p>
                <p style="margin-bottom: 0px;"><strong>공식 레퍼런스:</strong> <a href="{paper['link']}" style="color: #3498db; text-decoration: none; font-weight: bold;">[Link] &rarr;</a></p>
            </div>
        """

    news_html = ""
    colors = {"경제": "#c0392b", "외교": "#2980b9", "사회": "#8e44ad", "금융": "#f39c12"}
    bg_colors = {"경제": "#fdf2f2", "외교": "#f0f4f8", "사회": "#f5f0f9", "금융": "#fef9e7"}
    
    for item in data['news']:
        cat = item['category']
        color = colors.get(cat, "#333")
        bg = bg_colors.get(cat, "#f9f9f9")
        news_html += f"""
            <div style="margin-bottom: 20px; padding: 15px; border-left: 5px solid {color}; background-color: {bg};">
                <strong style="color: {color}; font-size: 1.1em;">[{cat}] {item['title']}</strong>
                <p style="margin: 10px 0; font-size: 0.95em;">{item['summary']}</p>
                <p style="margin: 5px 0 0 0;"><a href="{item['link']}" style="color: {color}; text-decoration: none; font-size: 0.9em; font-weight: bold;">[관련 기사 보기] &rarr;</a></p>
            </div>
        """

    html = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; color: #333; max-width: 850px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px; background-color: #ffffff;">
        <div style="text-align: center; padding: 20px; background-color: #2c3e50; border-radius: 10px 10px 0 0; color: white;">
            <h2 style="margin: 0;">[주간 레이더 기상 및 통계/AI 전문 리포트]</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">{report_date}</p>
        </div>
        <div style="padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 25px; border-left: 5px solid #3498db;">
                <strong>금주 연구 키워드:</strong> {data['keywords']}
            </div>
            <h3 style="color: #2980b9; border-bottom: 2px solid #2980b9; padding-bottom: 5px;">1. 기상 레이더 및 구름 물리 (Radar & Cloud Physics)</h3>
            {radar_papers_html}
            <h3 style="color: #e67e22; border-bottom: 2px solid #e67e22; padding-bottom: 5px; margin-top: 45px;">2. 통계 및 AI (Statistics & AI)</h3>
            {ai_papers_html}
            <h3 style="color: #27ae60; border-bottom: 2px solid #27ae60; padding-bottom: 5px; margin-top: 45px;">3. 주간 주요 뉴스 종합 리포트</h3>
            {news_html}
        </div>
        <div style="background-color: #2c3e50; padding: 20px; border-radius: 0 0 10px 10px; color: white; text-align: center; margin-top: 40px;">
            <p style="font-size: 0.85em; margin: 0;">
                본 리포트는 Gemini CLI가 자동 생성하였습니다.<br>
                © 2026 Cloud Physics Lab
            </p>
        </div>
    </body>
    </html>
    """
    return html

def execute_full_report_task():
    print(f"[{datetime.datetime.now()}] Starting Weekly Report Task execution...")
    report_data = get_automated_content()
    
    if report_data:
        html_content = generate_report_html(report_data)
        subject = f"[주간 요약 보고서] {datetime.date.today().strftime('%Y-%m-%d')}"
        print(f"[{datetime.datetime.now()}] Sending email via SMTP...")
        success = send_email_via_smtp(email_recipient, subject, html_content, cc_recipient=email_cc)
        
        if success:
            print(f"[{datetime.datetime.now()}] Automated Professional HTML Email sent to {email_recipient}")
            return True, "Report sent successfully."
        else:
            return False, "Failed to send email via SMTP."
    else:
        return False, "Failed to generate content via Gemini API."

if __name__ == "__main__":
    success, message = execute_full_report_task()
    print(f"Result: {message}")
    if not success:
        sys.exit(1)
