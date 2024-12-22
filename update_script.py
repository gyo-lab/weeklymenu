import os
import requests
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from datetime import datetime, timedelta
import re
from github import Github

# 설정
BASE_URL = "https://assembly.go.kr/portal/bbs/B0000054/list.do?pageIndex=1&menuNo=600100&sdate=&edate=&searchDtGbn=c0&pageUnit=10&pageIndex=1&cl1Cd=AN01"
PDF_SAVE_PATH = "weekly_menu.pdf"
JPG_SAVE_PATH = "weekly_menu.jpg"

def find_latest_pdf_url():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(BASE_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # 날짜 계산: 수집일 기준 3일 전부터 당일까지
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)

    # 게시물 리스트 파싱 (제목, 작성일, 다운로드 컬럼 추출)
    div_container = soup.find("div", class_="board01 pr td_center board-added")
    tbody = div_container.find("tbody")
    rows = tbody.find_all("tr") if tbody else []

    for row in rows:
        columns = row.find_all("td")   # <td> 태그로 열 가져오기
        if len(columns) >= 7:   # 다운로드 열 포함 최소 7개 확인
            title = columns[2].find("a").text.strip()   # 제목 컬럼에서 <a> 태그의 텍스트 추출
            date_text = columns[4].text.strip()   # 작성일 컬럼
            download_column = columns[6]  # 다운로드 컬럼

            # print(f"Title: {title}, Date: {date_text}, Download Tag: {download_link_tag}")

            # 날짜 확인
            try:
                post_date = datetime.strptime(date_text, "%Y-%m-%d")
                if three_days_ago <= post_date <= today and "주간식단표" in title:
                    # onclick 속성 찾기
                    link = download_column.find("a", onclick=True)
                    if link:
                        onclick_content = link["onclick"]
                        # print(f"onclick content: {onclick_content}")

                        # gfn_atchFileDownload 함수 파싱
                        match = re.search(r"gfn_atchFileDownload\('([^']*)', '([^']*)', '([^']*)', '([^']*)'\)", onclick_content)
                        if match:
                            portal, menu_no, file_id, file_sn = match.groups()

                            # URL 구성
                            base_url = "https://assembly.go.kr"
                            pdf_url = f"{base_url}/portal/cmmn/file/fileDown.do?menuNo={menu_no}&atchFileId={file_id}&fileSn={file_sn}&historyBackUrl=https%3A%2F%2Fassembly.go.kr%2Fportal%2Fbbs%2FB0000054%2Flist.do%3FpageIndex%3D1%26menuNo%3D600100%26sdate%3D%26edate%3D%26searchDtGbn%3Dc0%26pageUnit%3D10%26pageIndex%3D1%26cl1Cd%3DAN01"
                            # print(f"PDF URL: {pdf_url}")
                            return pdf_url
                    
            except ValueError:
                continue
    return None


def download_pdf(pdf_url):
    """PDF 파일 다운로드"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": BASE_URL  # 요청 출처를 명시
    }
    response = requests.get(pdf_url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(PDF_SAVE_PATH, "wb") as pdf_file:
          pdf_file.write(response.content)
        print(f"PDF 다운로드 완료: {PDF_SAVE_PATH}")
    else:
        print(f"PDF 다운로드 실패: {response.status_code}")


def convert_pdf_to_jpg():
    """PDF를 JPG로 변환"""
    images = convert_from_path(PDF_SAVE_PATH)
    if images:
        images[0].save(JPG_SAVE_PATH, "JPEG")   # 첫 페이지를 JPG로 저장

def upload_to_github(file_path, repo_name="gyo-lab/weeklymenu", branch="main"):
    """GitHub에 파일 업로드"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN 환경 변수가 설정되지 않았습니다.")

        g = Github(token)
        repo = g.get_repo(repo_name)

        with open(file_path, "rb") as file:
            content = file.read()
        
        file_name = os.path.basename(file_path)
        try:
            # 기존 파일 업데이트
            existing_file = repo.get_content(file_name, ref=branch)
            repo.update_file(existing_file.path, "Update weekly menu", content, existing_file.sha, branch=branch)
            print(f"GitHub에 {file_name} 업데이트 완료.")
        except Exception as e:
            # 새 파일 생성
            repo.create_file(file_name, "Add weekly menu", content, branch=branch)
            print(f"GitHub에 {file_name} 업로드 완료.")


def main():
    """전체 프로세스 실행"""
    pdf_url = find_latest_pdf_url()
    if pdf_url:
        # print(f"최신 PDF URL: {pdf_url}")
        download_pdf(pdf_url)
        convert_pdf_to_jpg()
        upload_to_github(JPG_SAVE_PATH)
        
    else:
        print("최신 게시물을 찾을 수 없습니다.")

if __name__ == "__main__":
    main()

