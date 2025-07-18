#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실제 데이터 구조에 맞는 샘플 데이터 생성 스크립트
"""

import pandas as pd
import random

def create_real_leader_data():
    """실제 구조에 맞는 조장/헬퍼 샘플 데이터 생성"""
    leaders_data = []
    
    # 5개 조의 조장/헬퍼 데이터
    for group_num in range(1, 6):
        # 조장
        leaders_data.append({
            '조 숫자': group_num,
            '학교/학년': random.choice([
                '대구한 본2', '서울대 본1', '연세대 본1', '고려대 본1', '성균관대 본1',
                '부산대 본1', '경남대 본1', '대구대 본1', '경북대 본1',
                '인천대 본1', '경기대 본1', '광주대 본1', '전남대 본1',
                '대전대 본1', '충남대 본1', '강원대 본1', '제주대 본1'
            ]),
            '이름': f'조장{group_num}',
            '학과': random.choice(['한', '의', '치', '간호', '약']),
            '성별': random.choice(['남', '여']),
            '조장or헬퍼': '조장',
            '나이': random.randint(24, 35),
            '연락처': f'010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}'
        })
        
        # 헬퍼
        leaders_data.append({
            '조 숫자': group_num,
            '학교/학년': random.choice([
                '대구한 본2', '서울대 본1', '연세대 본1', '고려대 본1', '성균관대 본1',
                '부산대 본1', '경남대 본1', '대구대 본1', '경북대 본1',
                '인천대 본1', '경기대 본1', '광주대 본1', '전남대 본1',
                '대전대 본1', '충남대 본1', '강원대 본1', '제주대 본1'
            ]),
            '이름': f'헬퍼{group_num}',
            '학과': random.choice(['한', '의', '치', '간호', '약']),
            '성별': random.choice(['남', '여']),
            '조장or헬퍼': '헬퍼',
            '나이': random.randint(23, 30),
            '연락처': f'010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}'
        })
    
    df_leaders = pd.DataFrame(leaders_data)
    df_leaders.to_excel('real_leaders.xlsx', sheet_name='Sheet1', index=False)
    print("실제 구조 조장/헬퍼 데이터 생성 완료: real_leaders.xlsx")

def create_real_member_data():
    """실제 구조에 맞는 조원 샘플 데이터 생성"""
    members_data = []
    
    # 35명의 조원 데이터 (5개 조에 6-7명씩 배정)
    for i in range(1, 36):
        # 의대 24/25학번 분리 테스트를 위한 특별 케이스
        if i <= 5:
            major = '의'
            year = '25'
            grade = '예과1'
        elif i <= 10:
            major = '의'
            year = '24'
            grade = '예과2'
        else:
            major = random.choice(['의', '치', '한', '간호', '약', '물리', '임상'])
            year = f'{random.randint(23, 25)}'
            grade = random.choice(['예과1', '예과2', '본1', '본2', '본3'])
        
        members_data.append({
            '번호': i,
            '이름': f'조원{i}',
            '성별': random.choice(['남', '여']),
            '지역': random.choice(['충북천안', '서울', '부산', '대구', '인천', '광주', '대전', '강원', '제주']),
            '캠퍼스': random.choice([
                '충북대', '서울대', '연세대', '고려대', '성균관대',
                '부산대', '경남대', '대구대', '경북대',
                '인천대', '경기대', '광주대', '전남대',
                '대전대', '충남대', '강원대', '제주대'
            ]),
            '트랙': 'EBS',
            '참가유형': '일반참',
            '학과': major,
            '학년': grade,
            '학번': year,
            '졸업년도': '-',
            '나이': f'{random.randint(20, 30)}세',
            '연락처': f'010{random.randint(10000000, 99999999)}',
            '참가일정': '월, 화, 수, 목, 금',
            '기숙사사용여부': '사용',
            '은행명': random.choice(['하나은행', '신한은행', '국민은행', '우리은행']),
            '계좌번호': f'{random.randint(100000000000000, 999999999999999)}',
            '예금주': f'조원{i}',
            '결제금액': 220000,
            '상태': '승인됨',
            '등록일': '2025.7.15. 14:50'
        })
    
    df_members = pd.DataFrame(members_data)
    df_members.to_excel('real_members.xlsx', sheet_name='등록 데이터', index=False)
    print("실제 구조 조원 데이터 생성 완료: real_members.xlsx")

if __name__ == '__main__':
    print("실제 데이터 구조 샘플 데이터 생성 중...")
    create_real_leader_data()
    create_real_member_data()
    print("모든 실제 구조 샘플 데이터 생성 완료!") 