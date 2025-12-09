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


# 전역변수는 복붙해서 각자 .py 파일에 쓰기 
import os
import sys
import re
from pathlib import Path
from datetime import date, datetime
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

RE_DATE = re.compile(
    r"^[1-9][0-9]{3}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"
) 
# 레코드 유효 여부: 'T' 또는 'F' 
RE_VALID_RECORD = re.compile(r"^[TF]$") 


## 영화 데이터 정규식 패턴
# 영화 고유 번호 (0000-9999)
RE_MOVIE_NUMBER = re.compile(r"^[0-9]{4}$")  
# 영화 제목: 특수문자 제외, 앞뒤 공백 금지, 내부 공백 허용(0개 이상)
RE_MOVIE_TITLE = re.compile(
    r"^[A-Za-z0-9\uAC00-\uD7A3](?:[A-Za-z0-9\uAC00-\uD7A3 ]*[A-Za-z0-9\uAC00-\uD7A3])?$"
) 
# 러닝타임: 1~3자리 숫자 
RE_RUNNING_TIME = re.compile(r"^[0-9]{1,3}$")  


## 상영,예매 데이터 정규식 패턴
# 상영 고유 번호 
RE_SCREENING_NUMBER = re.compile(r"^[1-9][0-9]{3}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])([01][0-9]|2[0-3])[0-5][0-9]$")
# 영화 시작 시간 
RE_MOVIE_START_TIME = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
# 좌석 유무,예약 벡터 (0과 1로 이루어진 길이 25의 벡터)
RE_SEAT_VECTOR_FULL = re.compile(r"^\[[01](,[01]){24}\]$")


# 전역 상태 (필수 컨텍스트)
CURRENT_DATE_STR: str | None = None  # 내부 현재 날짜(문자열, YYYY-MM-DD)
LATEST_DATE_STR : str | None = None  # 최종 작업 날짜
LOGGED_IN_SID: str | None = None     # 로그인된 학번(2자리)

 
class Movie:
    movie_id: str
    movie_name: str
    running_time: int
    time_stamp: str

class Schedule:
    schedule_id: str
    movie_id: str
    movie_date: str
    movie_start_time: str
    seats_vector: List[int]
    time_stamp: str

class Student:
    student_id: str #학번
    password: str #비밀번호
    timestamp: str #타임 스탬프

class Booking:
    student_id: str #학번
    schedule_id: str #상영 고유 번호
    seats: List[int] #좌석 예약 벡터
    timestamp: str #타임 스탬프
# ---------------------------------------------------------------
# 유틸리티 출력
# ---------------------------------------------------------------
def info(msg: str) -> None:
    print(msg)

def warn(msg: str) -> None:
    print(f"..! 경고: {msg}")

def error(msg: str) -> None:
    print(f"!!! 오류: {msg}")


## 파일 경로/권한 검사
def check_file(data_path: Path) -> None:
    """
    데이터 파일의 경로 유효성, 존재 여부 및 입출력 권한을 검사하고
    필요시 빈 파일을 생성하는 함수.

    매개변수:
        data_path: Path - 데이터 파일 이름 또는 경로

    반환값:
        없음. 오류 상황에서는 메시지 출력 후 프로그램을 종료(sys.exit).
    """

    # 1. OS가 제공하는 홈 디렉터리 경로 확인
    # try:
    #     home_dir = Path(os.path.expanduser("~")).resolve()  # 홈 경로 반환
    #     print(home_dir)
    # except Exception as e:
    #     error(f"홈 경로를 파악할 수 없습니다! 프로그램을 종료합니다.")
    #     sys.exit(1)
    home_dir = Path(os.getcwd())
    # print(home_dir)

    # 항상 '홈 디렉터리 바로 아래'에 데이터 파일이 위치한다고 가정
    # (data_path에 디렉터리 정보가 들어 있어도 파일 이름만 사용)
    target_path = home_dir / data_path.name

    if data_path.name == MOVIE_FILE:
        file_name = "영화"
    elif data_path.name == STUDENT_FILE:
        file_name = "학생"
    elif data_path.name == BOOKING_FILE:
        file_name = "예매"
    elif data_path.name == SCHEDULE_FILE:
        file_name = "상영"
    else:
        file_name = "알 수 없는 파일"

    # print(target_path)

    # 2. 파일 존재 여부 확인 및 없으면 생성
    if not target_path.exists():
        warn(f"홈 경로 {home_dir}에 {file_name} 데이터 파일이 없습니다.")
        try:
            # 상위 디렉터리는 홈 디렉터리이므로 별도 생성 없이 파일만 생성
            target_path.write_text("", encoding="utf-8", newline="\n")
            info(f"... 홈 경로에 빈 {file_name} 데이터 파일을 새로 생성했습니다:\n{target_path}")
        except Exception:
            error(f"홈 경로에 {file_name} 데이터 파일을 생성하지 못했습니다! 프로그램을 종료합니다.")
            sys.exit(1)

    # 3. 입출력(읽기/쓰기) 권한 확인
    # 3-1. 읽기 권한 확인
    try:
        _ = target_path.read_text(encoding="utf-8")
    except Exception:
        error(f"{file_name} 데이터 파일\n{target_path} 에 대한 입출력 권한이 없습니다! 프로그램을 종료합니다.")
        sys.exit(1)

    # 3-2. 쓰기 권한 확인 (내용 훼손 방지를 위해 빈 문자열만 추가 시도)
    try:
        with target_path.open("a", encoding="utf-8") as f:
            f.write("")
    except Exception:
        error(f"{file_name} 데이터 파일\n{target_path} 에 대한 입출력 권한이 없습니다! 프로그램을 종료합니다.")
        sys.exit(1)

############################################################
##################### 영화 데이터 파일 #########################
############################################################

def validate_movie_syntax(movie_path: Path) -> Tuple[bool, List[str]]:
    """
    영화 데이터 파일의 형식을 검증한다.

    매개변수:
        movie_path: Path - 영화 데이터 파일 경로

    반환값:
        (is_ok, error_lines)
        - is_ok: 형식 오류가 하나도 없으면 True, 하나 이상 있으면 False
        - error_lines: 형식 오류가 발생한 '원본 문자열' 리스트
    """

    error_lines: List[str] = []

    lines = movie_path.read_text(encoding="utf-8").splitlines()
    
    for line in lines:
        original = line

        # 1. 구분자('/') 개수 확인 (정확히 4개 → 5필드)
        if original.count("/") != 4:
            error_lines.append(original)
            continue

        # 2. 앞뒤 공백 금지 (전체 레코드 기준)
        if original != original.strip():
            error_lines.append(original)
            continue

        # 3. 필드 분리
        movie_id_str, movie_name_str, running_time_str, valid_flag_str, timestamp_str = original.split("/")

        # 각 필드별로도 앞뒤 공백이 없어야 함
        if any(f != f.strip() for f in [movie_id_str, movie_name_str, running_time_str, valid_flag_str, timestamp_str]):
            error_lines.append(original)
            continue

        # 4. 정규표현식에 따른 문법 형식 확인
        if not RE_MOVIE_NUMBER.fullmatch(movie_id_str):
            error_lines.append(original)
            continue

        if not RE_MOVIE_TITLE.fullmatch(movie_name_str):
            error_lines.append(original)
            continue

        if not RE_RUNNING_TIME.fullmatch(running_time_str):
            error_lines.append(original)
            continue

        if not RE_DATE.fullmatch(timestamp_str):
            error_lines.append(original)
            continue

        if not RE_VALID_RECORD.fullmatch(valid_flag_str):
            error_lines.append(original)
            continue

        # 5. 의미 규칙 확인
        # 5-1. 러닝 타임: 1~240 사이의 정수
        try:
            running_time_val = int(running_time_str)
        except ValueError:
            error_lines.append(original)
            continue

        if not (1 <= running_time_val <= 240):
            error_lines.append(original)
            continue

        # 5-2. 타임 스탬프(날짜) 의미 검증
        yyyy = int(timestamp_str[0:4])
        mm = int(timestamp_str[5:7])
        dd = int(timestamp_str[8:10])

        # 그레고리력 시행(1582-10-15) 이후만 허용 → 정확하게 1582-10-15부터 허용
        if (yyyy < 1582) or (yyyy == 1582 and (mm < 10 or (mm == 10 and dd < 15))):
            error_lines.append(original)
            continue

        try:
            date(yyyy, mm, dd)
        except ValueError:
            # 존재하지 않는 날짜
            error_lines.append(original)
            continue

    is_ok = len(error_lines) == 0
    return is_ok, error_lines


def parse_movie_data(movie_path: Path) -> List[Movie]:
    """
    (형식 검증이 완료된) 영화 데이터 파일을 읽어 Movie 객체 리스트로 변환한다.

    매개변수:
        movie_path: Path - 영화 데이터 파일 경로

    반환값:
        List[Movie] - 레코드 유효 여부가 'T'인 영화 객체 리스트
    """

    movies: List[Movie] = []
    lines = movie_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        if line.strip() == "":
            # 형식 검증을 통과했다면 등장하지 않겠지만, 방어적으로 무시
            continue

        parts = line.split("/")
        if len(parts) != 5:
            # 형식 검증이 끝난 상태라면 등장하지 않지만, 방어적으로 무시
            continue

        movie_id_str, movie_name_str, running_time_str, valid_flag_str, timestamp_str = parts

        # 레코드 유효 여부가 'T'인 레코드만 사용
        if valid_flag_str != "T":
            continue

        m = Movie()
        m.movie_id = movie_id_str
        m.movie_name = movie_name_str
        m.running_time = int(running_time_str)
        m.time_stamp = timestamp_str
        movies.append(m)

    return movies


def validate_movie_id_duplication(movie_path: Path) -> Tuple[bool, List[str]]:
    """
    영화 데이터 파일 내에서 중복된 영화 고유 번호가 존재하는지 검사한다.

    매개변수:
        movie_path: Path - 영화 데이터 파일 경로

    반환값:
        (is_ok, error_lines)
        - is_ok: 규칙 검증 오류(중복 ID)가 하나도 없으면 True, 하나 이상 있으면 False
        - error_lines: 중복된 영화 고유 번호를 가진 '원본 문자열' 리스트
    """

    lines = movie_path.read_text(encoding="utf-8").splitlines()

    # 레코드 유효 여부가 'T'인 레코드만 대상으로 고유번호 등장 횟수 카운트
    id_counts: Dict[str, int] = {}
    records: List[Tuple[str, str]] = []  # (movie_id, original_line)

    for line in lines:
        if line.strip() == "":
            continue

        parts = line.split("/")
        if len(parts) != 5:
            # 형식 검증을 통과했다면 등장하지 않겠지만, 방어적으로 무시
            continue

        movie_id_str, _, _, valid_flag_str, _ = parts

        if valid_flag_str != "T":
            # 유효 여부가 'T'가 아닌 레코드는 규칙 검증 대상에서 제외
            continue

        records.append((movie_id_str, line))
        id_counts[movie_id_str] = id_counts.get(movie_id_str, 0) + 1

    # 등장 횟수가 2 이상인 ID들을 찾는다.
    duplicated_ids = {mid for mid, cnt in id_counts.items() if cnt >= 2}

    if not duplicated_ids:
        return True, []

    # 중복 ID를 가진 레코드(원본 문자열)만 오류 리스트에 담는다.
    error_lines: List[str] = [
        original for mid, original in records if mid in duplicated_ids
    ]

    return False, error_lines



def validate_movie_name_duplication(movie_path: Path) -> Tuple[bool, List[str]]:
    """
    영화 데이터 파일 내에서 중복된 영화 제목이 존재하는지 검사한다.

    매개변수:
        movie_path: Path - 영화 데이터 파일 경로

    반환값:
        (is_ok, error_lines)
        - is_ok: 규칙 검증 오류(중복 제목)가 하나도 없으면 True, 하나 이상 있으면 False
        - error_lines: 중복된 영화 제목을 가진 '원본 문자열' 리스트
    """
    lines = movie_path.read_text(encoding="utf-8").splitlines()

    # 레코드 유효 여부가 'T'인 레코드만 대상으로 제목 등장 횟수 카운트
    name_counts: Dict[str, int] = {}
    records: List[Tuple[str, str]] = []  # (movie_name, original_line)

    for line in lines:
        if line.strip() == "":
            continue

        parts = line.split("/")
        if len(parts) != 5:
            # 형식 검증을 통과했다면 등장하지 않겠지만, 방어적으로 무시
            continue

        _, movie_name_str, _, valid_flag_str, _ = parts

        if valid_flag_str != "T":
            # 유효 여부가 'T'가 아닌 레코드는 규칙 검증 대상에서 제외
            continue

        records.append((movie_name_str, line))
        name_counts[movie_name_str] = name_counts.get(movie_name_str, 0) + 1

    # 등장 횟수가 2 이상인 제목들을 찾는다.
    duplicated_names = {name for name, cnt in name_counts.items() if cnt >= 2}

    if not duplicated_names:
        return True, []

    # 중복 제목을 가진 레코드(원본 문자열)만 오류 리스트에 담는다.
    error_lines: List[str] = [
        original for name, original in records if name in duplicated_names
    ]

    return False, error_lines

############################################################
##################### 상영 데이터 파일 #########################
############################################################

def validate_schedule_syntax(schedule_path: Path) -> Tuple[bool, List[str]]:
    """
    상영 데이터 파일의 형식을 검증한다.

    매개변수:
        schedule_path: Path - 상영 데이터 파일 경로

    반환값:
        (is_ok, error_lines)
        - is_ok: 형식 오류가 하나도 없으면 True, 하나 이상 있으면 False
        - error_lines: 형식 오류가 발생한 '원본 문자열' 리스트
    """

    error_lines: List[str] = []
    lines = schedule_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        original = line

        # 1. 구분자('/') 개수 확인 (정확히 6개 → 7필드)
        if original.count("/") != 6:
            error_lines.append(original)
            continue

        # 2. 앞뒤 공백 금지 (전체 레코드 기준)
        if original != original.strip():
            error_lines.append(original)
            continue

        # 3. 필드 분리
        parts = original.split("/")
        if len(parts) != 7:
            error_lines.append(original)
            continue

        (
            screening_id_str,
            movie_id_str,
            movie_date_str,
            movie_start_time_str,
            seats_vec_str,
            valid_flag_str,
            timestamp_str,
        ) = parts

        # 각 필드별로도 앞뒤 공백이 없어야 함
        if any(
            f != f.strip()
            for f in [
                screening_id_str,
                movie_id_str,
                movie_date_str,
                movie_start_time_str,
                seats_vec_str,
                valid_flag_str,
                timestamp_str,
            ]
        ):
            error_lines.append(original)
            continue

        # 4. 정규표현식에 따른 문법 형식 확인
        if not RE_SCREENING_NUMBER.fullmatch(screening_id_str):
            error_lines.append(original)
            continue

        if not RE_MOVIE_NUMBER.fullmatch(movie_id_str):
            error_lines.append(original)
            continue

        if not RE_DATE.fullmatch(movie_date_str):
            error_lines.append(original)
            continue

        if not RE_MOVIE_START_TIME.fullmatch(movie_start_time_str):
            error_lines.append(original)
            continue

        if not RE_SEAT_VECTOR_FULL.fullmatch(seats_vec_str):
            error_lines.append(original)
            continue

        if not RE_VALID_RECORD.fullmatch(valid_flag_str):
            error_lines.append(original)
            continue

        if not RE_DATE.fullmatch(timestamp_str):
            error_lines.append(original)
            continue

        # 5. 의미 규칙 확인
        # 5-1. 상영 고유 번호 YYYYMMDDHHmm 의미 검증
        try:
            year = int(screening_id_str[0:4])
            month = int(screening_id_str[4:6])
            day = int(screening_id_str[6:8])
            hour = int(screening_id_str[8:10])
            minute = int(screening_id_str[10:12])
        except ValueError:
            error_lines.append(original)
            continue

        # 그레고리력 시행(1582-10-15) 이후만 허용
        if (year < 1582) or (year == 1582 and (month < 10 or (month == 10 and day < 15))):
            error_lines.append(original)
            continue

        # 존재하는 날짜·시간인지 확인 (날짜 + 시각)
        try:
            datetime(year, month, day, hour, minute)
        except ValueError:
            error_lines.append(original)
            continue

        # 5-2. 영화 상영 날짜 의미 검증 + 상영 고유 번호와의 일관성
        yyyy = int(movie_date_str[0:4])
        mm = int(movie_date_str[5:7])
        dd = int(movie_date_str[8:10])

        if (yyyy < 1582) or (yyyy == 1582 and (mm < 10 or (mm == 10 and dd < 15))):
            error_lines.append(original)
            continue

        try:
            date(yyyy, mm, dd)
        except ValueError:
            error_lines.append(original)
            continue

        # 상영 고유 번호의 연·월·일과 동일해야 함
        if not (yyyy == year and mm == month and dd == day):
            error_lines.append(original)
            continue

        # 5-3. 영화 시작 시간 의미 검증 + 상영 고유 번호와의 일관성
        try:
            sh = int(movie_start_time_str[0:2])
            sm = int(movie_start_time_str[3:5])
        except ValueError:
            error_lines.append(original)
            continue

        if not (0 <= sh <= 23 and 0 <= sm <= 59):
            error_lines.append(original)
            continue

        # 상영 고유 번호의 시각과 동일해야 함
        if not (sh == hour and sm == minute):
            error_lines.append(original)
            continue

        # 5-4. 타임 스탬프 의미 검증
        ty = int(timestamp_str[0:4])
        tm = int(timestamp_str[5:7])
        td = int(timestamp_str[8:10])

        if (ty < 1582) or (ty == 1582 and (tm < 10 or (tm == 10 and td < 15))):
            error_lines.append(original)
            continue

        try:
            date(ty, tm, td)
        except ValueError:
            error_lines.append(original)
            continue

    is_ok = len(error_lines) == 0
    return is_ok, error_lines


def parse_schedule_data(schedule_path: Path) -> List[Schedule]:
    """
    (형식 검증이 완료된) 상영 데이터 파일을 읽어 Schedule 객체 리스트로 변환한다.

    매개변수:
        schedule_path: Path - 상영 데이터 파일 경로

    반환값:
        List[Schedule] - 레코드 유효 여부가 'T'인 상영 객체 리스트
    """

    schedules: List[Schedule] = []
    lines = schedule_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        if line.strip() == "":
            # 형식 검증을 통과했다면 등장하지 않겠지만, 방어적으로 무시
            continue

        parts = line.split("/")
        if len(parts) != 7:
            # 형식 검증이 끝난 상태라면 등장하지 않지만, 방어적으로 무시
            continue

        (
            schedule_id_str,
            movie_id_str,
            movie_date_str,
            movie_start_time_str,
            seats_vec_str,
            valid_flag_str,
            timestamp_str,
        ) = parts

        # 레코드 유효 여부가 'T'인 레코드만 사용
        if valid_flag_str != "T":
            continue

        # 좌석 벡터 문자열을 List[int]로 변환
        body = seats_vec_str.strip()[1:-1]  # 양쪽 대괄호 제거
        items = body.split(",")
        if len(items) != 25:
            # 형식 검증이 끝난 상태라면 등장하지 않지만, 방어적으로 무시
            continue

        try:
            seats_vector = [int(x) for x in items]
        except ValueError:
            continue

        if any(n not in (0, 1) for n in seats_vector):
            continue

        s = Schedule()
        s.schedule_id = schedule_id_str
        s.movie_id = movie_id_str
        s.movie_date = movie_date_str
        s.movie_start_time = movie_start_time_str
        s.seats_vector = seats_vector
        s.time_stamp = timestamp_str

        schedules.append(s)

    return schedules


def validate_schedule_id_duplication(schedule_path: Path) -> bool:
    """
    상영 데이터 파일 내에서 중복된 상영 고유 번호가 존재하는지 검사한다.

    매개변수:
        schedule_path: Path - 상영 데이터 파일 경로

    반환값:
        (is_ok)
        - is_ok: 규칙 검증 오류(중복 상영 ID)가 하나도 없으면 True, 하나 이상 있으면 False
    """

    lines = schedule_path.read_text(encoding="utf-8").splitlines()

    id_counts: Dict[str, int] = {}
    records: List[Tuple[str, str]] = []  # (schedule_id, original_line)

    for line in lines:
        if line.strip() == "":
            continue

        parts = line.split("/")
        if len(parts) != 7:
            # 형식 검증을 통과했다면 등장하지 않겠지만, 방어적으로 무시
            continue

        schedule_id_str, _, _, _, _, valid_flag_str, _ = parts

        if valid_flag_str != "T":
            # 유효 여부가 'T'가 아닌 레코드는 규칙 검증 대상에서 제외
            continue

        records.append((schedule_id_str, line))
        id_counts[schedule_id_str] = id_counts.get(schedule_id_str, 0) + 1

    # 등장 횟수가 2 이상인 상영 ID들을 찾는다.
    duplicated_ids = {sid for sid, cnt in id_counts.items() if cnt >= 2}

    if not duplicated_ids:
        return True

    return False

def check_sorted_schedule_id(schedules: List[Schedule]) -> bool:
    """
    상영 객체 리스트가 상영 고유 번호(schedule_id) 기준으로
    엄격한 오름차순(이전 값 < 현재 값)으로 정렬되어 있는지 검사한다.

    매개변수:
        schedules: List[Schedule] - 상영 객체 리스트

    반환값:
        True  - 모든 schedule_id가 오름차순을 만족하는 경우
        False - 하나라도 이전 schedule_id보다 작거나 같은 경우가 있는 경우
    """
    if not schedules:
        return True

    try:
        prev = int(schedules[0].schedule_id)
    except ValueError:
        # 형식 검증을 통과했다면 발생하지 않겠지만, 방어적으로 False 처리
        return False

    for sch in schedules[1:]:
        try:
            curr = int(sch.schedule_id)
        except ValueError:
            return False

        if curr <= prev:  # 이전 값보다 작거나 같으면 정렬 위반
            return False

        prev = curr

    return True

def check_movie_id_reference(schedules: List[Schedule], movies: List[Movie]) -> bool:
    """
    상영 객체의 영화 고유 번호가 영화 객체 리스트에 존재하는지 검사한다.

    매개변수:
        schedules: List[Schedule] - 상영 객체 리스트
        movies: List[Movie]       - 영화 객체 리스트

    반환값:
        True  - 모든 Schedule.movie_id 가 movies 에 존재하는 경우
        False - 하나라도 존재하지 않는 movie_id 가 있는 경우
    """
    # 1. 영화 목록에서 movie_id 집합 생성 (빠른 포함 여부 검사용)
    movie_ids = {m.movie_id for m in movies}

    # 2. 상영 목록을 순회하며 참조 무결성 검사
    for sch in schedules:
        if sch.movie_id not in movie_ids:
            return False

    return True


def check_daily_schedule_limit(schedules: List[Schedule]) -> bool:
    """
    같은 날짜를 가진 상영 객체가 10개 이상인지 검사한다.

    매개변수:
        schedules: List[Schedule] - 상영 객체 리스트

    반환값:
        True  - 모든 날짜의 상영 개수가 10개 미만인 경우
        False - 어떤 날짜의 상영 개수가 10개 이상인 경우
    """
    date_count_dict: Dict[str, int] = {}

    for sch in schedules:
        d = sch.movie_date
        # 날짜별 상영 개수 누적
        date_count_dict[d] = date_count_dict.get(d, 0) + 1
        if date_count_dict[d] >= 10:
            return False

    return True


def check_schedule_time_conflict(schedules: List[Schedule], movies: List[Movie]) -> bool:
    """
    동일한 날짜에 상영되는 영화들 간에 상영 시간이 서로 겹치는지 검사한다.

    매개변수:
        schedules: List[Schedule] - 상영 객체 리스트
        movies: List[Movie]       - 영화 객체 리스트

    반환값:
        True  - 동일한 날짜 내에서 모든 상영 시간이 서로 겹치지 않는 경우
        False - 동일한 날짜 내에서 상영 시간이 겹치는 일정이 하나라도 존재하는 경우
    """
    # 1. 영화 고유 번호 -> 러닝 타임(분) 매핑
    movie_time_dict: Dict[str, int] = {m.movie_id: m.running_time for m in movies}

    # 2. 날짜별 상영 목록 그룹화
    schedules_by_date: Dict[str, List[Schedule]] = {}
    for sch in schedules:
        d = sch.movie_date
        schedules_by_date.setdefault(d, []).append(sch)

    # 3. 날짜별로 시간 충돌 검사
    for d, sch_list in schedules_by_date.items():
        if len(sch_list) <= 1:
            continue

        # 영화 시작 시간 기준 오름차순 정렬
        sch_list_sorted = sorted(sch_list, key=lambda s: s.movie_start_time)

        # 각 상영에 대해 (시작 시각 분, 종료 시각 분) 계산
        intervals: List[tuple[int, int]] = []
        for sch in sch_list_sorted:
            # 시작 시각 "HH:MM" → 분 단위
            try:
                sh = int(sch.movie_start_time[0:2])
                sm = int(sch.movie_start_time[3:5])
            except ValueError:
                # 형식 검증이 끝난 상태라면 발생하지 않겠지만, 방어적으로 False 처리
                return False

            start_min = sh * 60 + sm

            # 영화 러닝 타임 조회
            rt = movie_time_dict.get(sch.movie_id)
            if rt is None:
                # 참조 무결성 검증에서 걸러졌어야 하지만, 방어적으로 False 처리
                return False

            end_min = start_min + rt
            intervals.append((start_min, end_min))

        # 인접 상영 간 시간 충돌 검사
        for i in range(len(intervals) - 1):
            _, end_curr = intervals[i]
            start_next, _ = intervals[i + 1]
            if end_curr >= start_next:
                return False

    return True


def check_schedule_end_time_before_midnight(schedules: List[Schedule], movies: List[Movie]) -> bool:
    """
    모든 상영 레코드에 대해 영화 종료 시간이 24:00(자정)을 초과하지 않는지 검사한다.

    매개변수:
        schedules: List[Schedule] - 상영 객체 리스트
        movies: List[Movie]       - 영화 객체 리스트

    반환값:
        True  - 모든 영화의 종료 시간이 24:00 이전(또는 정확히 24:00)인 경우
        False - 어떤 영화의 종료 시간이 24:00 이후인 경우
    """
    # 영화 고유 번호 -> 러닝 타임(분) 매핑
    movie_time_dict: Dict[str, int] = {m.movie_id: m.running_time for m in movies}

    for sch in schedules:
        # 영화 러닝 타임 조회
        rt = movie_time_dict.get(sch.movie_id)
        if rt is None:
            # 참조 무결성 검증에서 걸러졌어야 하지만, 방어적으로 False 처리
            return False

        # 시작 시각 "HH:MM" → 분 단위
        try:
            sh = int(sch.movie_start_time[0:2])
            sm = int(sch.movie_start_time[3:5])
        except ValueError:
            return False

        start_min = sh * 60 + sm
        end_min = start_min + rt

        # 24:00(= 1440분)을 초과하면 규칙 위반
        if end_min >= 1440:
            return False

    return True

############################################################
##################### 학생 데이터 파일 #########################
############################################################


def validate_student_syntax(student_path: Path) -> Tuple[bool, List[str]]:
    """
    학생 데이터 파일을 열어 각 레코드를 확인하고, 형식이 올바른지 검사
    1. 구분자(/) 개수 확인
    2. 불필요한 앞뒤 공백 확인
    3. 필드 분리
    4. 문법 형식 확인 (haeun.py의 정규식 활용) - 학번, 비밀번호, 타임스탬프
    5. 의미 규칙 확인 - 타임스탬프 (그레고리력)
    
    Returns:
        Tuple[bool, List[str]]: (형식 오류 여부, 오류 레코드 리스트)
    """
    error_records = []
    
    def _validate_timestamp(timestamp: str) -> bool:
        """타임스탬프의 의미 규칙 검증"""
        try:
            # 정수 변환 및 파싱
            parts = timestamp.split('-')
            yyyy = int(parts[0])
            mm = int(parts[1])
            dd = int(parts[2])
            
            # 그레고리력 범위 검사 (1582년 10월 15일 이후)
            if (yyyy < 1582) or (yyyy == 1582 and mm < 10) or (yyyy == 1582 and mm == 10 and dd < 15):
                return False
            
            # 날짜 실존 여부 검사
            date(yyyy, mm, dd)
            return True
        except (ValueError, IndexError):
            return False
    
    try:
        with open(student_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                original_line = line
                
                # 1. 구분자(/) 개수 확인
                if line.count('/') != 2:
                    error_records.append(original_line)
                    continue
                
                # 2. 불필요한 앞뒤 공백 확인
                if line != line.strip():
                    error_records.append(original_line)
                    continue
                
                # 3. 필드 분리
                parts = line.split('/')
                if len(parts) != 3:
                    error_records.append(original_line)
                    continue
                
                student_id, password, timestamp = parts
                
                # 4. 문법 형식 확인 (haeun.py의 정규식 활용)
                if not RE_STUDENT_ID.match(student_id):
                    error_records.append(original_line)
                    continue
                
                if not RE_PASSWORD.match(password):
                    error_records.append(original_line)
                    continue
                
                if not RE_DATE.match(timestamp):
                    error_records.append(original_line)
                    continue
                
                # 5. 의미 규칙 확인 - 타임스탬프 (그레고리력)
                if not _validate_timestamp(timestamp):
                    error_records.append(original_line)
                    continue
    
    except FileNotFoundError:
        result = (False, [])
        #print(result)
        return result

    # 파일을 정상적으로 읽은 경우: error_records 기반 결과 반환
    result = (len(error_records) == 0, error_records)
    #print(result)
    return result


def parse_student_data(student_path: Path) -> List[Student]:
    """
    형식 검증이 완료된 파일을 읽어 Student 객체 리스트로 변환
    """
    students = []
    
    try:
        with open(student_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                parts = line.split('/')
                
                if len(parts) == 3:
                    student_id, password, timestamp = parts
                    
                    # Student 객체 생성 (haeun.py의 클래스 활용)
                    student = Student()
                    student.student_id = student_id
                    student.password = password
                    student.timestamp = timestamp
                    students.append(student)
    
    except FileNotFoundError:
        return []
    
    return students


def validate_student_id_duplication(student_path: Path) -> Tuple[bool, List[str]]:
    """
    학생 데이터 파일 내에서 중복된 학번이 존재하는지 검사
    1. 파일을 한 레코드씩 읽음, 구분자(/)로 분리
    2. 학번별 카운트
    3. 중복된 학번 가진 레코드 추출
    
    Returns:
        Tuple[bool, List[str]]: (중복 없음 여부, 중복 레코드 리스트)
    """
    student_id_count = defaultdict(int)
    records_by_id = defaultdict(list)
    
    try:
        with open(student_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                parts = line.split('/')

                if len(parts) == 3:
                    student_id = parts[0]

                    # 학번별 카운트
                    student_id_count[student_id] += 1
                    records_by_id[student_id].append(line)

    except FileNotFoundError:
        result = (True, [])
        #print(result)
        return result

    # 중복된 학번을 가진 레코드 추출
    duplicate_records = []
    for sid, count in student_id_count.items():
        if count >= 2:
            duplicate_records.extend(records_by_id[sid])
    
    result = (len(duplicate_records) == 0, duplicate_records)
    #print(result)
    return result


############################################################
##################### 예매 데이터 파일 #########################
############################################################

def validate_booking_syntax(booking_path: Path) -> Tuple[bool, List[str]]:
    """
    예매 데이터 파일을 열어 각 레코드를 확인하고, 형식이 올바른지 검사
    1. 구분자(/) 개수 확인
    2. 불필요한 앞뒤 공백 확인
    3. 필드 분리
    4. 문법 형식 확인 (haeun.py의 정규식 활용) - 학번, 상영 고유 번호, 좌석 예약 벡터, 레코드 유효 여부, 타임 스탬프
    5. 의미 규칙 확인 - 타임스탬프 (그레고리력)
    6. 의미 규칙 확인 - 상영 고유 번호 (YYYYMMDDHHmm) + 그레고리력
    
    Returns:
        Tuple[bool, List[str]]: (형식 오류 여부, 오류 레코드 리스트)
    """
    error_records = []
    
    def _validate_timestamp(timestamp: str) -> bool:
        """타임스탬프의 의미 규칙 검증"""
        try:
            # 정수 변환 및 파싱
            parts = timestamp.split('-')
            yyyy = int(parts[0])
            mm = int(parts[1])
            dd = int(parts[2])
            
            # 그레고리력 범위 검사 (1582년 10월 15일 이후)
            if (yyyy < 1582) or (yyyy == 1582 and mm < 10) or (yyyy == 1582 and mm == 10 and dd < 15):
                return False
            
            # 날짜 실존 여부 검사
            date(yyyy, mm, dd)
            return True
        except (ValueError, IndexError):
            return False
    
    def _validate_schedule_id(schedule_id: str) -> bool:
        """상영 고유 번호의 의미 규칙 검증"""
        try:
            # 정수 변환 및 파싱
            yyyy = int(schedule_id[0:4])
            mm = int(schedule_id[4:6])
            dd = int(schedule_id[6:8])
            hh = int(schedule_id[8:10])
            minutes = int(schedule_id[10:12])
            
            # 그레고리력 범위 검사
            if (yyyy < 1582) or (yyyy == 1582 and mm < 10) or (yyyy == 1582 and mm == 10 and dd < 15):
                return False
            
            # 날짜 및 시간 실존 여부 검사
            datetime(yyyy, mm, dd, hh, minutes)
            return True
        except (ValueError, IndexError):
            return False
    
    try:
        with open(booking_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                original_line = line
                
                # 1. 구분자(/) 개수 확인
                if line.count('/') != 4:
                    error_records.append(original_line)
                    continue
                
                # 2. 불필요한 앞뒤 공백 확인
                if line != line.strip():
                    error_records.append(original_line)
                    continue
                
                # 3. 필드 분리
                parts = line.split('/')
                if len(parts) != 5:
                    error_records.append(original_line)
                    continue
                
                student_id, schedule_id, seats_vector, record_valid, timestamp = parts
                
                # 4. 문법 형식 확인 (haeun.py의 정규식 활용)
                if not RE_STUDENT_ID.match(student_id):
                    error_records.append(original_line)
                    continue
                
                if not RE_SCREENING_NUMBER.match(schedule_id):
                    error_records.append(original_line)
                    continue
                
                if not RE_SEAT_VECTOR_FULL.match(seats_vector):
                    error_records.append(original_line)
                    continue
                
                if not RE_VALID_RECORD.match(record_valid):
                    error_records.append(original_line)
                    continue
                
                if not RE_DATE.match(timestamp):
                    error_records.append(original_line)
                    continue
                
                # 5. 의미 규칙 확인
                # A. 타임스탬프 검증
                if not _validate_timestamp(timestamp):
                    error_records.append(original_line)
                    continue
                
                # B. 상영 고유 번호 검증
                if not _validate_schedule_id(schedule_id):
                    error_records.append(original_line)
                    continue

    except FileNotFoundError:
        result = (False, [])
        #print(result)
        return result

    result = (len(error_records) == 0, error_records)
    
    #print(result)
    return result


def parse_booking_data(booking_path: Path) -> List[Booking]:
    """
    형식 검증이 완료된 파일을 읽어 Booking 객체 리스트로 변환
    레코드 유효 여부가 T인 레코드만 추출
    """
    bookings = []
    
    try:
        with open(booking_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                parts = line.split('/')
                
                if len(parts) == 5:
                    student_id, schedule_id, seats_vector, record_valid, timestamp = parts
                    
                    # 유효한 레코드만 처리
                    if record_valid == 'T':
                        # 좌석 벡터 파싱
                        seats = ast.literal_eval(seats_vector)
                        
                        # Booking 객체 생성 (haeun.py의 클래스 활용)
                        booking = Booking()
                        booking.student_id = student_id
                        booking.schedule_id = schedule_id
                        booking.seats = seats
                        booking.timestamp = timestamp
                        bookings.append(booking)
    
    except FileNotFoundError:
        return []
    
    return bookings


def check_duplicate_seats(bookings: List[Booking]) -> bool:
    """
    예매 데이터에서 같은 상영 고유 번호 + 같은 좌석이 두 번 이상 예매된 경우를 탐지합니다.
    결과는 함수 내부에서 출력합니다.
    """
    """
    예매 데이터에서 같은 상영 고유 번호 + 같은 좌석이 두 번 이상 예매된 경우를 탐지합니다.
    
    Returns:
        bool: True(중복 없음), False(중복 존재)
    """
    # 상영 고유 번호별 좌석 누적 딕셔너리
    seat_accumulator = defaultdict(lambda: [0] * 25)
    
    for booking in bookings:
        schedule_id = booking.schedule_id
        # 좌석 벡터를 누적 합산
        for i in range(25):
            seat_accumulator[schedule_id][i] += booking.seats[i]
    
    # 누적 합산 결과 검사
    for schedule_id, accumulated_seats in seat_accumulator.items():
        for seat_count in accumulated_seats:
            if seat_count >= 2:
                result = False
                #print(result)
                return result

    # 여기까지 왔으면 중복 없음
    result = True
    #print(result)
    return result


def check_seat_consistency(bookings: List[Booking], schedules: List[Schedule]) -> bool:
    """
    예매 데이터의 좌석 합이 상영 데이터의 좌석 상태와 일치하는지 검증합니다.
    결과는 함수 내부에서 출력합니다.
    """
    """
    예매 데이터의 좌석 합이 상영 데이터의 좌석 상태와 일치하는지 검증합니다.
    
    Returns:
        bool: True(일치), False(불일치)
    """
    # 상영 데이터에서 기준 딕셔너리 생성
    schedule_dict = {}
    for schedule in schedules:
        schedule_dict[schedule.schedule_id] = schedule.seats_vector
    
    # 예매 데이터에서 좌석 합산
    calculated_seats = defaultdict(lambda: [0] * 25)
    for booking in bookings:
        schedule_id = booking.schedule_id
        for i in range(25):
            calculated_seats[schedule_id][i] += booking.seats[i]
    
    # 일치 여부 확인
    for schedule_id in schedule_dict.keys():
        expected = schedule_dict[schedule_id]
        actual = calculated_seats.get(schedule_id, [0] * 25)

        if expected != actual:
            result = False
            #print(result)
            return result

    # 여기까지 왔으면 모든 상영의 좌석 상태가 일치
    result = True
    #print(result)
    return result


def check_schedule_id_reference(bookings: List[Booking], schedules: List[Schedule]) -> bool:
    """
    예매 데이터의 상영 고유 번호가 상영 데이터에 실제로 존재하는지 검증합니다.
    결과는 함수 내부에서 출력합니다.
    """
    """
    예매 데이터의 상영 고유 번호가 상영 데이터에 실제로 존재하는지 검증합니다.
    
    Returns:
        bool: True(모두 존재), False(존재하지 않는 번호 있음)
    """
    # 상영 고유 번호 Set 생성
    valid_schedule_ids = set()
    for schedule in schedules:
        valid_schedule_ids.add(schedule.schedule_id)
    
    # 예매 데이터의 상영 고유 번호 확인
    for booking in bookings:
        if booking.schedule_id not in valid_schedule_ids:
            result = False
            #print(result)
            return result

    # 여기까지 왔으면 모든 예매 상영 번호가 상영 데이터에 존재
    result = True
    #print(result)
    return result


def check_student_id_reference(bookings: List[Booking], students: List[Student]) -> bool:
    """
    예매 데이터의 학번이 학생 데이터에 실제로 존재하는지 검증
    1. 학번 set 생성
    2. 예매 데이터의 학번이 미리 생성한 학번 set에 있는지 확인
    
    Returns:
        bool: True(모두 존재), False(존재하지 않는 학번 있음)
    """
    # 학번 Set 생성
    valid_student_ids = set()
    for student in students:
        valid_student_ids.add(student.student_id)
    
    # 예매 데이터의 학번 확인
    for booking in bookings:
        if booking.student_id not in valid_student_ids:
            result = False
            #print(result)
            return result

    # 모든 예매 학번이 학생 데이터에 존재
    result = True
    #print(result)
    return result


def remove_zero_seat_bookings(booking_path: Path) -> None:
    """
    좌석을 하나도 예매하지 않은(좌석 예약 벡터의 모든 숫자가 0인) 무의미한 예매 레코드의 유효 여부를 T에서 F로 수정
    1. 모든 레코드 읽어서 좌석 벡터 파싱
    2. 모든 좌석이 0 && 레코드 유효 여부가 "T"인 경우
    3. 레코드 유효 여부 "F"로 수정
    4. 타임 스탬프 - CURRENT_DATE_STR로 변경
    """
    try:
        with open(booking_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 수정된 라인 저장
        modified_lines = []
        modified = False  # 수정 여부 추적
        
        for i, line in enumerate(lines):
            line = line.rstrip('\n')
            parts = line.split('/')
            if len(parts) == 5:
                student_id, schedule_id, seats_vector, record_valid, timestamp = parts
                
                # 좌석 벡터 파싱
                seats = ast.literal_eval(seats_vector)
                
                # 모든 좌석이 0이고 레코드가 유효한 경우
                if all(seat == 0 for seat in seats) and record_valid == 'T':
                    # 유효 여부를 F로 변경, 타임스탬프를 현재 날짜로 변경 (CURRENT_DATE_STR 없으면 기본값)
                    fallback_date = CURRENT_DATE_STR or "1582-10-15"
                    modified_line = f"{student_id}/{schedule_id}/{seats_vector}/F/{fallback_date}"
                    if i < len(lines) - 1:
                        modified_line += '\n'
                    modified = True  # 수정 발생
                else:
                    modified_line = line
                    if i < len(lines) - 1:
                        modified_line += '\n'
            else:
                modified_line = line
                if i < len(lines) - 1:
                    modified_line += '\n'
            
            modified_lines.append(modified_line)
        
        # 파일 쓰기
        with open(booking_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
        
        # 수정이 발생했을 때만 경고 메시지 출력
        if modified:
            warn("예매 데이터 파일에 무의미한 예매 레코드가 존재합니다. 해당 예매 레코드를 삭제합니다.")
    
    except FileNotFoundError:
        pass





def verify_integrity():
    
    is_ok, error_lines = validate_movie_syntax(Path(MOVIE_FILE))
    if not is_ok:
        error(f"영화 데이터 파일\n{MOVIE_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    movies = parse_movie_data(Path(MOVIE_FILE))

    is_ok, error_lines = validate_movie_id_duplication(Path(MOVIE_FILE))
    if not is_ok:
        error(f"영화 데이터 파일\n{MOVIE_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    is_ok, error_lines = validate_movie_name_duplication(Path(MOVIE_FILE))
    if not is_ok:
        error(f"영화 데이터 파일\n{MOVIE_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    is_ok, error_lines = validate_schedule_syntax(Path(SCHEDULE_FILE))
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    schedules = parse_schedule_data(Path(SCHEDULE_FILE))

    is_ok = validate_schedule_id_duplication(Path(SCHEDULE_FILE))
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    is_ok = check_sorted_schedule_id(schedules) 
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    
    is_ok = check_movie_id_reference(schedules, movies)
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    is_ok = check_daily_schedule_limit(schedules)
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    is_ok = check_schedule_time_conflict(schedules, movies)
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    is_ok = check_schedule_end_time_before_midnight(schedules, movies)
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    
    is_ok, error_lines = validate_student_syntax(Path(STUDENT_FILE))
    if not is_ok:
        error(f"학생 데이터 파일\n{STUDENT_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    students = parse_student_data(Path(STUDENT_FILE))

    is_ok, error_lines = validate_student_id_duplication(Path(STUDENT_FILE))
    if not is_ok:
        error(f"학생 데이터 파일\n{STUDENT_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    is_ok, error_lines = validate_booking_syntax(Path(BOOKING_FILE))
    if not is_ok:
        error(f"예매 데이터 파일\n{BOOKING_FILE}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
        sys.exit(1)
    
    bookings = parse_booking_data(Path(BOOKING_FILE))

    is_ok = check_duplicate_seats(bookings)
    if not is_ok:
        error(f"데이터 파일\n{BOOKING_FILE}가 올바르지 않습니다!\n 의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    is_ok = check_seat_consistency(bookings, schedules)
    if not is_ok:
        error(f"데이터 파일\n{BOOKING_FILE}가 올바르지 않습니다!\n 의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)                 

    is_ok = check_schedule_id_reference(bookings, schedules)
    if not is_ok:
        error(f"데이터 파일\n{BOOKING_FILE}가 올바르지 않습니다!\n 의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    is_ok = check_student_id_reference(bookings, students)      
    if not is_ok:
        error(f"데이터 파일\n{BOOKING_FILE}가 올바르지 않습니다!\n 의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    remove_zero_seat_bookings(Path(BOOKING_FILE))
        

  

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
    #print("최종 작업 날짜:", LATEST_DATE_STR)
    while True:
        s = input(f"현재 날짜를 입력하세요 (YYYY-MM-DD) (최종 작업 날짜: {LATEST_DATE_STR}): ")
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
                    movie_map[parts[0]] = [parts[1], parts[2]]

    movies: list[dict] = []
    for line in scd_lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) != 7:
            continue
        if parts[-2] != "T":
            continue
        
        mov_id = parts[1]
        if mov_id in movie_map:
            title = movie_map[mov_id][0]
            scd_id = parts[0]
            date_str = parts[2]
            startTime = parts[3]
            runtime = int(movie_map[mov_id][1])
            end_hour = (int(startTime[0:2]) + (int(startTime[3:5]) + runtime) // 60) % 24
            end_minute = (int(startTime[3:5]) + runtime) % 60
            endTime = f"{end_hour:02d}:{end_minute:02d}"
            time_str = f"{startTime}-{endTime}"
            
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
            for i, m in enumerate(movies, start=1):
                print(f"{i}) {m['date']} {m['time']} | {m['title']}")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            for i, m in enumerate(movies, start=1):
                print(f"{i}) {m['date']} {m['time']} | {m['title']}")
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
            parts[-1] = CURRENT_DATE_STR
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
                    movie_map[parts[0]] = [parts[1], parts[2]]

    lines = schedule_path.read_text(encoding="utf-8").splitlines()
    details: dict[str, dict] = {}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if parts[-2] != "T":
            continue
        if len(parts) == 7:
            schedule_id = parts[0].strip()
            movie_id = parts[1].strip()
            title = movie_map[movie_id][0]
            date_str = parts[2].strip()
            
            startTime = parts[3]
            runtime = int(movie_map[movie_id][1])
            end_hour = (int(startTime[0:2]) + (int(startTime[3:5]) + runtime) // 60) % 24
            end_minute = (int(startTime[3:5]) + runtime) % 60
            endTime = f"{end_hour:02d}:{end_minute:02d}"
            time_str = f"{startTime}-{endTime}"
            
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
        if len(parts) == 5 and parts[0].strip() == LOGGED_IN_SID and parts[3].strip() == "T":
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
        return
    else:
        user_bookings.sort(key=lambda b: (b['date'], b['time']))
        for i, booking in enumerate(user_bookings, 1):
            seat_list_str = " ".join(booking["seats"])
            print(f"{i}) {booking['date']} {booking['time']} | {booking['title']} | {seat_list_str}")
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
                    movie_map[parts[0]] = [parts[1], parts[2]]

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
                    startTime = pm["time"]
                    runtime = int(movie_map[pm["movie_id"]][1])
                    end_hour = (int(startTime[0:2]) + (int(startTime[3:5]) + runtime) // 60) % 24
                    end_minute = (int(startTime[3:5]) + runtime) % 60
                    endTime = f"{end_hour:02d}:{end_minute:02d}"
                    time_str = f"{startTime}-{endTime}"     
                    bookings.append({
                        "scd_id": scd_id.strip(),
                        "seats": ast.literal_eval(seat_vec.strip()),
                        "title": movie_map[pm["movie_id"]][0],
                        "date": pm["date"],
                        "time": time_str,
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
        print("예매를 취소할 내역을 선택해주세요. (번호로 입력)")
        s = input()
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
    print(f"{selected_booking['date']} {selected_booking['time']} | {selected_booking['title']}의 예매를 취소하겠습니까? (Y/N)")
    n = input()
    
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
                    movie_map[parts[0]] = [parts[1], parts[2]]
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
            startTime = parts[3]
            runtime = int(movie_map[parts[1].strip()][1])
            end_hour = (int(startTime[0:2]) + (int(startTime[3:5]) + runtime) // 60) % 24
            end_minute = (int(startTime[3:5]) + runtime) % 60
            endTime = f"{end_hour:02d}:{end_minute:02d}"
            time_str = f"{startTime}-{endTime}"     
            available_movies.append({
                "date": movie_date,
                "time": time_str.strip(),
                "title": movie_map[parts[1].strip()][0],
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

def admin_menu0() -> None:
    info("프로그램을 종료합니다.")
    sys.exit(0)
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
                    if parts[3] == 'T':
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
        mid = input()

        # 4. "0"인 경우 반환
        if mid == "0":
            return None

        # 2. 형식 검사 (길이 4, 숫자)
        if len(mid) != 4 or not mid.isdigit():
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            print()
            _ = print_modifiable_movie_list()
            continue

        # 3. 수정 가능한 목록에 있는지 검사
        if mid not in modifiable_movie:
            print("수정 가능한 영화 고유번호만 입력 가능합니다. 다시 입력해주세요.")
            print()
            _ = print_modifiable_movie_list()
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
    print(f"<{movie_id} | {current_title} | {current_time}>을 선택하셨습니다. 원하는 동작에 해당하는 번호를 입력하세요.")
    print("1. 영화 제목 수정")
    print("2. 러닝 타임 수정")
    print("0. 뒤로 가기")

    while True:
        # 5. 입력
        func = input()

        # 8. "0" 반환
        if func == "0":
            return None

        # 6. 한 자리 정수 검사
        if len(func) != 1 or not func.isdigit():
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            print(f"<{movie_id} | {current_title} | {current_time}>을 선택하셨습니다. 원하는 동작에 해당하는 번호를 입력하세요.")
            print("1. 영화 제목 수정")
            print("2. 러닝 타임 수정")
            print("0. 뒤로 가기")
            continue

        # 7. 범위 검사 (1~2) -> 0은 위에서 처리했으므로 1, 2만 확인
        if func not in ["1", "2"]:
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            print(f"<{movie_id} | {current_title} | {current_time}>을 선택하셨습니다. 원하는 동작에 해당하는 번호를 입력하세요.")
            print("1. 영화 제목 수정")
            print("2. 러닝 타임 수정")
            print("0. 뒤로 가기")
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
    existing_titles_tuple = tuple(existing_titles)

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
        if title in existing_titles_tuple:
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
        mid = input()

        # 4. "0"인 경우 반환
        if mid == "0":
            return None

        # 2. 형식 검사 (길이 4, 숫자)
        if len(mid) != 4 or not mid.isdigit():
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            _ = print_deletable_movie_list()
            continue

        # 3. 삭제 가능한 목록에 있는지 검사
        if mid not in movie_set:
            print("삭제 가능한 영화 고유 번호만 입력 가능합니다. 다시 입력해주세요.")
            _ = print_deletable_movie_list()
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
# 8.5 상영 시간표 추가
# ---------------------------------------------------------------

def show_available_movie() -> list[str]:
    """
    movie-info.txt에서 'T'인 영화 목록을 출력하고, 유효한 영화 ID 리스트를 반환
    """
    movie_path = home_path() / MOVIE_FILE
    valid_ids = []
    
    print("영화 데이터 파일에 존재하는 영화 목록입니다. 상영 시간표에 추가할 영화 고유 번호를 입력하세요.")
    print("영화 고유 번호 | 영화 제목 | 러닝 타임(분)")
    
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split('/')
                # 형식: id/title/runtime/valid/timestamp
                if len(parts) >= 5 and parts[3] == 'T':
                    print(f"{parts[0]} | {parts[1]} | {parts[2]}")
                    valid_ids.append(parts[0])
    
    print("0. 뒤로 가기")
    return valid_ids

def input_movie_id() -> str | None:
    """
    상영할 영화 ID 입력 및 검증
    """
    while True:
        valid_ids = show_available_movie()
        movie_id = input("").strip()
        
        if movie_id == "0":
            return None
            
        if not re.fullmatch(r"\d{4}", movie_id):
             print("올바르지 않은 입력입니다. 다시 입력해주세요.")
             continue
             
        if movie_id not in valid_ids:
            print("상영 시간표에 추가 가능한 영화 고유 번호만 입력 가능합니다. 다시 입력해주세요.")
            continue
            
        return movie_id

def input_scd_date(movie_id: str) -> str | None:
    """
    상영 날짜 입력 및 검증 (시간 여행, 일일 쿼터 제한)
    """
    # 영화 정보 출력을 위해 영화 제목, 러닝타임 가져오기
    movie_title = ""
    movie_runtime = ""
    movie_path = home_path() / MOVIE_FILE
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 5 and parts[0] == movie_id:
                    movie_title = parts[1]
                    movie_runtime = parts[2]
                    break
    
    print(f"<{movie_id} | {movie_title} | {movie_runtime}>을 선택하셨습니다.")

    while True:
        scd_date = input("위 영화의 영화 상영 날짜를 입력해주세요 (YYYY-MM-DD): ").strip()
        
        if scd_date == "0":
            return None
            
        # 1. 문법 형식 검사
        if not RE_DATE.fullmatch(scd_date):
            print("날짜 형식이 맞지 않습니다. 다시 입력해주세요.")
            print(f"<{movie_id} | {movie_title} | {movie_runtime}>을 선택하셨습니다.")
            continue
            
        # 3. 시간 여행 방지 (현재 날짜보다 이전인지 확인)
        if scd_date < CURRENT_DATE_STR:
            print("내부 현재 날짜 이전의 날짜입니다. 다시 입력해주세요.")
            print(f"<{movie_id} | {movie_title} | {movie_runtime}>을 선택하셨습니다.")
            continue
            
        y, m, d = int(scd_date[0:4]), int(scd_date[5:7]), int(scd_date[8:10])
        try:
            date(y, m, d)
        except ValueError:
            info(f"존재하지 않는 날짜입니다. 다시 입력해주세요.")
            print(f"<{movie_id} | {movie_title} | {movie_runtime}>을 선택하셨습니다.")
            continue
        # return scd_date
    
        # 4. 일일 상영 수 제한 (10개 미만인지 확인)
        cnt = 0
        schedule_path = home_path() / SCHEDULE_FILE
        if schedule_path.exists():
            with open(schedule_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('/')
                    if len(parts) >= 7 and parts[2] == scd_date and parts[5] == 'T':
                        cnt += 1
        
        if cnt >= 10:
            print("일일 영화 상영 수를 초과했습니다. 다시 입력해주세요.")
            continue
            
        return scd_date

# ---------------------------------------------------------------
# 상영 시간표 중복 검사 함수들 (2차 설계서 8.5, 8.6 반영)
# ---------------------------------------------------------------

def chk_overlap_date(scd_id: str, running_time: int, scd_date: str) -> bool:
    """
    [설계서 9. chk_overlap_date]
    영화 날짜를 수정할 때, 변경된 날짜에서 시간 충돌이 발생하는지 검사
    """
    schedule_path = home_path() / SCHEDULE_FILE
    
    # 1. schedule-info.txt에서 scd_id에 해당하는 레코드의 '영화 시작 시간'을 찾음
    scd_time = ""
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 7 and parts[0] == scd_id and parts[5] == 'T':
                    scd_time = parts[3] # 영화 시작 시간
                    break
    
    if not scd_time: return False # 레코드가 없으면 검사 불가 (False 반환)

    # 2. 시간 계산 (분 단위)
    h, m = map(int, scd_time.split(':'))
    newStart = h * 60 + m
    newEnd = newStart + running_time

    # 3. schedule-info.txt에서 조건에 맞는 레코드 필터링 및 중복 검사
    # 조건: 영화 날짜 == scd_date AND 상영 고유 번호 != scd_id AND 유효 여부 == "T"
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) < 7: continue
                
                ex_scd_id = parts[0]
                ex_movie_id = parts[1]
                ex_date = parts[2]
                ex_time = parts[3]
                ex_valid = parts[5]

                # 필터링
                if ex_date == scd_date and ex_scd_id != scd_id and ex_valid == 'T':
                    # A. 영화 고유 번호를 old_movie_id에 저장
                    old_movie_id = ex_movie_id
                    
                    # B. movie-info.txt에서 old_movie_id의 러닝 타임 가져오기
                    old_running_time = 0
                    movie_path = home_path() / MOVIE_FILE
                    if movie_path.exists():
                        with open(movie_path, 'r', encoding='utf-8') as mf:
                            for mline in mf:
                                mparts = mline.strip().split('/')
                                if len(mparts) >= 5 and mparts[0] == old_movie_id and mparts[3] == 'T':
                                    old_running_time = int(mparts[2])
                                    break
                    
                    # C. oldStart, oldEnd 계산
                    eh, em = map(int, ex_time.split(':'))
                    oldStart = eh * 60 + em
                    oldEnd = oldStart + old_running_time
                    
                    # D. 겹침 판별
                    if newStart < oldEnd and newEnd > oldStart:
                        return True # 겹침

    return False # 겹치지 않음

def chk_overlap_time(scd_id: str, running_time: int, scd_time: str) -> bool:
    """
    [설계서 8. chk_overlap_time] - 수정본
    영화 시작 시간을 수정할 때, 변경할 시간(scd_time)을 기준으로 충돌 검사
    
    매개변수:
        scd_id: 수정 대상 상영 고유 번호 (기존 ID)
        running_time: 영화 러닝 타임
        scd_time: 사용자가 입력한 새로운 시작 시간 (HH:MM)
    """
    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE 

    # 1. scd_id에서 날짜 파싱 (YYYYMMDD...) -> YYYY-MM-DD
    # 수정 기능이므로 날짜는 scd_id에 있는 날짜(기존 날짜)를 유지한다고 가정
    # (만약 날짜 수정 기능에서 이 함수를 쓴다면 로직이 달라져야 하나, 
    #  현재 문맥상 '시간 수정' 단계이므로 scd_id의 날짜를 사용)
    yyyy = scd_id[0:4]
    mm = scd_id[4:6]
    dd = scd_id[6:8]
    scd_date = f"{yyyy}-{mm}-{dd}"

    # 2. 입력받은 scd_time으로 새로운 시작/종료 시간 계산
    # (파일에서 읽지 않고, 인자로 받은 scd_time 사용)
    h, m = map(int, scd_time.split(':'))
    newStart = h * 60 + m
    newEnd = newStart + running_time

    # 3. 24:00(1440분) 초과 검사
    # 24:00은 허용 안 함 (1440 이상이면 오류)
    #if newEnd >= 1440: 
    #    print("영화 종료 시간은 24:00 이후일 수 없습니다. 다시 입력해주세요.")
    #    return True

    # 4. schedule-info.txt 필터링 및 중복 검사
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) < 7: continue
                
                ex_scd_id = parts[0]
                ex_movie_id = parts[1]
                ex_date = parts[2]
                ex_time = parts[3]
                ex_valid = parts[5]

                # 조건: 날짜 일치 AND 유효함(T)
                # ★ 핵심: 수정 대상인 자기 자신(scd_id)은 비교에서 제외 ★
                if ex_date == scd_date and ex_scd_id != scd_id and ex_valid == 'T':
                    
                    # A. 비교 대상의 러닝타임 가져오기 (old_movie_id)
                    old_movie_id = ex_movie_id
                    old_running_time = 0
                    
                    if movie_path.exists():
                        with open(movie_path, 'r', encoding='utf-8') as mf:
                            for mline in mf:
                                mparts = mline.strip().split('/')
                                if len(mparts) >= 5 and mparts[0] == old_movie_id and mparts[3] == 'T':
                                    old_running_time = int(mparts[2])
                                    break
                    
                    # B. 비교 대상의 시작/종료 시간 계산
                    eh, em = map(int, ex_time.split(':'))
                    oldStart = eh * 60 + em
                    oldEnd = oldStart + old_running_time
                    
                    # C. 겹침 판별
                    # (Start1 < End2) and (End1 > Start2)
                    if newStart < oldEnd and newEnd > oldStart:
                        return True

    return False
# ---------------------------------------------------------------
# 8.6 상영 시간표 수정
# ---------------------------------------------------------------

def print_modifiable_scd_list() -> set:
    """
    수정 가능한(예매 없음, 미래, 유효함) 스케줄 목록을 출력하고 ID 집합 반환
    """
    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE
    
    modifiable_ids = set()
    
    if not schedule_path.exists():
        return modifiable_ids

    # 영화 정보 로드
    movie_info = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 5 and parts[3] == 'T':
                    movie_info[parts[0]] = {'title': parts[1], 'runtime': parts[2]}

    print("상영 데이터 파일에 존재하는 수정 가능한 상영 시간표 목록입니다. 수정할 상영 고유 번호를 입력하세요.")
    print("상영 고유 번호 | 영화 제목 | 러닝 타임(분) | 영화 날짜 | 영화 시작 시간")

    schedules_to_print = []
    with open(schedule_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('/')
            # 구조: scd_id/movie_id/date/time/vec/valid/ts
            if len(parts) < 7: continue
            
            scd_id, mid, date_str, time_str, vec_str, valid = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            
            # 조건: 유효T, 날짜>=현재, 벡터가 모두 0(예매 없음)
            try:
                seats = ast.literal_eval(vec_str)
                is_empty_seats = all(s == 0 for s in seats)
            except:
                is_empty_seats = False

            if valid == 'T' and date_str >= CURRENT_DATE_STR and is_empty_seats:
                m_data = movie_info.get(mid, {'title': '알수없음', 'runtime': '0'})
                schedules_to_print.append({
                    'id': scd_id,
                    'title': m_data['title'],
                    'runtime': m_data['runtime'],
                    'date': date_str,
                    'time': time_str
                })
                modifiable_ids.add(scd_id)

    # 정렬하여 출력
    schedules_to_print.sort(key=lambda x: x['id'])
    for s in schedules_to_print:
        print(f"{s['id']} | {s['title']} | {s['runtime']} | {s['date']} | {s['time']}")

    print("0. 뒤로 가기")
    return modifiable_ids

def input_modify_scd_id(modifiable_ids: set) -> str | None:
    """
    수정할 상영 고유 번호 입력 및 검증
    """
    while True:
        scd_id = input("").strip()
        
        if scd_id == "0":
            return None
            
        # 문법 형식 검사 (12자리 숫자)
        if not re.fullmatch(r"\d{12}", scd_id):
             print("올바르지 않은 입력입니다. 다시 입력해주세요.")
             continue
             
        # 의미 규칙 검사 (목록에 존재 여부)
        if scd_id not in modifiable_ids:
            print("수정 가능한 상영 고유 번호만 입력 가능합니다. 다시 입력해주세요.")
            continue
            
        return scd_id

def input_modify_scd_func(scd_id: str) -> str | None:
    """
    수정할 항목(날짜/시간) 선택
    """
    # 선택된 스케줄 정보 출력을 위해 파일 읽기
    target_scd = None
    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE
    
    # 영화 정보 로드
    movie_info = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 5:
                    movie_info[parts[0]] = {'title': parts[1], 'runtime': parts[2]}

    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 7 and parts[0] == scd_id:
                    mid = parts[1]
                    m_data = movie_info.get(mid, {'title': '알수없음', 'runtime': '0'})
                    target_scd = {
                        'id': scd_id, 'title': m_data['title'], 'runtime': m_data['runtime'],
                        'date': parts[2], 'time': parts[3]
                    }
                    break
    
    if target_scd:
        print(f"<{target_scd['id']} | {target_scd['title']} | {target_scd['runtime']} | {target_scd['date']} | {target_scd['time']}>을 선택하셨습니다. 수정할 번호를 선택해주세요.")

    print("1. 영화 날짜 수정")
    print("2. 영화 시작 시간 수정")
    print("0. 뒤로 가기")

    while True:
        func = input("").strip()
        
        if func == "0":
            return None
            
        if func not in ["1", "2"]:
            if not re.fullmatch(r"\d", func):
                 print("올바르지 않은 입력입니다. 원하는 동작에 해당하는 번호만 입력하세요.")
            else:
                 print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
            
        return func

def input_modify_scd_date(scd_id: str) -> str | None:
    """
    수정할 영화 날짜 입력 및 검증
    (is_valid_date_string, count_daily_schedules 함수 없이 직접 구현)
    """
    # 러닝타임 가져오기 (chk_overlap_date 호출용)
    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE
    runtime = 0
    
    # 스케줄에서 movie_id 찾기 -> movie_info에서 runtime 찾기
    mid = ""
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 7 and parts[0] == scd_id: # 7개 필드 확인
                    mid = parts[1]
                    break
    if mid and movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 5 and parts[0] == mid:
                    runtime = int(parts[2])
                    break

    while True:
        scd_date = input("수정할 영화 상영 날짜를 입력해주세요 (YYYY-MM-DD): ").strip()
        
        if scd_date == "0":
            return None
            
        # 1. 문법 형식 검사
        if not RE_DATE.fullmatch(scd_date):
            print("날짜 형식이 맞지 않습니다. 다시 입력해주세요.")
            continue
        
        # 2. 날짜 유효성(그레고리력) 검사 (직접 구현)
        y, m, d = int(scd_date[0:4]), int(scd_date[5:7]), int(scd_date[8:10])
        try:
            date(y, m, d)
        except ValueError:
            print("존재하지 않는 날짜입니다. 다시 입력해주세요.")
            continue

        # 3. 시간 여행 방지
        if scd_date < CURRENT_DATE_STR:
             print("내부 현재 날짜 이전의 날짜입니다. 다시 입력해주세요.")
             continue

        # 4. 일일 상영 수 제한 (10개 미만인지 직접 카운트)
        cnt = 0
        if schedule_path.exists():
            with open(schedule_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('/')
                    # 구조: scd_id/movie_id/date/time/vec/valid/ts
                    # 자기 자신은 날짜가 바뀌므로 어차피 카운트에서 제외되거나,
                    # 날짜가 안 바뀌면 자기 포함 10개인지 체크해야 함.
                    # 수정이므로 '바뀔 날짜(scd_date)'에 있는 다른 스케줄 개수 + (만약 날짜 안 바꾸면 나 포함) 확인
                    # 하지만 여기선 '바뀔 날짜'에 이미 있는 유효한(T) 스케줄 개수만 세면 됨.
                    
                    # 주의: 내가 날짜를 안 바꾸면(같은 날짜 입력), 나는 이미 파일에 T로 존재하므로 cnt에 포함됨.
                    # 내가 날짜를 바꾸면, 바뀔 날짜엔 내가 아직 없으므로 cnt에 포함 안 됨.
                    # 기획서 의도상 "해당 날짜의 상영 레코드 수"를 제한하는 것이므로
                    # 수정될 날짜에 이미 있는 스케줄 수를 세되, '자기 자신'은 제외하고 세는 것이 논리적으로 맞음 (수정 후 T로 들어갈 거니까).
                    # 다만 input_scd_date(신규추가) 로직과 동일하게 '파일에 있는 T 개수'를 그대로 세면
                    # 날짜 변경 시: 대상 날짜의 기존 스케줄 수 (내 거 없음) -> 10개면 추가 불가 (OK)
                    # 날짜 미변경 시: 내 거 포함 10개 -> 수정 불가? (내 거 1개 빼고 9개여야 수정 가능)
                    
                    if len(parts) >= 7 and parts[2] == scd_date and parts[5] == 'T':
                         # 수정 기능이므로 자기 자신(scd_id)은 카운트에서 제외해야 정확함
                         if parts[0] != scd_id:
                            cnt += 1
        
        if cnt >= 10:
             print("일일 영화 상영 수를 초과했습니다. 다시 입력해주세요.")
             continue

        # 5. 중복 검사 (chk_overlap_date 사용)
        if chk_overlap_date(scd_id, runtime, scd_date):
             print("상영 시간은 다른 상영 시간표와 중복될 수 없습니다. 다시 입력해주세요.")
             continue

        return scd_date

def input_modify_scd_time(scd_id: str) -> str | None:
    """
    수정할 영화 시작 시간 입력 및 검증
    """
    # 러닝타임 가져오기
    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE
    runtime = 0
    
    mid = ""
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if parts[0] == scd_id:
                    mid = parts[1]
                    break
    if mid and movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if parts[0] == mid:
                    running_time = int(parts[2])
                    break

    while True:
        scd_time = input("수정할 영화 시작 시간을 입력해주세요 (HH:MM): ").strip()
        
        if scd_time == "0":
            return None
            
        if not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", scd_time):
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue
        # ====================================================================================
        # [추가] 24:00 (1440분) 이상 검사
        h, m = map(int, scd_time.split(':'))
        newStart = h * 60 + m
        newEnd = newStart + running_time
        
        if newEnd >= 1440: 
             print("영화 종료 시간은 24:00 이후일 수 없습니다. 다시 입력해주세요.")
             continue # 여기서 루프 재시작 -> 중복 검사로 안 넘어감
        # ====================================================================================

        # 중복 검사 (chk_overlap_time 사용 - 내부에서 24시 초과 검사 하려 했으나, 이를 수정)
        if chk_overlap_time(scd_id, running_time, scd_time):
             print("상영 시간은 다른 상영 시간표와 중복될 수 없습니다. 다시 입력해주세요.")
             continue
             
        return scd_time
    

def modify_scd_date(scd_id: str, scd_date: str) -> None:
    """
    상영 날짜 수정 (Soft Update) - 줄바꿈 오류 수정됨
    """
    lines = []
    schedule_path = home_path() / SCHEDULE_FILE
    
    target_line = ""
    
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            # readlines() 대신 한 줄씩 읽어서 strip() 후 처리하는 것이 안전함
            for line in f:
                if line.strip(): # 빈 줄 제외
                    lines.append(line.strip()) # 개행 문자 제거하고 저장
            
    # 2. 기존 레코드 F 처리 및 타겟 찾기
    # 인덱스가 아니라 리스트를 순회하며 처리
    new_lines = []
    for line in lines:
        parts = line.split('/')
        if parts[0] == scd_id and parts[5] == 'T':
            parts[5] = 'F'
            parts[6] = CURRENT_DATE_STR
            target_line = line
            new_lines.append("/".join(parts)) # 수정된 내용 추가
        else:
            new_lines.append(line) # 기존 내용 그대로 추가
            
    if target_line:
        parts = target_line.split('/')
        mid = parts[1]
        old_time = parts[3]
        
        # 새 ID 생성
        new_scd_id = scd_date.replace("-", "") + old_time.replace(":", "")
        zero_vector = "[" + ",".join(["0"]*25) + "]"
        
        # 새 레코드 추가
        new_record = f"{new_scd_id}/{mid}/{scd_date}/{old_time}/{zero_vector}/T/{CURRENT_DATE_STR}"
        new_lines.append(new_record)
        
        # 정렬
        new_lines.sort(key=lambda x: x.split('/')[0]) 

        # [핵심 수정] 저장 시 개행 문자(\n)를 명시적으로 붙여서 join
        with open(schedule_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines) + "\n") # 마지막 줄에도 개행 추가 권장

def modify_scd_time(scd_id: str, scd_time: str) -> None:
    """
    상영 시간 수정 (Soft Update) - 줄바꿈 오류 수정됨
    """
    lines = []
    schedule_path = home_path() / SCHEDULE_FILE
    
    target_line = ""
    
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
             for line in f:
                if line.strip():
                    lines.append(line.strip())
            
    new_lines = []
    for line in lines:
        parts = line.split('/')
        if parts[0] == scd_id and parts[5] == 'T':
            parts[5] = 'F'
            parts[6] = CURRENT_DATE_STR
            target_line = line
            new_lines.append("/".join(parts))
        else:
            new_lines.append(line)
            
    if target_line:
        parts = target_line.split('/')
        mid = parts[1]
        old_date = parts[2]
        
        # 새 ID 생성
        new_scd_id = old_date.replace("-", "") + scd_time.replace(":", "")
        zero_vector = "[" + ",".join(["0"]*25) + "]"
        
        new_record = f"{new_scd_id}/{mid}/{old_date}/{scd_time}/{zero_vector}/T/{CURRENT_DATE_STR}"
        new_lines.append(new_record)
        
        # 정렬
        new_lines.sort(key=lambda x: x.split('/')[0])

        # [핵심 수정] 저장 시 개행 문자(\n)를 명시적으로 붙여서 join
        with open(schedule_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines) + "\n")

def admin_menu5():
    """
    8.6 상영 시간표 수정 메인 함수
    """
    while True:
        # 1. 수정 가능한 목록 출력 및 ID 입력
        modifiable_ids = print_modifiable_scd_list()
        scd_id = input_modify_scd_id(modifiable_ids)
        
        if scd_id is None:
            return # 종료
            
        while True:
            # 2. 수정 메뉴 선택
            func = input_modify_scd_func(scd_id)
            
            if func is None:
                break # 상위(ID 입력)로 이동
                
            # 3. 날짜 수정
            if func == "1":
                scd_date = input_modify_scd_date(scd_id)
                if scd_date is None:
                    continue # 메뉴 선택으로 돌아감
                
                modify_scd_date(scd_id, scd_date)
                print("수정이 완료되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
                # verify_integrity()
                return # 완료 후 종료

            # 4. 시간 수정
            elif func == "2":
                scd_time = input_modify_scd_time(scd_id)
                if scd_time is None:
                    continue # 메뉴 선택으로 돌아감
                
                modify_scd_time(scd_id, scd_time)
                print("수정이 완료되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
                # verify_integrity()
                return # 완료 후 종료
            



def input_scd_time(movie_id: str, scd_date: str) -> str | None:
    """
    상영 시작 시간 입력 및 검증
    """
    while True:
        scd_time = input("영화 시작 시간을 입력해주세요 (HH:MM): ").strip()
        
        if scd_time == "0":
            return None

        # 1. 문법 형식 검사
        if not re.fullmatch(r"[0-9][0-9]:[0-9][0-9]", scd_time):
            print("올바르지 않은 입력입니다. 다시 입력해주세요.")
            continue

        if not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", scd_time):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        
        running_time = 0
        movie_path = home_path() / MOVIE_FILE
        if movie_path.exists():
            with open(movie_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('/')
                    if len(parts) >= 5 and parts[0] == movie_id and parts[3] == 'T':
                        running_time = int(parts[2])
                        break

        # 2. 24:00 이후 검사 로직 추가 (8.5.3 의미 규칙)
        h, m = map(int, scd_time.split(':'))
        newStart = h * 60 + m
        newEnd = newStart + running_time
        
        if newEnd >= 1440: # 24:00 (1440분) 이후
             print("영화 종료 시간은 24:00 이후일 수 없습니다. 다시 입력해주세요.")
             continue
        if chk_overlap(movie_id, scd_date, scd_time):

            print("상영 시간은 다른 상영 시간표와 중복될 수 없습니다. 다시 입력해주세요.") 
            continue
            
        return scd_time

def add_scd(movie_id: str, scd_date: str, scd_time: str) -> None:
    """
    상영 데이터 파일에 레코드 추가 (오름차순 정렬 유지)
    """
    # 상영 고유 번호 생성 (YYYYMMDDHHmm)
    scd_id = scd_date.replace("-", "") + scd_time.replace(":", "")
    
    # 좌석 유무 벡터 (25개의 0)
    zero_vector = "[" + ",".join(["0"] * 25) + "]"
    
    # 새 레코드 생성
    new_record = f"{scd_id}/{movie_id}/{scd_date}/{scd_time}/{zero_vector}/T/{CURRENT_DATE_STR}"
    
    schedule_path = home_path() / SCHEDULE_FILE
    
    # 1. 기존 파일 내용 읽기
    lines = []
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    lines.append(line.strip())

    # 2. 새 레코드 리스트에 추가
    lines.append(new_record)

    # 3. 상영 고유 번호(첫 번째 필드) 기준으로 오름차순 정렬
    lines.sort(key=lambda x: x.split('/')[0])

    # 4. 파일 덮어쓰기 (정렬된 순서대로 저장)
    with open(schedule_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

        
def chk_overlap(movie_id: str, scd_date: str, scd_time: str) -> bool:
    """
    [설계서 7. chk_overlap]
    상영 시간표 추가(admin_menu4) 시 중복 검사
    """
    movie_path = home_path() / MOVIE_FILE
    schedule_path = home_path() / SCHEDULE_FILE

    # 1. 현재 영화의 러닝타임(running_time) 및 시간 계산
    running_time = 0
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 5 and parts[0] == movie_id and parts[3] == 'T':
                    running_time = int(parts[2])
                    break
    
    h, m = map(int, scd_time.split(':'))
    newStart = h * 60 + m
    newEnd = newStart + running_time

    # (설계서에는 없으나 로직상 필요한 24시 체크, 설계서 7번 항목에는 명시되지 않았지만 
    # admin_menu4의 input_scd_time 처리 과정에 언급됨. 여기서는 순수 중복 체크 로직만 수행)
    
    # 2. schedule-info.txt 필터링
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) < 7: continue
                
                ex_scd_id = parts[0]
                ex_movie_id = parts[1]
                ex_date = parts[2]
                ex_time = parts[3]
                ex_valid = parts[5]

                # 조건: 날짜 일치 AND 유효함
                if ex_date == scd_date and ex_valid == 'T':
                    # A. old_movie_id
                    old_movie_id = ex_movie_id
                    
                    # B. old_running_time
                    old_running_time = 0
                    if movie_path.exists():
                        with open(movie_path, 'r', encoding='utf-8') as mf:
                            for mline in mf:
                                mparts = mline.strip().split('/')
                                if len(mparts) >= 5 and mparts[0] == old_movie_id and mparts[3] == 'T':
                                    old_running_time = int(mparts[2])
                                    break
                    
                    # C. oldStart, oldEnd
                    eh, em = map(int, ex_time.split(':'))
                    oldStart = eh * 60 + em
                    oldEnd = oldStart + old_running_time
                    
                    # D. 겹침 판별
                    if newStart < oldEnd and newEnd > oldStart:
                        return True

    return False

def admin_menu4():
    """
    8.5 상영 시간표 추가 메인 함수
    """
    while True:
        # 1. 영화 선택
        movie_id = input_movie_id()
        if movie_id is None:
            return # 관리자 메인으로
            
        # 2. 날짜 입력 (중첩 루프)
        while True:
            scd_date = input_scd_date(movie_id)
            if scd_date is None:
                break # 영화 선택으로 돌아감
                
            # 3. 시간 입력 (중첩 루프)
            while True:
                scd_time = input_scd_time(movie_id, scd_date)
                if scd_time is None:
                    break # 날짜 입력으로 돌아감
                    
                # 4. 추가 및 종료
                add_scd(movie_id, scd_date, scd_time)
                print("상영 시간표가 추가되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
                
                # 무결성 검사 호출 (빈 함수라도 호출)
                # verify_integrity() 
                return
# ---------------------------------------------------------------
# 8.7 상영 시간표 삭제
# ---------------------------------------------------------------

def print_deletable_scd_list() -> set:
    """
    삭제 가능한(예매 없음, 미래, 유효함) 스케줄 목록을 출력하고 ID 집합 반환
    """
    schedule_path = home_path() / SCHEDULE_FILE
    movie_path = home_path() / MOVIE_FILE
    
    deletable_ids = set()
    
    if not schedule_path.exists():
        return deletable_ids

    # 영화 정보 로드
    movie_info = {}
    if movie_path.exists():
        with open(movie_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('/')
                if len(parts) >= 5 and parts[3] == 'T':
                    movie_info[parts[0]] = {'title': parts[1], 'runtime': parts[2]}

    print("상영 데이터 파일에 존재하는 삭제 가능한 상영 시간표 목록입니다. 삭제할 상영 고유 번호를 입력하세요.")
    print("상영 고유 번호 | 영화 제목 | 러닝 타임(분) | 영화 날짜 | 영화 시작 시간")

    schedules_to_print = []
    with open(schedule_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('/')
            # 구조: scd_id/movie_id/date/time/vec/valid/ts
            if len(parts) < 7: continue
            
            scd_id, mid, date_str, time_str, vec_str, valid = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            
            # 조건: 유효T, 날짜>=현재, 벡터가 모두 0(예매 없음)
            try:
                seats = ast.literal_eval(vec_str)
                is_empty_seats = all(s == 0 for s in seats)
            except:
                is_empty_seats = False

            # 내부 현재 날짜 '후'의 상영 시간표 (설계서 8.7 본문: 내부 현재 날짜 후)
            # 보통 당일 삭제도 막는 것이 안전하므로 > 로 처리하거나, 
            # 4.4 입력 날짜 규칙(>=)과 일관성을 위해 >= 로 처리할 수 있음.
            # 여기서는 설계서 텍스트("내부 현재 날짜 후")를 따라 > 로 구현하되, 
            # 필요시 >= 로 변경 가능. (8.6 수정에서는 >= CURRENT_DATE_STR 로 구현했음)
            # 통일성을 위해 여기서도 >= CURRENT_DATE_STR 로 구현합니다.
            if valid == 'T' and date_str >= CURRENT_DATE_STR and is_empty_seats:
                m_data = movie_info.get(mid, {'title': '알수없음', 'runtime': '0'})
                schedules_to_print.append({
                    'id': scd_id,
                    'title': m_data['title'],
                    'runtime': m_data['runtime'],
                    'date': date_str,
                    'time': time_str
                })
                deletable_ids.add(scd_id)

    # 정렬하여 출력 (상영 고유 번호 기준 오름차순)
    schedules_to_print.sort(key=lambda x: x['id'])
    for s in schedules_to_print:
        print(f"{s['id']} | {s['title']} | {s['runtime']} | {s['date']} | {s['time']}")

    print("0. 뒤로 가기")
    return deletable_ids

def input_delete_scd_id(deletable_ids: set) -> str | None:
    """
    삭제할 상영 고유 번호 입력 및 검증
    """
    while True:
        scd_id = input("").strip()
        
        if scd_id == "0":
            return None
            
        # 문법 형식 검사 (12자리 숫자)
        if not re.fullmatch(r"\d{12}", scd_id):
             print("올바르지 않은 입력입니다. 다시 입력해주세요.")
             continue
             
        # 의미 규칙 검사 (삭제 가능 목록에 존재 여부)
        if scd_id not in deletable_ids:
            print("삭제 가능한 상영 고유 번호만 입력 가능합니다. 다시 입력해주세요.")
            continue
            
        return scd_id

def delete_scd(scd_id: str) -> None:
    """
    상영 레코드 삭제 (유효 여부를 T -> F로 수정 및 타임스탬프 갱신)
    """
    lines = []
    schedule_path = home_path() / SCHEDULE_FILE
    
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            # 안전하게 모든 줄 읽기 (개행 제거)
            for line in f:
                if line.strip():
                    lines.append(line.strip())
    
    new_lines = []
    for line in lines:
        parts = line.strip().split('/')
        # 구조: id(0)/mid(1)/date(2)/time(3)/vec(4)/valid(5)/ts(6)
        if len(parts) >= 7 and parts[0] == scd_id and parts[5] == 'T':
            parts[5] = 'F' # 유효 여부 F
            parts[6] = CURRENT_DATE_STR # 타임스탬프 갱신
            new_lines.append("/".join(parts))
        else:
            new_lines.append(line)

    # 파일 덮어쓰기 (개행 문자 추가하여 join)
    with open(schedule_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_lines) + "\n")

def admin_menu6():
    """
    8.7 상영 시간표 삭제 메인 함수
    """
    while True:
        # 1. 삭제 가능한 목록 출력 (처리 과정 3.A)
        deletable_ids = print_deletable_scd_list()
        
        # 2. 상영 고유 번호 입력 (처리 과정 4.A)
        scd_id = input_delete_scd_id(deletable_ids)
        
        # 2.B "0" 입력 시 종료
        if scd_id is None:
            return

        # 3. 상영 레코드 삭제 (처리 과정 5)
        delete_scd(scd_id)
        print("해당 상영 시간표가 삭제되었습니다. 관리자 주 프롬프트로 돌아갑니다.")
        
        # 4. 데이터 무결성 검사 (처리 과정 6.A)
        # verify_integrity()
        
        # 5. 함수 종료
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
        "0": admin_menu0,
        "1": admin_menu1,
        "2": admin_menu2,
        "3": admin_menu3,
        "4": admin_menu4,
        "5": admin_menu5,
        "6": admin_menu6,
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
            info("올바르지 않은 입력입니다. 다시 입력해주세요.")
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

    check_file(Path(MOVIE_FILE))
    check_file(Path(STUDENT_FILE))
    check_file(Path(BOOKING_FILE))
    check_file(Path(SCHEDULE_FILE))

    verify_integrity()

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

    #print(LATEST_DATE_STR)
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
            if LOGGED_IN_SID == "admin":
                info("관리자 계정으로 로그인했습니다.")
            else:
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
