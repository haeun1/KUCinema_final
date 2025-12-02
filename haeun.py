# 전역변수는 복붙해서 각자 .py 파일에 쓰기 

MOVIE_FILE = "movie-info.txt"
STUDENT_FILE = "student-info.txt"
BOOKING_FILE = "booking-info.txt"
SCHEDULE_FILE = "schedule-info.txt"

# 정규식 패턴 (문법 형식)
# 내가 빨리 정리해볼게 @haeun - 오늘 

# 전역 상태 (필수 컨텍스트)
CURRENT_DATE_STR: str | None = None  # 내부 현재 날짜(문자열, YYYY-MM-DD)
LATEST_DATE_STR: str | None = None   # 최종 작업 날짜 
LOGGED_IN_SID: str | None = None     # 로그인된 학번(2자리)

# 밑에는 모두 함수로 모듈화 