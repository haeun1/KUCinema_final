# 전역변수는 복붙해서 각자 .py 파일에 쓰기 
import os
import sys
import re
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Tuple, List
from collections import defaultdict
import ast


MOVIE_FILE = "movie-info.txt"
STUDENT_FILE = "student-info.txt"
BOOKING_FILE = "booking-info.txt"
SCHEDULE_FILE = "schedule-info.txt"


## 전체 데이터 파일 정규식 패턴
# 날짜, 영화 상영 날짜, 타임스탬프: 연, 월, 일 유효성 포함 (월 01~12, 일 01~31)
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


## 학생 데이터 정규식 패턴
# 학번(2자리 숫자) 및 비밀번호(4자리 숫자) 정규식 패턴
RE_STUDENT_ID = re.compile(r"^[0-9]{2}$")       # 00~99
RE_PASSWORD = re.compile(r"^[0-9]{4}$")         # 0000~9999



# 전역 상태 (필수 컨텍스트)
CURRENT_DATE_STR: str | None = None  # 내부 현재 날짜(문자열, YYYY-MM-DD)
LATEST_DATE_STR: str | None = None   # 최종 작업 날짜 
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


## 유틸리티 출력 함수
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


def validate_schedule_id_duplication(schedule_path: Path) -> Tuple[bool, List[str]]:
    """
    상영 데이터 파일 내에서 중복된 상영 고유 번호가 존재하는지 검사한다.

    매개변수:
        schedule_path: Path - 상영 데이터 파일 경로

    반환값:
        (is_ok, error_lines)
        - is_ok: 규칙 검증 오류(중복 상영 ID)가 하나도 없으면 True, 하나 이상 있으면 False
        - error_lines: 중복된 상영 고유 번호를 가진 '원본 문자열' 리스트
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
        return True, []

    # 중복 상영 ID를 가진 레코드(원본 문자열)만 오류 리스트에 담는다.
    error_lines: List[str] = [
        original for sid, original in records if sid in duplicated_ids
    ]

    return False, error_lines

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
            if end_curr > start_next:
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
        if end_min > 1440:
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
                print(result)
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
        
        for line in lines:
            line = line.rstrip('\n')
            parts = line.split('/')
            
            if len(parts) == 5:
                student_id, schedule_id, seats_vector, record_valid, timestamp = parts
                
                # 좌석 벡터 파싱
                seats = ast.literal_eval(seats_vector)
                
                # 모든 좌석이 0이고 레코드가 유효한 경우
                if all(seat == 0 for seat in seats) and record_valid == 'T':
                    # 유효 여부를 F로 변경, 타임스탬프를 현재 날짜로 변경
                    modified_line = f"{student_id}/{schedule_id}/{seats_vector}/F/{CURRENT_DATE_STR}\n"
                    modified = True  # 수정 발생
                else:
                    modified_line = line + '\n'
            else:
                modified_line = line + '\n'
            
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

    is_ok, error_lines = validate_schedule_id_duplication(Path(SCHEDULE_FILE))
    if not is_ok:
        error(f"상영 데이터 파일\n{SCHEDULE_FILE}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        for line in error_lines:
            print(line)
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

    is_ok = check_seat_consistency(bookings)
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
        
  

def main():
    """
    프로그램의 진입점(main) 함수입니다.
    데이터 파일 체크 등 초기화 루틴을 수행합니다.
    """
    check_file(Path(MOVIE_FILE))
    check_file(Path(STUDENT_FILE))
    check_file(Path(BOOKING_FILE))
    check_file(Path(SCHEDULE_FILE))

    verify_integrity()

  

if __name__ == "__main__":
    main()





