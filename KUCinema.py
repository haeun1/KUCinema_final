from __future__ import annotations
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KU 영화 예매 프로그램 — KUCinema.py

이 파일은 기획서의 6장 중 다음을 구현합니다.
  • 6.1 날짜 입력 프롬프트 (입력 날짜 검증 및 설정)
  • 6.2 로그인 프롬프트 (학번 입력 → 로그인 의사 → 기존/신규 분기 → 비밀번호 입력/설정)
  • 6.3 주 프롬프트 (메뉴 1~4와 0 종료 / 외부 모듈로 디스패치)

※ 데이터 파일 관련
  - 홈 경로({HOME}) 기준으로 다음 파일을 사용합니다.
      movie-schedule.txt : 반드시 존재해야 하며(읽기 가능), 없으면 즉시 종료
      student-info.txt   : 없으면 빈 파일 생성
      booking-info.txt   : 없으면 빈 파일 생성
  - 학생 데이터 파일(student-info.txt)은 프로그램 시작 시 최소 무결성(형식/중복) 검사를 수행합니다.

※ 메뉴 디스패치
  - 사용자가 ‘1’~‘4’를 선택하면 각각 menu1.py~menu4.py의 동일한 함수명(menu1, menu2, ...)을 실행합니다.
  - 모듈/함수가 없을 경우 친절한 오류 메시지를 출력하고 주 프롬프트로 복귀합니다.

Python 3.11 표준 라이브러리만 사용합니다.
"""

"""
    github 사용법은 노션에
"""


import os
import sys
import re
from pathlib import Path
from datetime import date
from typing import Dict, Tuple, List
from collections import defaultdict
import ast


# ---------------------------------------------------------------
# 상수 정의
# ---------------------------------------------------------------
MOVIE_FILE = "movie-info.txt"
STUDENT_FILE = "student-info.txt"
BOOKING_FILE = "booking-info.txt"
SCHEDULE_FILE = "schedule-info.txt"

# 정규식 패턴 (문법 형식)
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")          # YYYY-MM-DD
RE_STUDENT_ID = re.compile(r"^\d{2}$")                  # 2자리 숫자
RE_PASSWORD = re.compile(r"^\d{4}$")                   # 4자리 숫자
RE_STUDENT_RECORD = re.compile(r"^(?P<sid>\d{2})/(?P<pw>\d{4})$")  # 학생 레코드 형식
RE_MOVIE_ID = re.compile(r"^\d{12}$")                   # YYYYMMDDHHMM
RE_TIME = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")      # HH:MM-HH:MM
RE_TITLE = re.compile(r"^(?!\s)(?!.*\s$)[0-9A-Za-z가-힣 ]+$")  # 특수문자 제외, 앞뒤 공백 금지
RE_SEAT_VECTOR = re.compile(r"^\[(?:\s*[01]\s*,){24}\s*[01]\s*\]$")  # 길이 25의 0/1
RE_BOOKING_RECORD = re.compile(
    r"^(?P<sid>\d{2})/(?P<mid>\d{12})/(?P<vec>\[(?:\s*[01]\s*,){24}\s*[01]\s*\])$"
)

# 전역 상태 (필수 컨텍스트)
CURRENT_DATE_STR: str | None = None  # 내부 현재 날짜(문자열, YYYY-MM-DD)
LATEST_DATE_STR : str | None = None  # 최종 작업 날짜
LOGGED_IN_SID: str | None = None     # 로그인된 학번(2자리)

# ---------------------------------------------------------------
# 유틸리티 출력
# ---------------------------------------------------------------
def info(msg: str) -> None:
    print(msg)

def warn(msg: str) -> None:
    print(f"..! 경고: {msg}")

def error(msg: str) -> None:
    print(f"!!! 오류: {msg}")


# ---------------------------------------------------------------
# 파일/환경 준비
# ---------------------------------------------------------------
def home_path() -> Path:
    hp = Path(os.path.expanduser("~")).resolve() # 홈 경로 반환
    try:
        hp = Path(os.path.expanduser("~")).resolve()  # 홈 경로 반환
    except Exception as e:
        error(f"홈 경로를 파악할 수 없습니다! 프로그램을 종료합니다. {e}")
        sys.exit(1)
    # 배포하기 전은 현재 경로인 KUCinema.py 파일의 경로를 반환
    hp = Path(os.getcwd())
    #print("현재 경로:", os.getcwd())
    return hp


# ---------------------------------------------------------------
# 6.4.(5) 무결성 검사 - 전체 모두 실행하는 함수 (예매 파일 의미 규칙)
# ---------------------------------------------------------------
def verify_integrity():
    return

# ---------------------------------------------------------------
# 날짜(6.1) — 문법/의미 검증
# ---------------------------------------------------------------
def init_latest_date() -> str:
    """
    모든 데이터 파일을 읽어 가장 최근의 타임스탬프를 반환하는 함수
    반환값: str (최종 작업 날짜)
    """
    
    # 1. 로컬 변수 latest를 None으로 초기화한다.
    latest = None
    
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE    
    # 읽어야 할 파일 목록 정의
    target_files = [movie_path, schedule_path, student_path, booking_path]
    
    # 2. 영화, 상영, 학생, 예매 데이터 파일을 각각 한 레코드씩 읽는다.
    for filename in target_files:
        if not os.path.exists(filename):
            continue  # 파일이 없으면 건너뜀
            
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # A. 타임 스탬프를 읽어 로컬 변수 temp에 저장한다.
                # [가정] 데이터가 '/'로 구분되어 있고, 타임스탬프가 마지막 필드에 위치한다고 가정
                # 실제 데이터 포맷에 맞춰 인덱스나 파싱 로직을 수정해야 합니다.
                try:
                    parts = line.split('/') 
                    temp = parts[-1].strip() # 실제 타임스탬프 위치로 변경 필요
                except IndexError:
                    continue

                # B. latest에 max(latest, temp)를 할당한다.
                # 주의: Python에서 max(None, str)은 오류가 발생하므로 분기 처리 필요
                if latest is None:
                    latest = temp
                else:
                    latest = max(latest, temp)

    # 3. latest가 None인 경우, “1582-10-15”를 반환한다.
    if latest is None:
        return "1582-10-15"

    # 4. latest가 None이 아닌 경우, latest를 반환한다.
    return latest

def prompt_input_date() -> str:
    """6.1 날짜 입력 프롬프트"""
    global LATEST_DATE_STR, LOGGED_IN_SID
    LATEST_DATE_STR = init_latest_date()
    print("최종 작업 날짜:", LATEST_DATE_STR)
    while True:
        s = input("현재 날짜를 입력하세요 (YYYY-MM-DD) : ")
        # 문법/의미 체크
        if not RE_DATE.fullmatch(s):
            info("날짜 형식이 맞지 않습니다. 다시 입력해주세요")
            continue
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        try:
            date(y, m, d)
        except ValueError:
            info(f"존재하지 않는 날짜입니다. 다시 입력해주세요.")
            continue
        if s < LATEST_DATE_STR:
            info(f"최종 작업 날짜 전의 날짜입니다. 다시 입력해주세요.")
            continue
        return s


# ---------------------------------------------------------------
# 로그인 플로우(6.2)
# ---------------------------------------------------------------
def prompt_student_id() -> str:
    """6.2.1 학번 입력 — 문법 형식: 2자리 숫자, 공백 불가"""
    while True:
        sid = input("학번을 입력하세요 (2자리 숫자) : ")
        if not RE_STUDENT_ID.fullmatch(sid) and sid != "admin":
            info("학번의 형식이 올바르지 않습니다. 다시 입력해주세요.")
            continue
        return sid


def prompt_login_intent(sid: str) -> bool:
    """6.2.2 로그인 의사 — 'Y'만 긍정, 나머지는 모두 부정"""
    ans = input(f"{sid} 님으로 로그인하시겠습니까? (Y/N) : ")
    return ans == "Y"


def prompt_password_existing(expected_pw: str) -> bool:
    """6.2.3 기존 회원 비밀번호 입력.
    - 문법 형식 위배: 현재 단계(비밀번호 입력) 재시작
    - 의미 규칙 위배(불일치): 6.2.1 학번 입력으로 되돌아가야 하므로 False 반환
    - 정상: True 반환
    """
    while True:
        pw = input("비밀번호를 입력하세요 (4자리 숫자) : ")
        if expected_pw == "admin" and pw == "admin":
            return True
        if not RE_PASSWORD.fullmatch(pw):
            info("비밀번호의 형식이 올바르지 않습니다. 다시 입력해주세요.")
            continue  # 6.2.3 재시작
        if pw != expected_pw:
            info("비밀번호가 올바르지 않습니다.")
            return False  # 6.2.1로 복귀
        # 정상
        return True

def prompt_password_new(student_path: Path, sid: str, students: Dict[str, str]) -> None:
    """6.2.4 신규 회원: 비밀번호 설정 후 파일에 <학번>/<비밀번호> 추가"""
    while True:
        pw = input("신규 회원입니다. 비밀번호를 설정해주세요 (4자리 숫자) : ")
        if not RE_PASSWORD.fullmatch(pw):
            info("비밀번호의 형식이 올바르지 않습니다. 다시 입력해주세요.")
            continue
        # 파일에 추가
        with student_path.open("r", encoding="utf-8") as f:
            content = f.read()
        with student_path.open("a", encoding="utf-8", newline="\n") as f:
            if content:
                f.write(f"\n{sid}/{pw}/{CURRENT_DATE_STR}")
            else:
                f.write(f"{sid}/{pw}/{CURRENT_DATE_STR}")
        students[sid] = pw
        #info("신규 회원 가입이 완료되었습니다.")
        break


# ---------------------------------------------------------------
# 메뉴 구현 (menu1 ~ menu4)
# ---------------------------------------------------------------

# ===== menu1: 영화 예매 =====
# 기본 좌석 설정
ROWS = ["A", "B", "C", "D", "E"]
COLS = [1, 2, 3, 4, 5]

def create_seat_buffer(seat_vector: list[int]) -> dict[str, int]:
    """
    영화의 좌석 유무 벡터(길이 25, 0/1)를 
    {'A1':0, 'A2':1, ..., 'E5':1} 형태로 변환
    """
    seat_buffer: dict[str, int] = {}
    idx = 0
    for row in ROWS:
        for col in COLS:
            seat_id = f"{row}{col}"
            seat_buffer[seat_id] = seat_vector[idx]
            idx += 1
    return seat_buffer

def print_seat_board(seat_buffer: dict[str, int]) -> None:
    """
    좌석 버퍼를 기반으로 현재 좌석 상태를 콘솔에 시각화하여 출력
    - '□' : 예매 가능 (0)
    - '■' : 이미 예매됨 (1)
    - '*' : 이번 예매에서 방금 선택한 좌석 (2)
    """
    print("빈 사각형은 예매 가능한 좌석입니다.")
    print("   스크린")
    print("   ", " ".join(str(c) for c in COLS))

    for row in ROWS:
        line: list[str] = [f"{row}"]
        for col in COLS:
            seat_id = f"{row}{col}"
            val = seat_buffer[seat_id]
            if val == 0:
                line.append("□")  # 예매 가능
            elif val == 1:
                line.append("■")  # 이미 예매됨
            elif val == 2:
                #line.append("★")  # 현재 예매 중
                line.append("■")  # 현재 예매 중
        print(" ", " ".join(line))

def select_date() -> str | None:
    """
    6.4.1 날짜 선택
    - 영화 데이터 파일에서 현재 날짜 이후의 상영 날짜를 제시하고 선택을 받음
    - 정상 입력 시 해당 날짜 문자열을 반환
    - '0' 입력 시 None 반환 (주 프롬프트 복귀)
    """
    if CURRENT_DATE_STR is None:
        error("내부 현재 날짜가 설정되어 있지 않습니다.")
        return None

    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE
    lines = schedule_path.read_text(encoding="utf-8").splitlines()

    dates: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) != 7:
            continue
        _, movie_id, movie_date, _, _, valid, _ = parts
        if valid != "T":
            continue
        if movie_date > CURRENT_DATE_STR and movie_date not in dates:
            dates.append(movie_date)

    dates.sort()
    dates = dates[:9]
    n = len(dates)

    print("영화예매를 선택하셨습니다. 아래는 예매 가능한 날짜 리스트입니다.")
    if n == 0:
        info("상영이 예정된 영화가 없습니다.")
        return None

    for i, d in enumerate(dates, start=1):
        print(f"{i}) {d}")
    print("0) 뒤로 가기")

    while True:
        s = input("원하는 날짜의 번호를 입력해주세요 : ").strip()
        if not re.fullmatch(r"\d", s or "") or re.search(r"[A-Za-z]", s or ""):
            print("올바르지 않은 입력입니다. 원하는 날짜의 번호만 입력하세요.")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        if num == 0:
            return None
        return dates[num - 1]

def select_movie(selected_date: str) -> dict | None:
    """
    6.4.2 영화 선택 — 입력받은 날짜의 영화를 시간순으로 제시하고 선택
    """
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE
    scd_lines = schedule_path.read_text(encoding="utf-8").splitlines()
    movie_lines = movie_path.read_text(encoding="utf-8").splitlines()

    movie_map = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                # format: mov_id/title/runtime/valid/ts
                if len(parts) == 5 and parts[3] == 'T':
                    movie_map[parts[0]] = parts[1]

    movies: list[dict] = []
    for line in scd_lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) != 7:
            continue
        if parts[-1] < CURRENT_DATE_STR:
            continue
        if parts[-2] != "T":
            continue
        
        mov_id = parts[1]
        if mov_id in movie_map:
            title = movie_map[mov_id]
            scd_id = parts[0]
            date_str = parts[2]
            time_str = parts[3]
            seats = parts[4]
            if date_str == selected_date:
                movies.append({
                    "id": scd_id,
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "seats": ast.literal_eval(seats)
                })
    def sort_key(m: dict) -> str:
        return m["time"].split("-")[0]
    movies.sort(key=sort_key)
    n = len(movies)

    print(f"{selected_date}의 상영시간표입니다.")
    if n == 0:
        info("해당 날짜에는 상영 중인 영화가 없습니다.")
        return None

    for i, m in enumerate(movies, start=1):
        print(f"{i}) {m['date']} {m['time']} | {m['title']}")
    print("0) 뒤로 가기")

    while True:
        s = input("원하는 영화의 번호를 입력해주세요 : ").strip()
        if not re.fullmatch(r"\d", s or "") or re.search(r"[A-Za-z]", s):
            print("올바르지 않은 입력입니다. 원하는 영화의 번호만 입력해주세요.")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("해당 번호의 영화가 존재하지 않습니다. 다시 입력해주세요.")
            continue
        if num == 0:
            return None
        return movies[num - 1]

def input_people(selected_movie: dict) -> int | None:
    """6.4.3 인원 수 입력 — 최대 4명, 0이면 이전 단계로"""
    movie_date = selected_movie["date"]
    movie_time = selected_movie["time"]
    movie_title = selected_movie["title"]

    while True:
        s = input(f"{movie_date} {movie_time} | 〈{movie_title}〉를 선택하셨습니다. 인원 수를 입력해주세요 (최대 4명): ").strip()
        if not re.fullmatch(r"\d", s or "") or re.search(r"[A-Za-z]", s):
            print("올바르지 않은 입력입니다. 한 자리 숫자만 입력하세요.")
            continue
        n = int(s)
        if not (0 <= n <= 4):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        if n == 0:
            return None
        return n

def finalize_booking(selected_movie: dict, chosen_seats: list[str], student_id: str,
                     schedule_path: Path, booking_path: Path) -> None:
    scd_id = selected_movie["id"]
    # 이번 예매의 좌석 벡터 만들기 (내가 선택한 좌석만 1)
    new_booking_vector = [0] * 25
    for seat in chosen_seats:
        row_idx = ROWS.index(seat[0])
        col_idx = int(seat[1]) - 1
        new_booking_vector[row_idx * 5 + col_idx] = 1

    # schedule-info.txt 업데이트 (기존 1 유지 + 새 1 추가)
    lines = schedule_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    for line in lines:
        parts = line.strip().split("/")
        if len(parts) != 7:
            updated_lines.append(line)
            continue
        scd_id_in_file = parts[0].strip()
        if scd_id_in_file == scd_id:
            seats = ast.literal_eval(parts[-3])
            for i in range(25):
                seats[i] = 1 if (seats[i] == 1 or new_booking_vector[i] == 1) else 0
            parts[-3] = "[" + ",".join(map(str, seats)) + "]"
            updated_line = "/".join(parts)

            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)
    schedule_path.write_text("\n".join(updated_lines), encoding="utf-8")

    # booking-info.txt에 새로운 예매 레코드 추가
    with open(booking_path, "a+", encoding="utf-8") as f:
        f.seek(0)
        is_empty = (f.read().strip() == "")
        booking_vec_str = ",".join(map(str, new_booking_vector))
        if is_empty:
            f.write(f"{student_id}/{scd_id}/[{booking_vec_str}]/T/{CURRENT_DATE_STR}")
        else:
            f.write(f"\n{student_id}/{scd_id}/[{booking_vec_str}]/T/{CURRENT_DATE_STR}")

def input_seats(selected_movie: dict, n: int) -> bool:
    """
    6.4.4 좌석 입력 — 좌석 문법/예매 가능 여부/중복 검사 후 선택 처리
    """
    seat_vector = selected_movie["seats"]
    seat_buffer = create_seat_buffer(seat_vector)
    print_seat_board(seat_buffer)
    print()

    chosen_seats: list[str] = []
    k = 0
    while k < n:
        s = input(f"{k + 1}번째로 예매할 좌석을 입력하세요. (예:A1): ").strip().upper()
        if s == "0":
            return False
        if not re.fullmatch(r"[A-E][1-5]", s) or re.search(r"[가-힣]", s):
            print("올바르지 않은 입력입니다.")
            continue
        if seat_buffer[s] == 1:
            print("이미 예매된 좌석입니다.")
            continue
        if s in chosen_seats:
            print("동일 좌석 중복 선택은 불가능합니다.")
            continue
        seat_buffer[s] = 2
        chosen_seats.append(s)
        k += 1
        if k < n:
            print()
            print_seat_board(seat_buffer)
            print()
            continue
        else:
            schedule_path = home_path() / SCHEDULE_FILE
            booking_path = home_path() / BOOKING_FILE
            finalize_booking(
                selected_movie=selected_movie,
                chosen_seats=chosen_seats,
                student_id=LOGGED_IN_SID,
                schedule_path=schedule_path,
                booking_path=booking_path,
            )
            print(f"{', '.join(chosen_seats)} 자리 예매가 완료되었습니다. 주 프롬프트로 돌아갑니다.")
            return True

def menu1() -> None:
    movie_path = home_path() / MOVIE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE

    if LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return

    # 1️⃣ 날짜 선택
    while True:
        selected_date = select_date()
        if selected_date is None:
            return  # 완전히 종료

        # 2️⃣ 영화 선택
        while True:
            selected_movie = select_movie(selected_date)
            if selected_movie is None:
                break  # 날짜 선택으로 돌아가기

            # 3️⃣ 인원 수 입력
            while True:
                num_people = input_people(selected_movie)
                if num_people is None:
                    break  # 영화 선택으로 돌아가기

                # 4️⃣ 좌석 선택
                seat_input_success = input_seats(selected_movie, num_people)
                if not seat_input_success:
                    # 좌석 선택 실패 → 인원 수 입력으로 돌아감
                    continue  

                # 예매 성공 시 검증
                verify_integrity()
                return  # 모든 과정 완료 → 함수 종료


# ===== menu2: 예매 내역 조회 =====
def get_movie_details() -> dict[str, dict]:
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE

    movie_map = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                # format: mov_id/title/runtime/valid/ts
                if len(parts) == 5 and parts[3] == 'T':
                    movie_map[parts[0]] = parts[1]

    lines = schedule_path.read_text(encoding="utf-8").splitlines()
    details: dict[str, dict] = {}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if len(parts) == 7:
            schedule_id = parts[0].strip()
            movie_id = parts[1].strip()
            title = movie_map[movie_id]
            date_str = parts[2].strip()
            time_str = parts[3].strip()
            details[schedule_id] = {"title": title, "date": date_str, "time": time_str}
    return details

def vector_to_seats(vector: list[int]) -> list[str]:
    booked_seats: list[str] = []
    for i, status in enumerate(vector):
        if status == 1:
            row = ROWS[i // 5]
            col = COLS[i % 5]
            booked_seats.append(f"{row}{col}")
    return booked_seats

def menu2() -> None:
    """
    6.3.2 예매 내역 조회 — 현재 로그인 사용자의 '지나가지 않은' 예매 내역 출력
    """
    if not LOGGED_IN_SID:
        error("로그인 정보가 없습니다. 먼저 로그인해주세요.")
        return
    if not CURRENT_DATE_STR:
        error("가상 현재 날짜가 설정되지 않았습니다.")
        return
    booking_path = home_path() / BOOKING_FILE
    movie_details = get_movie_details()

    try:
        lines = booking_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        error(f"'{BOOKING_FILE}' 파일을 찾을 수 없습니다.")
        return
    user_bookings: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if len(parts) == 5 and parts[0].strip() == LOGGED_IN_SID:
            movie_id = parts[1].strip()
            if movie_id not in movie_details:
                continue
            movie_info = movie_details[movie_id]
            movie_date = movie_info["date"]
            if movie_date < CURRENT_DATE_STR:
                continue
            vector_str = parts[2].strip()
            seat_vector = ast.literal_eval(vector_str)
            user_bookings.append({
                "title": movie_info["title"],
                "date": movie_date,
                "time": movie_info["time"],
                "seats": vector_to_seats(seat_vector),
            })
    print(f"\n{LOGGED_IN_SID} 님의 예매 내역입니다.")
    if not user_bookings:
        print(f"{LOGGED_IN_SID} 님의 예매 내역이 존재하지 않습니다. 주 프롬프트로 돌아갑니다.")
    else:
        user_bookings.sort(key=lambda b: (b['date'], b['time']))
        for i, booking in enumerate(user_bookings, 1):
            seat_list_str = ", ".join(booking["seats"])
            print(f"{i}) {booking['date']} {booking['time']} | {booking['title']} | 좌석: {seat_list_str}")
    print("주 프롬프트로 돌아갑니다.")


# ===== menu3: 예매 취소 =====
def load_records(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()

def parse_schedule_record(line: str) -> dict:
    uid, movie_id, ddate, ttime, seats, _, _ = line.split("/")
    return {
        "uid": uid.strip(),
        "movie_id": movie_id.strip(),
        "date": ddate.strip(),
        "time": ttime.strip(),
        "seats": ast.literal_eval(seats.strip()),
    }

def parse_booking_record(line: str) -> dict:
    sid, uid, seats = line.split("/", 2)
    return {"sid": sid.strip(), "uid": uid.strip(), "seats": ast.literal_eval(seats.strip())}

def save_records(path: Path, records: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for i, line in enumerate(records):
            line = line.strip()
            if i < len(records) - 1:
                f.write(line + "\n")
            else:
                f.write(line)

def select_cancelation(student_id: str) -> dict | None:
    if CURRENT_DATE_STR is None:
        error("내부 현재 날짜가 설정되어 있지 않습니다.")
        return None
    booking_path = home_path() / BOOKING_FILE
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE
    booking_lines = booking_path.read_text(encoding="utf-8").splitlines()
    movie_lines = movie_path.read_text(encoding="utf-8").splitlines()
    schedule_lines = schedule_path.read_text(encoding="utf-8").splitlines()

    movie_map = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                # format: mov_id/title/runtime/valid/ts
                if len(parts) == 5 and parts[3] == 'T':
                    movie_map[parts[0]] = parts[1]

    bookings: list[dict] = []
    for line in booking_lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) != 5:
            continue
        student_who_booked, scd_id, seat_vec, validity, timestamp = parts
        if validity != "T":
            continue
        movie_date = scd_id[0:4] + "-" + scd_id[4:6] + "-" + scd_id[6:8]
        if student_id == student_who_booked and movie_date > CURRENT_DATE_STR and validity == "T":
            for scd_line in schedule_lines:
                if not scd_line.strip():
                    continue
                scd_parts = scd_line.split("/")
                if not scd_parts:
                    continue
                line_scd_id = scd_parts[0].strip()

                if scd_id == line_scd_id:
                    pm = parse_schedule_record(scd_line)
                    if pm is None:
                        error(f"parse_movie_record 실패: {scd_line}")
                        continue
                    
                    bookings.append({
                        "scd_id": scd_id.strip(),
                        "seats": ast.literal_eval(seat_vec.strip()),
                        "title": movie_map[pm["movie_id"]],
                        "date": pm["date"],
                        "time": pm["time"],
                    })
                    break
    if not bookings:
        info(f"{student_id}님의 예매 내역이 존재하지 않습니다. 주 프롬프트로 돌아갑니다.")
        return None
    bookings.sort(key=lambda x: x["scd_id"])
    bookings = bookings[:9]
    n = len(bookings)
    info(f"{student_id}님의 예매 내역입니다.")
    seat_names = [f"{row}{col}" for row in "ABCDE" for col in range(1, 6)]
    for i, d in enumerate(bookings, start=1):
        booked = [seat_names[idx] for idx, v in enumerate(d['seats']) if v == 1]
        seat_str = " ".join(booked) if booked else "(예매된 좌석 없음)"
        print(f"{i}) {d['date']} {d['time']} | {d['title']} | {seat_str}")
    print("0) 뒤로 가기")
    while True:
        s = input("예매를 취소할 내역을 선택해주세요. (번호로 입력) : ").strip()
        if not re.fullmatch(r"\d", s):
            print("올바르지 않은 입력입니다. 취소할 내역의 번호만 입력하세요.")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        if num == 0:
            return None
        return bookings[num - 1]

def confirm_cancelation(selected_booking: dict) -> None:
    schedule_path = home_path() / SCHEDULE_FILE
    booking_path = home_path() / BOOKING_FILE

    seat_names = [f"{row}{col}" for row in "ABCDE" for col in range(1, 6)]

    seats = selected_booking.get('seats', [])
    if not seats:
        print("(예매된 좌석 없음)")
        return
    booked = [seat_names[idx] for idx, v in enumerate(seats) if v == 1]
    seat_str = " ".join(booked) if booked else "(예매된 좌석 없음)"
    n = input(f"{selected_booking['date']} {selected_booking['time']} | {selected_booking['title']} | {seat_str}의 예매를 취소하겠습니까? (Y/N) : ")
    
    if n == 'Y':
        booking_lines = booking_path.read_text(encoding="utf-8").splitlines()
        new_booking_lines: list[str] = []
        for line in booking_lines:
            if not line.strip():
                continue
            parts = line.split("/")
            if len(parts) != 5:
                continue
            student_who_booked, scd_id, seat_vec, validity, _ = parts
            if (student_who_booked == LOGGED_IN_SID and 
                scd_id == selected_booking['scd_id'] and 
                ast.literal_eval(seat_vec.strip()) == selected_booking['seats'] and
                validity == "T"):
                line = f"{student_who_booked}/{scd_id}/{seat_vec}/F/{CURRENT_DATE_STR}"
            new_booking_lines.append(line)

        schedule_lines = schedule_path.read_text(encoding="utf-8").splitlines()
        new_schedule_lines: list[str] = []
        for line in schedule_lines:
            if not line.strip():
                continue
            parts = line.split("/")
            if len(parts) != 7:
                continue
            uid, scd_id, ddate, ttime, seats, validity, _ = parts
            if uid == selected_booking['scd_id']:
                current_seats = ast.literal_eval(seats.strip())
                restored_seats = [max(0, cs - ss) for cs, ss in zip(current_seats, selected_booking['seats'])]
                seat_str2 = "[" + ",".join(map(str, restored_seats)) + "]"
                new_line = f"{uid}/{scd_id}/{ddate}/{ttime}/{seat_str2}/T/{CURRENT_DATE_STR}"
                new_schedule_lines.append(new_line)
            else:
                new_schedule_lines.append(line)

        save_records(booking_path, new_booking_lines)
        save_records(schedule_path, new_schedule_lines)
        info("예매가 취소되었습니다.")
    else:
        menu3()
        return

    verify_integrity()
    # 6.6.1 재실행
    menu3()

def menu3() -> None:
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE
    if LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return
    selected_cancelation = select_cancelation(LOGGED_IN_SID)
    if selected_cancelation is None:
        return
    confirm_cancelation(selected_cancelation)
    
    verify_integrity()


# ===== menu4: 상영 시간표 조회 =====
def menu4() -> None:
    """
    6.3.4 상영 시간표 조회 — 현재 날짜 이후 상영 시간표 출력
    """
    if not CURRENT_DATE_STR:
        error("가상 현재 날짜가 설정되지 않았습니다. 프로그램을 다시 시작해주세요.")
        return
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE

    movie_map = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                # format: mov_id/title/runtime/valid/ts
                if len(parts) == 5 and parts[3] == 'T':
                    movie_map[parts[0]] = parts[1]
    try:
        lines = schedule_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        error(f"'{SCHEDULE_FILE}' 파일을 찾을 수 없습니다.")
        return
    available_movies: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if len(parts) == 7:
            movie_date = parts[2].strip()
            if movie_date < CURRENT_DATE_STR:
                continue
            available_movies.append({
                "date": movie_date,
                "time": parts[3].strip(),
                "title": movie_map[parts[1].strip()],
            })
    print(f"상영시간표 조회를 선택하셨습니다. 현재 조회 가능한 모든 상영 시간표를 출력합니다.")
    if not available_movies:
        print("상영이 예정된 영화가 없습니다.")
    else:
        available_movies.sort(key=lambda m: (m['date'], m['time']))
        for i, movie in enumerate(available_movies, 1):
            print(f"{i}) {movie['date']} {movie['time']} | {movie['title']}")
    print("모든 상영 시간표 출력이 완료되었습니다. 주 프롬프트로 돌아갑니다.")

# ===== menu0: 종료 =====
def menu0() -> None:
    info("프로그램을 종료합니다.")
    sys.exit(0)


# ---------------------------------------------------------------
# 주 프롬프트(6.3) & 메뉴 디스패치
# ---------------------------------------------------------------
def show_main_menu() -> None:
    print()
    print("원하는 동작에 해당하는 번호를 입력하세요.")
    print("1) 영화 예매")
    print("2) 예매 내역 조회")
    print("3) 예매 취소")
    print("4) 상영 시간표 조회")
    print("0) 종료")


def dispatch_menu(choice: str) -> None:
    """동일 파일 내의 menu1~menu4 함수를 직접 호출."""
    mapping = {
        "0": menu0,
        "1": menu1,
        "2": menu2,
        "3": menu3,
        "4": menu4,
    }
    func = mapping.get(choice)
    if func is None:
        error("잘못된 메뉴 선택입니다.")
        return
    try:
        func()
    except SystemExit:
        raise
    except Exception as e:
        error(f"메뉴 실행 중 예외가 발생했습니다: {e}")


def main_prompt_loop() -> None:
    """6.3 주 프롬프트 — 입력 검증 및 분기"""
    while True:
        show_main_menu()
        s = input("")

        # 문법 형식: 숫자만의 길이 1
        if not re.fullmatch(r"\d", s or ""):
            info("올바르지 않은 입력입니다. 원하는 동작에 해당하는 번호만 입력하세요.")
            continue

        # 의미 규칙: {1,2,3,4,0}
        if s not in {"1", "2", "3", "4", "0"}:
            info("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue

        # 1~4: 해당 메뉴 모듈로 디스패치
        dispatch_menu(s)

# ---------------------------------------------------------------
# 영화 데이터 추가(8.2)
# ---------------------------------------------------------------
def input_movie_title() -> str | None:
    """
    2. input_movie_title
    - 기능: 영화 제목 입력 및 유효성 검증
    - 반환값: 입력 받은 영화 제목(str) 또는 None
    """
    
    # 1. 영화 데이터 파일로부터 레코드 유효 여부가 T인 모든 영화 제목을 읽어 튜플로 저장
    existing_titles = set()
    if os.path.exists(MOVIE_FILE):
        with open(MOVIE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                # 포맷: id/title/time/validity/date (구분자 '/' 기준)
                parts = line.split('/')
                if len(parts) >= 4 and parts[3] == 'T':
                    existing_titles.add(parts[1])
    
    existing_titles_tuple = tuple(existing_titles)

    while True:
        # 2. 영화 제목 입력 받기
        title = input("추가할 영화 제목을 입력하세요 : ")

        # 5. "0"인 경우, None 반환
        if title == "0":
            return None

        # 3. 유효성 검증 (특수문자 제외, 앞뒤 공백 확인)
        if not RE_TITLE.fullmatch(title):
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        # 4. 중복 제목 확인
        if title in existing_titles_tuple:
            print("이미 존재하는 영화 제목입니다. 다시 입력해주세요.")
            continue

        # 6. 모든 조건 만족 시 반환
        return title

def input_running_time() -> int | None:
    """
    3. input_running_time
    - 기능: 러닝 타임 입력 (1~240분)
    """
    while True:
        s = input("추가할 영화의 러닝 타임(분)을 입력하세요 (1~240): ")

        if s == "0":
            return None

        # 숫자 여부 및 길이(3자리 이하) 확인
        if not s.isdigit() or len(s) > 3:
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue
        
        running_time = int(s)

        # 범위 확인
        if not (1 <= running_time <= 240):
            print("러닝타임은 1~240분 사이 정수만 입력하세요. 다시 입력해주세요.")
            continue

        return running_time

def add_movie(movie_title: str, running_time: int):
    """
    4. add_movie
    - 기능: 영화 데이터 파일에 레코드 추가
    """
    current_ids = set()
    movie_file = home_path() / MOVIE_FILE
    file_exists = os.path.exists(MOVIE_FILE)
    is_empty = True

    with open(movie_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.strip():
            is_empty = False
            f.seek(0)
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split('/')
                if parts[0].isdigit():
                    current_ids.add(int(parts[0]))
    
    movie_id = 1
    while movie_id in current_ids:
        movie_id += 1

    record = f"{movie_id:04d}/{movie_title}/{running_time}/T/{CURRENT_DATE_STR}"

    # 2. 파일 쓰기
    with open(MOVIE_FILE, 'a', encoding='utf-8') as f:
        if not is_empty:
            f.write(f"\n{record}")
        else:
            f.write(record)

def admin_menu1():
    """
    1. admin_menu1
    - 기능: 영화 데이터 추가 기능의 메인 함수
    """
    # 1. 반복문 진입 (처리 과정 1.A)
    while True:
        # 2. 영화 제목 입력 (처리 과정 2)
        movie_title = input_movie_title()
        
        # 2.B / 1.A : movie_title이 None이면 함수 종료
        if movie_title is None:
            return

        # 중첩된 반복문 (러닝타임 입력 루프)
        while True:
            # 3. 러닝 타임 입력 (처리 과정 3)
            running_time = input_running_time()

            # 3.B / 1.B.i : running_time이 None이면 내부 루프 탈출 -> 제목 입력 다시 수행
            if running_time is None:
                break
            
            # 4. 영화 레코드 추가 (처리 과정 4)
            # running_time이 정상적으로 입력된 경우 여기서 추가하고 함수 종료
            add_movie(movie_title, running_time)
            print("영화가 추가되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
            
            # 5. 데이터 무결성 검사 (처리 과정 5)
            verify_integrity()
            
            # 6. admin_menu1 함수 종료 (처리 과정 6)
            return
# ---------------------------------------------------------------
# 영화 데이터 수정(8.3)
# ---------------------------------------------------------------
def print_modifiable_movie_list() -> set:
    """
    수정 가능한 영화 목록(상영 정보가 없는 영화)을 출력하고 ID 집합 반환
    """
    movie_data = {}  # {id: (title, runtime)}
    screening_ids = set()
    movie_file = home_path() / MOVIE_FILE
    schedule_file = home_path() / SCHEDULE_FILE
    # 1. 영화 데이터 파일 읽기 (유효여부 T인 것만)
    with open(movie_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('/')
            # parts: [id, title, running_time, valid, date]
            if len(parts) == 5 and parts[3] == 'T':
                movie_data[parts[0]] = (parts[1], parts[2])

    # 2. 상영 데이터 파일 읽기 (유효여부 T인 것만)
    with open(schedule_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('/')
            # 상영 데이터 구조: id/movie_id/.../valid/... 
            if len(parts) == 7 and parts[-2] == 'T': 
                screening_ids.add(parts[1]) 

    # 3. 차집합 연산 (영화 파일엔 있고, 상영 파일엔 없는 것)
    modifiable_ids = set(movie_data.keys()) - screening_ids

    # 4 ~ 7. 출력
    print("수정 가능한 영화 목록입니다. 수정할 영화의 영화 고유 번호를 입력해주세요.")
    print("영화 고유 번호 | 영화 제목 | 러닝 타임(분)")
    # 정렬하여 출력 (선택 사항이나 보기 좋게 하기 위함)
    sorted_ids = sorted(list(modifiable_ids))
    for mid in sorted_ids:
        title, runtime = movie_data[mid]
        print(f"{mid} | {title} | {runtime}")

    print("0. 뒤로 가기")

    # 8. 반환
    return modifiable_ids

def input_modify_movie_id(modifiable_movie: set) -> str | None:
    """
    수정할 영화 고유 번호 입력
    """
    while True:
        # 1. 입력
        mid = input("수정할 영화의 영화 고유 번호를 입력해주세요 : ")

        # 4. "0"인 경우 반환
        if mid == "0":
            return None

        # 2. 형식 검사 (길이 4, 숫자)
        if len(mid) != 4 or not mid.isdigit():
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        # 3. 수정 가능한 목록에 있는지 검사
        if mid not in modifiable_movie:
            print("수정 가능한 영화 고유번호만 입력 가능합니다. 다시 입력해주세요.")
            continue

        # 5. 반환
        return mid

def input_modify_movie_func(movie_id: str) -> str | None:
    """
    수정할 항목(제목/러닝타임) 선택
    """
    # 현재 영화 정보를 가져오기 위한 파일 읽기 (출력 메시지 구성을 위해)
    current_title = ""
    current_time = ""
    
    with open(MOVIE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('/')
            if parts[0] == movie_id and parts[3] == 'T':
                current_title = parts[1]
                current_time = parts[2]
                break
    
    # 1 ~ 4. 메뉴 출력
    print(f"<{movie_id} | {current_title} | {current_time}>을 선택하셨습니다. 원하는 동작에 해당하는 번호를 입력해주세요.")
    print("1. 영화 제목 수정")
    print("2. 러닝 타임 수정")
    print("0. 뒤로 가기")

    while True:
        # 5. 입력
        func = input("번호를 입력하세요: ")

        # 8. "0" 반환
        if func == "0":
            return None

        # 6. 한 자리 정수 검사
        if len(func) != 1 or not func.isdigit():
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        # 7. 범위 검사 (1~2) -> 0은 위에서 처리했으므로 1, 2만 확인
        if func not in ["1", "2"]:
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue

        # 9. 반환
        return func

def input_modify_movie_title() -> str | None:
    """
    수정할 영화 제목 입력
    """
    # 1. 기존 제목 로딩
    existing_titles = set()
    if os.path.exists(MOVIE_FILE):
        with open(MOVIE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 4 and parts[3] == 'T':
                    existing_titles.add(parts[1])

    while True:
        # 2. 입력
        title = input("수정할 영화 제목을 입력하세요 : ")

        # 5. "0" 반환
        if title == "0":
            return None

        # 3. 유효성 검증 (RE_TITLE 활용)
        if not RE_TITLE.match(title):
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        # 4. 중복 검사
        if title in existing_titles:
            print("이미 존재하는 영화 제목입니다. 다시 입력해주세요.")
            continue

        # 6. 반환
        return title

def input_modify_running_time() -> int | None:
    """
    수정할 러닝 타임 입력
    """
    while True:
        # 1. 입력
        s = input("수정할 러닝 타임을 입력해주세요 (1~240): ")

        # 4. "0" 반환
        if s == "0":
            return None

        # 2. 형식 검사
        if not s.isdigit() or len(s) > 3:
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        val = int(s)
        # 3. 범위 검사
        if not (1 <= val <= 240):
            print("러닝타임은 1~240분 사이 정수만 입력하세요. 다시 입력해주세요.")
            continue

        # 5. 반환
        return val

def modify_movie(movie_id: str, movie_title: str | None, running_time: int | None):
    """
    영화 레코드 수정 (기존 레코드 F 처리 -> 바로 뒤에 새 레코드 T 추가)
    """
    if not os.path.exists(MOVIE_FILE):
        return

    lines = []
    with open(MOVIE_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    target_index = -1
    original_line = ""
    
    # 1. 수정 대상 찾기
    for i, line in enumerate(lines):
        parts = line.strip().split('/')
        if parts[0] == movie_id and parts[3] == 'T':
            target_index = i
            original_line = line.strip()
            break
    
    if target_index != -1:
        # 기존 정보 파싱
        parts = original_line.split('/')
        old_title = parts[1]
        old_time = parts[2]
        
        # 수정할 값 결정 (입력된 값이 없으면 기존 값 유지)
        new_title = movie_title if movie_title is not None else old_title
        new_time = running_time if running_time is not None else old_time
        
        # 2. 기존 레코드 유효여부 F로 변경
        # 포맷: id/title/time/valid/date
        # 날짜도 업데이트해야 하는지 명세엔 없으나, 보통 수정 시점 날짜로 하거나 기존 유지.
        # 여기서는 기존 레코드의 내용은 건드리지 않고 유효성만 F로 바꿉니다.
        parts[3] = 'F' 
        lines[target_index] = "/".join(parts) + "\n"

        # 3. 새로운 레코드 생성 및 삽입
        new_record = f"{movie_id}/{new_title}/{new_time}/T/{CURRENT_DATE_STR}\n"
        
        # "동일한 위치에 그 직후에" 추가
        lines.insert(target_index + 1, new_record)

        # 파일 다시 쓰기
        with open(MOVIE_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)

def admin_menu2():
    """
    4.3 영화 데이터 수정 메인 함수
    """
    while True:
        # 2. 수정 가능한 영화 목록 출력
        modifiable_movies = print_modifiable_movie_list()

        # 3. 영화 고유 번호 입력
        movie_id = input_modify_movie_id(modifiable_movies)
        
        # 3.B "0" 입력 시 종료
        if movie_id is None:
            return

        while True:
            # 4. 작업 번호 입력
            func = input_modify_movie_func(movie_id)
            
            # 4.B "0" 입력 시 상위(영화 선택)로 이동
            if func is None:
                break
            
            final_title = None
            final_time = None
            
            # 4.D 분기 처리
            if func == "1":
                # 5. 영화 제목 수정
                final_title = input_modify_movie_title()
                # 5.B "0" 입력 시 상위(작업 선택)로 이동
                if final_title is None:
                    continue
            
            elif func == "2":
                # 6. 러닝 타임 수정
                final_time = input_modify_running_time()
                # 6.B "0" 입력 시 상위(작업 선택)로 이동
                if final_time is None:
                    continue
            
            # 7. 영화 레코드 수정
            # modify_movie는 (id, title, time)을 받음. 수정 안 하는 건 None 전달
            modify_movie(movie_id, final_title, final_time)
            
            print("수정이 완료되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
            
            # 8. 무결성 검사
            verify_integrity()
            
            # 9. 함수 종료
            return
# ---------------------------------------------------------------
# 영화 데이터 추가(8.2)
# ---------------------------------------------------------------
def print_deletable_movie_list() -> set:
    """
    삭제 가능한 영화 목록(상영 정보가 없는 영화)을 출력하고 ID 집합 반환
    """
    movie_data = {}  # {id: (title, runtime)}
    screening_ids = set()
    movie_file = home_path() / MOVIE_FILE
    schedule_file = home_path() / SCHEDULE_FILE
    # 1. 영화 데이터 파일 읽기 (유효여부 T인 것만)
    with open(movie_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('/')
            # parts: [id, title, running_time, valid, date]
            if len(parts) == 5 and parts[3] == 'T':
                movie_data[parts[0]] = (parts[1], parts[2])

    # 2. 상영 데이터 파일 읽기 (유효여부 T인 것만)
    with open(schedule_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('/')
            # 상영 데이터 구조: id/movie_id/.../valid/... 
            if len(parts) == 7 and parts[-2] == 'T': 
                screening_ids.add(parts[1]) 

    # 3. 차집합 연산 (영화 파일엔 있고, 상영 파일엔 없는 것)
    deletable_ids = set(movie_data.keys()) - screening_ids

    # 4 ~ 7. 출력
    print("삭제 가능한 영화 목록입니다. 삭제할 영화의 영화 고유 번호를 입력해주세요.")
    print("영화 고유 번호 | 영화 제목 | 러닝 타임(분)")
    
    # 정렬하여 출력
    sorted_ids = sorted(list(deletable_ids))
    for mid in sorted_ids:
        title, runtime = movie_data[mid]
        print(f"{mid} | {title} | {runtime}")
        
    print("0. 뒤로 가기")

    # 8. 반환
    return deletable_ids

def input_delete_movie_id(movie_set: set) -> str | None:
    """
    삭제할 영화 고유 번호 입력 및 검증
    """
    while True:
        # 1. 입력
        mid = input("삭제할 영화의 영화 고유 번호를 입력해주세요 : ")

        # 4. "0"인 경우 반환
        if mid == "0":
            return None

        # 2. 형식 검사 (길이 4, 숫자)
        if len(mid) != 4 or not mid.isdigit():
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        # 3. 삭제 가능한 목록에 있는지 검사
        if mid not in movie_set:
            print("삭제 가능한 영화 고유 번호만 입력 가능합니다. 다시 입력해주세요.")
            continue

        # 5. 반환
        return mid

def delete_movie(movie_id: str):
    """
    영화 레코드 삭제 (유효 여부를 T -> F로 수정 및 날짜 업데이트)
    """
    if not os.path.exists(MOVIE_FILE):
        return

    lines = []
    with open(MOVIE_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        parts = line.strip().split('/')
        # 1. 대상 찾기 (ID 일치, 유효성 T)
        if len(parts) >= 5 and parts[0] == movie_id and parts[3] == 'T':
            # 2. 수정 (T -> F, 날짜 업데이트)
            parts[3] = 'F'
            parts[4] = CURRENT_DATE_STR
            
            # 다시 합쳐서 리스트 업데이트
            lines[i] = "/".join(parts) + "\n"
            updated = True
            break # ID는 고유하므로 찾으면 중단
    
    if updated:
        with open(MOVIE_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)

def admin_menu3():
    """
    4.4 영화 데이터 삭제 메인 함수
    """
    while True:
        # 2. 삭제 가능한 영화 목록 출력 (처리 과정 2)
        deletable_movie = print_deletable_movie_list()

        # 3. 영화 고유 번호 입력 (처리 과정 3)
        movie_id = input_delete_movie_id(deletable_movie)
        
        # 3.B / 2.A "0" 입력 시 종료
        if movie_id is None:
            return

        # 4. 영화 레코드 삭제 (처리 과정 4)
        delete_movie(movie_id)
        print("해당 영화가 삭제되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
        
        # 5. 데이터 무결성 검사 (처리 과정 5)
        verify_integrity()
        
        # 6. 함수 종료 (처리 과정 6)
        return
# ---------------------------------------------------------------
# 관리자 주 프롬프트(8.1) & 메뉴 디스패치
# ---------------------------------------------------------------
def show_admin_main_menu() -> None:
    print()
    print("원하는 동작에 해당하는 번호를 입력하세요.")
    print("1) 영화 데이터 추가")
    print("2) 영화 데이터 수정")
    print("3) 영화 데이터 삭제")
    print("4) 상영 시간표 추가")
    print("5) 상영 시간표 수정")
    print("6) 상영 시간표 삭제")
    print("0) 종료")

def dispatch_admin_menu(choice: str) -> None:
    """동일 파일 내의 admin_menu1~admin_menu6 함수를 직접 호출."""
    mapping = {
        "0": menu0,
        "1": admin_menu1,
        "2": admin_menu2,
        "3": admin_menu3,
        # "4": admin_menu4,
        # "5": admin_menu5,
        # "6": admin_menu6,
    }
    func = mapping.get(choice)
    if func is None:
        error("잘못된 메뉴 선택입니다.")
        return
    try:
        func()
    except SystemExit:
        raise
    except Exception as e:
        error(f"메뉴 실행 중 예외가 발생했습니다: {e}")

def admin_main_prompt_loop() -> None:
    """6.3 주 프롬프트 — 입력 검증 및 분기"""
    while True:
        show_admin_main_menu()
        s = input("")

        # 문법 형식: 숫자만의 길이 1
        if not re.fullmatch(r"\d", s or ""):
            info("올바르지 않은 입력입니다. 원하는 동작에 해당하는 번호만 입력하세요.")
            continue

        # 의미 규칙: {1,2,3,4,5,6,0}
        if s not in {"1", "2", "3", "4", "5", "6", "0"}:
            info("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue

        # 1~6: 해당 메뉴 모듈로 디스패치
        dispatch_admin_menu(s)


# ---------------------------------------------------------------
# 엔트리포인트: 전체 플로우 결합
# ---------------------------------------------------------------
def main() -> None:
    global CURRENT_DATE_STR, LATEST_DATE_STR, LOGGED_IN_SID
    students = {}
    student_path = home_path() / STUDENT_FILE
    for line in student_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) != 3:
            continue
        sid, pw, _ = parts
        students[sid] = pw
    # 1) 6.1 — 날짜 입력
    CURRENT_DATE_STR = prompt_input_date()  # 내부 현재 날짜 확정

    print(LATEST_DATE_STR)
    # 2) 6.2 — 로그인 플로우
    while True:
        sid = prompt_student_id()  # 6.2.1
        if not prompt_login_intent(sid):  # 6.2.2 (부정이면 학번 입력 재시작)
            continue

        if sid in students or sid == "admin":  # 기존 회원 → 6.2.3
            if sid == "admin":
                ok = prompt_password_existing("admin")
            else:
                ok = prompt_password_existing(students[sid])
            if not ok:
                # 의미 규칙 위배(비밀번호 불일치) → 6.2.1로 되돌아감
                continue
            # 정상 로그인
            LOGGED_IN_SID = sid
            info(f"{LOGGED_IN_SID} 님 환영합니다.")
            break
        else:
            # 신규 회원 → 6.2.4
            prompt_password_new(home_path()/STUDENT_FILE, sid, students)
            LOGGED_IN_SID = sid
            info(f"회원가입되었습니다. {LOGGED_IN_SID} 님 환영합니다.")
            break

    # 3) 6.3 — 주 프롬프트
    if LOGGED_IN_SID == "admin":
        admin_main_prompt_loop()
    else:
        main_prompt_loop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()  # 줄바꿈 정리
        warn("사용자에 의해 종료되었습니다.")
        sys.exit(130)