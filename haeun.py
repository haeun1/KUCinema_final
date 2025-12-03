# 전역변수는 복붙해서 각자 .py 파일에 쓰기 
import os
import sys
import re
from pathlib import Path
from datetime import date
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
