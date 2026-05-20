import datetime
import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment Variables
api_key = os.getenv("GEMINI_API_KEY")
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
email_recipient = os.getenv("EMAIL_RECIPIENT", "gusdbs16@knu.ac.kr")
email_cc = os.getenv("EMAIL_CC", "dance3414@naver.com")

if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY not found.")

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

def get_automated_content():
    today = datetime.date.today()
    prompt = f"""
    당신은 기상 레이더 및 AI 분야의 전문 연구원입니다. 구글 검색을 활용하여 {today} 기준의 최신 실제 정보(뉴스 및 논문)를 바탕으로 주간 리포트 내용을 생성해주세요.
    
    필수 조건:
    1. 모든 링크는 반드시 실제로 존재하는 실시간 링크여야 합니다. 
    2. 기상 레이더, 구름 물리, 최신 AI 트렌드를 포함하세요.
    3. 반드시 다음 구조의 JSON 형식으로 답변하세요. 다른 설명은 생략하세요.
    
    {{
      "keywords": "쉼표로 구분된 3-5개의 핵심 키워드",
      "radar_papers": [
        {{
          "title_ko": "한국어 제목",
          "title_en": "Original English Title",
          "authors": "저자 정보",
          "summary": "2-3문장의 상세 요약",
          "link": "실제 논문 또는 프로젝트 페이지 URL"
        }},
        ... (2개 생성)
      ],
      "ai_papers": [
        {{
          "title_ko": "한국어 제목",
          "title_en": "Original English Title",
          "authors": "저자 정보",
          "summary": "2-3문장의 상세 요약",
          "link": "실제 논문 또는 프로젝트 페이지 URL"
        }}
      ],
      "news": [
        {{
          "category": "경제/외교/사회/금융 중 하나",
          "title": "뉴스 제목",
          "summary": "2-3문장의 상세 요약",
          "link": "실제 뉴스 기사 URL"
        }},
        ... (4개 생성)
      ]
    }}
    """
    try:
        # Standard model and tool usage for google-generativeai
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=[{'google_search_retrieval': {}}]
        )
        
        response = model.generate_content(prompt)
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
        print(f"Error generating content: {e}")
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
            recipients.append(cc_recipient)
            
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
        
        filename = f"{datetime.date.today().strftime('%Y%m%d')}_weekly_report.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        if success:
            print(f"[{datetime.datetime.now()}] Automated Professional HTML Email sent to {email_recipient}")
            return True, "Report sent successfully."
        else:
            return False, "Failed to send email via SMTP."
    else:
        return False, "Failed to generate content via Gemini API."

if __name__ == "__main__":
    execute_full_report_task()
