# yeeun.py
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Tuple, List
from collections import defaultdict
import ast
import re

# ==================== 전역 상수/상태 ====================

# 데이터 파일 경로 상수
MOVIE_FILE = "movie-info.txt"
STUDENT_FILE = "student-info.txt"
BOOKING_FILE = "booking-info.txt"
SCHEDULE_FILE = "schedule-info.txt"

# 날짜/로그인 상태 전역 변수 
CURRENT_DATE_STR: str | None = None  # 내부 현재 날짜(문자열, YYYY-MM-DD)
LATEST_DATE_STR: str | None = None   # 최종 작업 날짜
LOGGED_IN_SID: str | None = None     # 로그인된 학번(2자리)

#Class 선언
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

# # 임시 영화 데이터 파일 파싱 함수 - 테스트용
# def parse_movie_data(movie_path: Path) -> List[Movie]:
#     """
#     형식 검증이 완료된 파일을 읽어 Movie 객체 리스트로 변환합니다.
#     레코드 유효 여부가 T인 레코드만 추출합니다.
#     """
#     movies = []
    
#     try:
#         with open(movie_path, 'r', encoding='utf-8') as f:
#             for line in f:
#                 line = line.rstrip('\n')
#                 parts = line.split('/')
                
#                 if len(parts) == 5:
#                     movie_id, movie_name, running_time, record_valid, timestamp = parts
                    
#                     # 유효한 레코드만 처리
#                     if record_valid == 'T':
#                         # Movie 객체 생성
#                         movie = Movie()
#                         movie.movie_id = movie_id
#                         movie.movie_name = movie_name
#                         movie.running_time = int(running_time)
#                         movie.time_stamp = timestamp
#                         movies.append(movie)
    
#     except FileNotFoundError:
#         return []
    
#     return movies

# # 임시 상영 데이터 파일 파싱 함수 - 테스트용
# def parse_schedule_data(schedule_path: Path) -> List[Schedule]:
#     """
#     형식 검증이 완료된 파일을 읽어 Schedule 객체 리스트로 변환합니다.
#     레코드 유효 여부가 T인 레코드만 추출합니다.
#     """
#     schedules = []
    
#     try:
#         with open(schedule_path, 'r', encoding='utf-8') as f:
#             for line in f:
#                 line = line.rstrip('\n')
#                 parts = line.split('/')
                
#                 if len(parts) == 7:
#                     schedule_id, movie_id, movie_date, movie_start_time, seats_vector, record_valid, timestamp = parts
                    
#                     # 유효한 레코드만 처리
#                     if record_valid == 'T':
#                         # 좌석 벡터 파싱
#                         seats = ast.literal_eval(seats_vector)
                        
#                         # Schedule 객체 생성
#                         schedule = Schedule()
#                         schedule.schedule_id = schedule_id
#                         schedule.movie_id = movie_id
#                         schedule.movie_date = movie_date
#                         schedule.movie_start_time = movie_start_time
#                         schedule.seats_vector = seats
#                         schedule.time_stamp = timestamp
#                         schedules.append(schedule)
    
#     except FileNotFoundError:
#         return []
    
#     return schedules

# ==================== 1.4 학생 데이터 파일 ====================

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


# ==================== 1.5 예매 데이터 파일 ====================

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
                else:
                    modified_line = line + '\n'
            else:
                modified_line = line + '\n'
            
            modified_lines.append(modified_line)
        
        # 파일 쓰기
        with open(booking_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
    
    except FileNotFoundError:
        pass


# ==================== 2. 날짜 입력 및 로그인 사용 흐름 ====================

def init_latest_date() -> str:
    """
    모든 데이터 파일의 타임스탬프를 읽어 최종 작업 날짜를 결정합니다.
    
    Returns:
        str: 최종 작업 날짜 (YYYY-MM-DD)
    """
    latest = None
    
    # haeun.py의 전역 변수 활용
    files = [MOVIE_FILE, SCHEDULE_FILE, STUDENT_FILE, BOOKING_FILE]
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.rstrip('\n')
                    parts = line.split('/')
                    
                    if len(parts) >= 2:
                        # 타임스탬프는 마지막 필드
                        timestamp = parts[-1]
                        
                        # haeun.py의 정규식 활용
                        if RE_DATE.match(timestamp):
                            if latest is None:
                                latest = timestamp
                            else:
                                latest = max(latest, timestamp)
        
        except FileNotFoundError:
            continue
    
    if latest is None:
        return "1582-10-15"
    
    #(latest)
    return latest


# def prompt_input_date() -> None:
#     """
#     날짜 입력 프롬프트를 실행합니다.
#     올바른 입력이 들어올 때까지 반복하며, 전역 변수를 설정합니다.
#     """
#     # haeun.py의 전역 변수 사용
#     global CURRENT_DATE_STR, LATEST_DATE_STR
    
#     # 최종 작업 날짜 초기화
#     LATEST_DATE_STR = init_latest_date()
    
#     while True:
#         print(f"현재 날짜를 입력하세요 (YYYY-MM-DD 형식, {LATEST_DATE_STR} 이후):")
#         s = input().strip()
        
#         # 형식 확인 (haeun.py의 정규식 활용)
#         if len(s) != 10 or not RE_DATE.match(s):
#             print("잘못된 형식입니다. YYYY-MM-DD 형식으로 입력해주세요.")
#             continue
        
#         # 날짜 유효성 확인
#         if not _validate_timestamp(s):
#             print("유효하지 않은 날짜입니다.")
#             continue
        
#         # 최종 작업 날짜 이후 확인
#         if s <= LATEST_DATE_STR:
#             print(f"날짜는 {LATEST_DATE_STR} 이후여야 합니다.")
#             continue
        
#         # 전역 변수 설정
#         CURRENT_DATE_STR = s
#         print(f"현재 날짜가 {CURRENT_DATE_STR}로 설정되었습니다.")
#         break
