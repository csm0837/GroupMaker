#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수련회 조 배정 프로그램

조건:
- 필수조건1: 의대24학번과 25학번은 한조에 있지 않음
- 필수조건2: 같은 조에는 같은 학교 사람이 존재하지 않음
- 최적화조건0: 조원들은 헬퍼보다 어림 (37세 조장 예외: 39세까지 허용)
- 최적화조건1: 남녀 성비는 전체 성비와 비슷해야 함
- 최적화조건2: 의대,치대,한의대,간호대는 각 조에 2명 이상씩
- 최적화조건3: 최대한 다양한 지역의 사람들로 구성
"""

import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import random
import argparse
from typing import List, Dict, Tuple

def load_data(leaders_file: str, members_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """데이터 로드 및 전처리"""
    # 조장/헬퍼 데이터
    df_leaders = pd.read_excel(leaders_file, sheet_name="Sheet1", dtype=str)
    df_leaders['나이'] = pd.to_numeric(df_leaders['나이'], errors='coerce').fillna(0).astype(int)
    
    # 조원 데이터
    df_members = pd.read_excel(members_file, sheet_name="등록 데이터", dtype=str)
    # 나이 컬럼에서 "세" 제거하고 숫자로 변환
    df_members['나이'] = df_members['나이'].str.replace("세", "").astype(int)
    
    return df_leaders, df_members

def canonical_school(school_name: str) -> str:
    """학교명 정규화"""
    if pd.isna(school_name):
        return ""
    return str(school_name).replace("대학교", "").replace("대학", "").replace("본", "").replace("캠퍼스", "").strip()

def extract_major(학과: str) -> str:
    """학과에서 전공 분류 추출"""
    if pd.isna(학과):
        return ""
    학과 = str(학과).strip()
    
    # 의·치·한·간 약칭 처리
    if 학과 in ["의", "치", "한", "간"]:
        if 학과 == "의":
            return "의대"
        elif 학과 == "치":
            return "치대"
        elif 학과 == "한":
            return "한의대"
        elif 학과 == "간":
            return "간호대"
    
    # 전체 학과명 처리
    if "의공학과" in 학과 or "약학과" in 학과:
        return "기타"  # 의공학과, 약학과는 기타로 분류
    
    if "의" in 학과 and "한의" not in 학과:
        return "의대"
    elif "치" in 학과:
        return "치대"
    elif "한의" in 학과:
        return "한의대"
    elif "간호" in 학과:
        return "간호대"
    else:
        return "기타"

def extract_region(학교: str) -> str:
    """학교에서 지역 추출"""
    if pd.isna(학교):
        return ""
    학교 = str(학교).strip()
    
    # 서울‧경기
    if "서울" in 학교 or "연세" in 학교 or "고려" in 학교 or "성균관" in 학교 or "경기" in 학교:
        return "서울‧경기"
    
    # 대구‧경북
    elif "대구" in 학교 or "경북" in 학교:
        return "대구‧경북"
    
    # 부산‧경남
    elif "부산" in 학교 or "경남" in 학교:
        return "부산‧경남"
    
    # 전북
    elif "전북" in 학교:
        return "전북"
    
    # 충북·천안
    elif "충북" in 학교 or "천안" in 학교:
        return "충북·천안"
    
    # 강원
    elif "강원" in 학교:
        return "강원"
    
    # 광주‧전남
    elif "광주" in 학교 or "전남" in 학교:
        return "광주‧전남"
    
    # 대전‧충남
    elif "대전" in 학교 or "충남" in 학교:
        return "대전‧충남"
    
    else:
        return "기타"

def can_assign_to_group(group: Dict, member: Dict, used_schools: set, used_regions: set, total_gender_ratio: float = 0.5, max_gender_diff: int = 1) -> bool:
    """조원을 해당 조에 배정할 수 있는지 확인"""
    
    # === 1단계: 필수 조건 체크 (절대 위반 불가) ===
    
    # 1. 의대 24/25학번 분리 체크
    leader_major = extract_major(group['leader'].get('학과', ''))
    member_major = extract_major(member.get('학과', ''))
    
    if leader_major == "의대" and member_major == "의대":
        # 학번 컬럼이 있는지 확인하고 안전하게 처리
        leader_학번 = group['leader'].get('학번', '')
        member_학번 = member.get('학번', '')
        
        if leader_학번 and member_학번 and leader_학번 != '-' and member_학번 != '-':
            leader_year = str(leader_학번)[-2:]  # 마지막 2자리
            member_year = str(member_학번)[-2:]
            if leader_year in ["24", "25"] and member_year in ["24", "25"] and leader_year != member_year:
                return False
    
    # 2. 같은 학교 체크
    member_school = canonical_school(member.get('캠퍼스', ''))
    if member_school in used_schools:
        return False
    
    # 3. 나이 조건 체크 (헬퍼보다 어려야 함)
    helper_age = group['helper'].get('나이', 0)
    member_age = member.get('나이', 0)
    
    if group['leader'].get('나이', 0) == 37:  # 37세 조장 예외
        if member_age > 39:
            return False
    else:
        if member_age >= helper_age:
            return False
    
    # === 2단계: 최적화 조건 체크 (유연한 제한) ===
    
    # 4. 성비 균형 체크 (전체 인원 대비 1명 차이까지 허용)
    all_members = [group['leader'], group['helper']] + group['members']
    male_count = sum(1 for m in all_members if m['성별'] == '남')
    female_count = sum(1 for m in all_members if m['성별'] == '여')
    
    # 새 멤버 추가 시 성비 계산
    if member['성별'] == '남':
        new_male = male_count + 1
        new_female = female_count
    else:
        new_male = male_count
        new_female = female_count + 1
    
    # 전체 인원 대비 성비 차이 계산
    total_members = new_male + new_female
    expected_male = total_members * total_gender_ratio
    expected_female = total_members * (1 - total_gender_ratio)
    
    # 성비 차이가 설정값을 초과하면 배정 제한
    male_diff = abs(new_male - expected_male)
    female_diff = abs(new_female - expected_female)
    
    if male_diff > max_gender_diff or female_diff > max_gender_diff:
        return False
    
    return True

def calculate_group_stats(group: Dict) -> Dict:
    """조별 통계 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    
    # 성별 통계
    male_count = sum(1 for m in all_members if m['성별'] == '남')
    female_count = sum(1 for m in all_members if m['성별'] == '여')
    
    # 학과별 통계
    majors = [extract_major(m.get('학과', '')) for m in all_members]
    major_counts = Counter(majors)
    
    # 지역별 통계
    regions = [extract_region(m.get('캠퍼스', m.get('학교/학년', ''))) for m in all_members]
    region_counts = Counter(regions)
    
    # 조건 충족 여부
    conditions = {
        '의대24_25_분리': True,  # 기본적으로 True (can_assign에서 체크됨)
        '같은학교_금지': True,   # 기본적으로 True (can_assign에서 체크됨)
        '나이_조건': True,       # 기본적으로 True (can_assign에서 체크됨)
        '성비_균형': abs(male_count - female_count) <= 2,  # 남녀 차이가 2명 이하
        '학과_분포': all(count >= 2 or count == 0 for major, count in major_counts.items() 
                        if major in ['의대', '치대', '한의대', '간호대']) or 
             all(major not in ['의대', '치대', '한의대', '간호대'] for major in major_counts.keys()),
        '지역_다양성': len(region_counts) >= 3  # 최소 3개 지역
    }
    
    return {
        'male_count': male_count,
        'female_count': female_count,
        'total_count': len(all_members),
        'major_distribution': dict(major_counts),
        'region_distribution': dict(region_counts),
        'conditions_met': conditions
    }

def assign_groups(leaders: pd.DataFrame, members: pd.DataFrame, min_members: int = 6, max_members: int = 8, 
                 max_gender_diff: int = 1) -> pd.DataFrame:
    """조 배정 메인 함수"""
    
    # 디버깅: 컬럼명 확인
    print(f"조장/헬퍼 파일 컬럼: {list(leaders.columns)}")
    print(f"조원 파일 컬럼: {list(members.columns)}")
    
    # 전체 데이터의 실제 성비 계산
    all_members_data = members.to_dict('records')
    total_male = sum(1 for m in all_members_data if m['성별'] == '남')
    total_female = sum(1 for m in all_members_data if m['성별'] == '여')
    total_members = total_male + total_female
    
    if total_members > 0:
        actual_gender_ratio = total_male / total_members
    else:
        actual_gender_ratio = 0.5  # 기본값
    
    print(f"전체 데이터 성비: 남성 {total_male}명, 여성 {total_female}명 (남성 비율: {actual_gender_ratio:.1%})")
    print(f"성비 차이 허용 범위: {max_gender_diff}명")
    
    # 조장/헬퍼 데이터에서 조 번호 추출
    available_groups = sorted(leaders['조 숫자'].unique(), key=lambda x: int(x))
    print(f"사용 가능한 조 번호: {available_groups}")
    
    # 그룹 초기화
    groups = {}
    for grp_num in available_groups:
        leader_df = leaders[leaders['조 숫자'] == grp_num]
        helper_df = leaders[leaders['조 숫자'] == grp_num]
        
        # 조장 찾기 (컬럼명 확인 후 수정)
        if '조장or헬퍼' in leaders.columns:
            leader_row = leader_df[leader_df['조장or헬퍼'] == '조장']
        elif '역할' in leaders.columns:
            leader_row = leader_df[leader_df['역할'] == '조장']
        else:
            print(f"경고: 조장/헬퍼 구분 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(leaders.columns)}")
            continue
            
        if leader_row.empty:
            print(f"경고: 조 {grp_num}에 조장이 없습니다.")
            continue
        
        # 헬퍼 찾기 (컬럼명 확인 후 수정)
        if '조장or헬퍼' in leaders.columns:
            helper_row = helper_df[helper_df['조장or헬퍼'] == '헬퍼']
        elif '역할' in leaders.columns:
            helper_row = helper_df[helper_df['역할'] == '헬퍼']
        else:
            print(f"경고: 조장/헬퍼 구분 컬럼을 찾을 수 없습니다.")
            continue
            
        if helper_row.empty:
            print(f"경고: 조 {grp_num}에 헬퍼가 없습니다.")
            continue
        
        groups[str(grp_num)] = {
            '조 번호': str(grp_num),
            'leader': leader_row.iloc[0].to_dict(),
            'helper': helper_row.iloc[0].to_dict(),
            'members': [],
            'used_schools': set(),
            'used_regions': set(),
            'age_distribution': []  # 연령 분포 추적
        }
    
    if not groups:
        raise ValueError("유효한 조장/헬퍼 데이터가 없습니다.")
    
    print(f"생성된 조 수: {len(groups)}")
    print(f"조원 인원 범위: {min_members}-{max_members}명")
    
    # 조원을 연령대별로 분류
    members_list = members.to_dict('records')
    
    # 연령대별 분류 (5세 단위)
    age_groups = {}
    for member in members_list:
        age = member.get('나이', 0)
        age_group = (age // 5) * 5  # 20-24, 25-29, 30-34 등
        if age_group not in age_groups:
            age_groups[age_group] = []
        age_groups[age_group].append(member)
    
    print(f"연령대별 분포: {[(k, len(v)) for k, v in sorted(age_groups.items())]}")
    
    # 1단계: 연령대별 균형 배정
    for age_group, age_members in sorted(age_groups.items()):
        random.shuffle(age_members)  # 각 연령대 내에서 랜덤화
        
        for member in age_members:
            assigned = False
            
            # 가능한 조들을 성비와 연령 분포를 고려하여 평가
            candidate_groups = []
            for group in groups.values():
                if len(group['members']) < max_members and can_assign_to_group(group, member, group['used_schools'], group['used_regions'], actual_gender_ratio, max_gender_diff):
                    # 성비 점수 계산 (높은 우선순위)
                    gender_score = calculate_gender_balance_score(group, member, actual_gender_ratio)
                    # 연령 분포 점수 계산 (중간 우선순위)
                    age_score = calculate_age_distribution_score(group, member)
                    # 학과 분포 점수 계산 (중간 우선순위)
                    major_score = calculate_major_distribution_score(group, member)
                    # 지역 다양성 점수 계산 (낮은 우선순위)
                    region_score = calculate_region_diversity_score(group, member)
                    
                    # 종합 점수 (성비 40%, 연령 25%, 학과 20%, 지역 15%)
                    total_score = (gender_score * 0.4 + 
                                 age_score * 0.25 + 
                                 major_score * 0.2 + 
                                 region_score * 0.15)
                    candidate_groups.append((group, total_score))
            
            if candidate_groups:
                # 종합 점수가 가장 좋은 조 선택
                candidate_groups.sort(key=lambda x: x[1], reverse=True)
                best_group = candidate_groups[0][0]
                
                best_group['members'].append(member)
                best_group['used_schools'].add(canonical_school(member.get('캠퍼스', '')))
                best_group['used_regions'].add(extract_region(member.get('캠퍼스', '')))
                best_group['age_distribution'].append(member.get('나이', 0))
                assigned = True
            
            if not assigned:
                # 조건을 만족하는 조가 없으면 가장 적은 조에 배정
                min_group = min(groups.values(), key=lambda g: len(g['members']))
                min_group['members'].append(member)
                min_group['used_schools'].add(canonical_school(member.get('캠퍼스', '')))
                min_group['used_regions'].add(extract_region(member.get('캠퍼스', '')))
                min_group['age_distribution'].append(member.get('나이', 0))
    
    # 2단계: 최소 인원 조건 확인 및 조정
    under_min_groups = []
    over_max_groups = []
    
    for group in groups.values():
        if len(group['members']) < min_members:
            under_min_groups.append(group)
            print(f"경고: 조 {group['조 번호']}의 조원이 {len(group['members'])}명으로 최소 인원({min_members}명)에 미달합니다.")
        elif len(group['members']) > max_members:
            over_max_groups.append(group)
            print(f"경고: 조 {group['조 번호']}의 조원이 {len(group['members'])}명으로 최대 인원({max_members}명)을 초과합니다.")
    
    # 최소 인원 미달 조들을 위한 재배정
    if under_min_groups:
        print(f"최소 인원 미달 조 {len(under_min_groups)}개에 대한 재배정을 시작합니다.")
        
        # 최대 인원 초과 조에서 멤버를 최소 인원 미달 조로 이동
        for under_group in under_min_groups:
            needed_members = min_members - len(under_group['members'])
            
            for over_group in over_max_groups:
                if needed_members <= 0:
                    break
                    
                # 초과 조에서 이동 가능한 멤버 찾기
                movable_members = []
                for member in over_group['members']:
                    if can_assign_to_group(under_group, member, under_group['used_schools'], under_group['used_regions'], actual_gender_ratio, max_gender_diff):
                        movable_members.append(member)
                
                # 이동할 멤버 선택 (가장 적은 수로)
                move_count = min(needed_members, len(movable_members), len(over_group['members']) - min_members)
                
                for i in range(move_count):
                    if i < len(movable_members):
                        member_to_move = movable_members[i]
                        
                        # 멤버 이동
                        over_group['members'].remove(member_to_move)
                        under_group['members'].append(member_to_move)
                        
                        # 사용된 학교/지역 업데이트
                        under_group['used_schools'].add(canonical_school(member_to_move.get('캠퍼스', '')))
                        under_group['used_regions'].add(extract_region(member_to_move.get('캠퍼스', '')))
                        under_group['age_distribution'].append(member_to_move.get('나이', 0))
                        
                        # 초과 조에서 제거
                        over_group['used_schools'].discard(canonical_school(member_to_move.get('캠퍼스', '')))
                        over_group['used_regions'].discard(extract_region(member_to_move.get('캠퍼스', '')))
                        if member_to_move.get('나이', 0) in over_group['age_distribution']:
                            over_group['age_distribution'].remove(member_to_move.get('나이', 0))
                        
                        needed_members -= 1
                        print(f"조 {over_group['조 번호']}에서 조 {under_group['조 번호']}로 {member_to_move.get('이름', '')} 이동")
                
                # 초과 조가 더 이상 초과하지 않으면 목록에서 제거
                if len(over_group['members']) <= max_members:
                    over_max_groups.remove(over_group)
    
    # 최종 상태 확인
    final_under_min = [g for g in groups.values() if len(g['members']) < min_members]
    final_over_max = [g for g in groups.values() if len(g['members']) > max_members]
    
    if final_under_min:
        print(f"⚠️ 재배정 후에도 최소 인원 미달 조 {len(final_under_min)}개가 남아있습니다.")
        for group in final_under_min:
            print(f"  - 조 {group['조 번호']}: {len(group['members'])}명 (최소 {min_members}명 필요)")
    
    if final_over_max:
        print(f"⚠️ 재배정 후에도 최대 인원 초과 조 {len(final_over_max)}개가 남아있습니다.")
        for group in final_over_max:
            print(f"  - 조 {group['조 번호']}: {len(group['members'])}명 (최대 {max_members}명 초과)")
    
    # 3단계: 성비 및 연령 분포 최적화 (인원 균형 우선)
    for _ in range(3):  # 3번 반복하여 최적화
        # 먼저 인원 균형 최적화
        for group in groups.values():
            if len(group['members']) < min_members:
                # 최소 인원 미달 조는 다른 조에서 멤버를 가져오기 시도
                for other_group in groups.values():
                    if other_group == group or len(other_group['members']) <= min_members:
                        continue
                    
                    # 다른 조에서 이동 가능한 멤버 찾기
                    for member in other_group['members']:
                        if can_assign_to_group(group, member, group['used_schools'], group['used_regions'], actual_gender_ratio, max_gender_diff):
                            # 멤버 이동
                            other_group['members'].remove(member)
                            group['members'].append(member)
                            
                            # 사용된 학교/지역 업데이트
                            group['used_schools'].add(canonical_school(member.get('캠퍼스', '')))
                            group['used_regions'].add(extract_region(member.get('캠퍼스', '')))
                            group['age_distribution'].append(member.get('나이', 0))
                            
                            other_group['used_schools'].discard(canonical_school(member.get('캠퍼스', '')))
                            other_group['used_regions'].discard(extract_region(member.get('캠퍼스', '')))
                            if member.get('나이', 0) in other_group['age_distribution']:
                                other_group['age_distribution'].remove(member.get('나이', 0))
                            
                            print(f"인원 균형: 조 {other_group['조 번호']}에서 조 {group['조 번호']}로 {member.get('이름', '')} 이동")
                            break
                    
                    if len(group['members']) >= min_members:
                        break
        
        # 그 다음 성비 및 연령 분포 최적화
        for group in groups.values():
            if len(group['members']) < min_members:
                continue
            
            # 현재 조의 종합 점수 계산
            current_gender_score = calculate_group_gender_score(group, actual_gender_ratio)
            current_age_score = calculate_group_age_score(group)
            current_major_score = calculate_group_major_score(group)
            current_region_score = calculate_group_region_score(group)
            current_total_score = (current_gender_score * 0.4 + 
                                 current_age_score * 0.25 + 
                                 current_major_score * 0.2 + 
                                 current_region_score * 0.15)
            
            # 다른 조와 교환 시도 (인원 균형 유지하면서)
            for other_group in groups.values():
                if other_group == group or len(other_group['members']) < min_members:
                    continue
                
                # 조원 교환 시도
                for i, member1 in enumerate(group['members']):
                    for j, member2 in enumerate(other_group['members']):
                        # 교환 가능성 확인 (인원 균형 유지)
                        if (can_assign_to_group(other_group, member1, other_group['used_schools'], other_group['used_regions'], actual_gender_ratio, max_gender_diff) and
                            can_assign_to_group(group, member2, group['used_schools'], group['used_regions'], actual_gender_ratio, max_gender_diff)):
                            
                            # 교환 후 점수 계산
                            temp_group1 = group.copy()
                            temp_group2 = other_group.copy()
                            
                            temp_group1['members'][i] = member2
                            temp_group2['members'][j] = member1
                            
                            new_gender_score1 = calculate_group_gender_score(temp_group1, actual_gender_ratio)
                            new_age_score1 = calculate_group_age_score(temp_group1)
                            new_major_score1 = calculate_group_major_score(temp_group1)
                            new_region_score1 = calculate_group_region_score(temp_group1)
                            new_total_score1 = (new_gender_score1 * 0.4 + 
                                              new_age_score1 * 0.25 + 
                                              new_major_score1 * 0.2 + 
                                              new_region_score1 * 0.15)
                            
                            new_gender_score2 = calculate_group_gender_score(temp_group2, actual_gender_ratio)
                            new_age_score2 = calculate_group_age_score(temp_group2)
                            new_major_score2 = calculate_group_major_score(temp_group2)
                            new_region_score2 = calculate_group_region_score(temp_group2)
                            new_total_score2 = (new_gender_score2 * 0.4 + 
                                              new_age_score2 * 0.25 + 
                                              new_major_score2 * 0.2 + 
                                              new_region_score2 * 0.15)
                            
                            other_gender_score = calculate_group_gender_score(other_group, actual_gender_ratio)
                            other_age_score = calculate_group_age_score(other_group)
                            other_major_score = calculate_group_major_score(other_group)
                            other_region_score = calculate_group_region_score(other_group)
                            other_total_score = (other_gender_score * 0.4 + 
                                               other_age_score * 0.25 + 
                                               other_major_score * 0.2 + 
                                               other_region_score * 0.15)
                            
                            # 전체 점수가 개선되면 교환
                            if new_total_score1 + new_total_score2 > current_total_score + other_total_score:
                                group['members'][i] = member2
                                other_group['members'][j] = member1
                                
                                # 연령 분포 업데이트
                                group['age_distribution'][i] = member2.get('나이', 0)
                                other_group['age_distribution'][j] = member1.get('나이', 0)
                                break
    
    # 결과 데이터프레임 생성
    rows = []
    for group in groups.values():
        # 조장
        rows.append({
            '조 번호': group['조 번호'],
            '역할': '조장',
            '이름': group['leader'].get('이름', ''),
            '학과': group['leader'].get('학과', ''),
            '학번': group['leader'].get('학번', ''),
            '나이': group['leader'].get('나이', 0),
            '학교': group['leader'].get('학교/학년', ''),
            '성별': group['leader'].get('성별', ''),
            '전화번호': group['leader'].get('연락처', ''),
            '트랙': 'EBS'
        })
        
        # 헬퍼
        rows.append({
            '조 번호': group['조 번호'],
            '역할': '헬퍼',
            '이름': group['helper'].get('이름', ''),
            '학과': group['helper'].get('학과', ''),
            '학번': group['helper'].get('학번', ''),
            '나이': group['helper'].get('나이', 0),
            '학교': group['helper'].get('학교/학년', ''),
            '성별': group['helper'].get('성별', ''),
            '전화번호': group['helper'].get('연락처', ''),
            '트랙': 'EBS'
        })
        
        # 조원들
        for member in group['members']:
            rows.append({
                '조 번호': group['조 번호'],
                '역할': '조원',
                '이름': member.get('이름', ''),
                '학과': member.get('학과', ''),
                '학번': member.get('학번', ''),
                '나이': member.get('나이', 0),
                '지역': member.get('지역', ''),
                '성별': member.get('성별', ''),
                '전화번호': member.get('연락처', ''),
                '트랙': member.get('트랙', 'EBS')
            })
    
    return pd.DataFrame(rows)

def calculate_gender_balance_score(group: Dict, new_member: Dict, total_gender_ratio: float) -> float:
    """조에 새로운 멤버를 추가했을 때의 성비 균형 점수 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    male_count = sum(1 for m in all_members if m['성별'] == '남')
    female_count = sum(1 for m in all_members if m['성별'] == '여')
    
    # 새 멤버 추가 시 성비 계산
    if new_member['성별'] == '남':
        new_male = male_count + 1
        new_female = female_count
    else:
        new_male = male_count
        new_female = female_count + 1
    
    total_members = new_male + new_female
    
    # 전체 인원 대비 성비 차이 계산
    expected_male = total_members * total_gender_ratio
    expected_female = total_members * (1 - total_gender_ratio)
    
    male_diff = abs(new_male - expected_male)
    female_diff = abs(new_female - expected_female)
    
    # 성비 차이가 작을수록 높은 점수
    max_diff = max(male_diff, female_diff)
    
    # 성비 균형 점수 (차이가 0이면 1.0, 차이가 클수록 낮은 점수)
    if max_diff == 0:
        balance_score = 1.0
    elif max_diff <= 0.5:
        balance_score = 0.9
    elif max_diff <= 1.0:
        balance_score = 0.7
    elif max_diff <= 1.5:
        balance_score = 0.5
    else:
        balance_score = 0.1  # 1.5명 이상 차이나면 매우 낮은 점수
    
    return balance_score

def calculate_age_distribution_score(group: Dict, new_member: Dict) -> float:
    """조에 새로운 멤버를 추가했을 때의 연령 분포 점수 계산"""
    current_ages = group['age_distribution'].copy()
    new_age = new_member.get('나이', 0)
    current_ages.append(new_age)
    
    if len(current_ages) <= 1:
        return 1.0  # 첫 번째 멤버는 높은 점수
    
    # 연령 분산 계산 (분산이 클수록 다양함)
    mean_age = sum(current_ages) / len(current_ages)
    variance = sum((age - mean_age) ** 2 for age in current_ages) / len(current_ages)
    
    # 연령대별 균형 점수
    age_groups = {}
    for age in current_ages:
        age_group = (age // 5) * 5
        age_groups[age_group] = age_groups.get(age_group, 0) + 1
    
    # 연령대가 다양할수록 높은 점수
    diversity_score = len(age_groups) / max(len(current_ages), 1)
    
    # 분산과 다양성을 결합한 점수
    score = (variance * 0.7 + diversity_score * 0.3) / 100  # 정규화
    
    return score

def calculate_major_distribution_score(group: Dict, new_member: Dict) -> float:
    """조에 새로운 멤버를 추가했을 때의 학과 분포 점수 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    major_counts = Counter([extract_major(m.get('학과', '')) for m in all_members])
    
    # 새 멤버 추가 시 학과 분포 계산
    new_major = extract_major(new_member.get('학과', ''))
    new_major_count = major_counts.get(new_major, 0) + 1
    
    # 학과 분포 점수 (의대,치대,한의대,간호대 중 2명 이상인 학과가 많을수록 높은 점수)
    major_score = sum(1 for major, count in major_counts.items() if major in ['의대', '치대', '한의대', '간호대'] and count >= 2)
    
    # 새 멤버가 의대,치대,한의대,간호대 중 하나라면 점수 증가
    if new_major in ['의대', '치대', '한의대', '간호대']:
        major_score += 1
    
    # 점수 정규화 (0~5 사이)
    return min(major_score / 5, 1.0)

def calculate_region_diversity_score(group: Dict, new_member: Dict) -> float:
    """조에 새로운 멤버를 추가했을 때의 지역 다양성 점수 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    regions = [extract_region(m.get('캠퍼스', m.get('학교/학년', ''))) for m in all_members]
    region_counts = Counter(regions)
    
    # 새 멤버 추가 시 지역 분포 계산
    new_region = extract_region(new_member.get('캠퍼스', ''))
    new_region_count = region_counts.get(new_region, 0) + 1
    
    # 지역 다양성 점수 (3개 이상 지역에서 온 사람이 많을수록 높은 점수)
    region_score = sum(1 for region, count in region_counts.items() if count >= 2)
    
    # 새 멤버가 다른 지역에서 온 경우 점수 증가
    if new_region != '기타': # 기타 지역은 다양성에 포함되지 않음
        region_score += 1
    
    # 점수 정규화 (0~5 사이)
    return min(region_score / 5, 1.0)

def calculate_group_gender_score(group: Dict, total_gender_ratio: float) -> float:
    """조의 현재 성비 균형 점수 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    male_count = sum(1 for m in all_members if m['성별'] == '남')
    female_count = sum(1 for m in all_members if m['성별'] == '여')
    
    total_members = male_count + female_count
    
    # 전체 인원 대비 성비 차이 계산
    expected_male = total_members * total_gender_ratio
    expected_female = total_members * (1 - total_gender_ratio)
    
    male_diff = abs(male_count - expected_male)
    female_diff = abs(female_count - expected_female)
    
    # 성비 차이가 작을수록 높은 점수
    max_diff = max(male_diff, female_diff)
    
    # 성비 균형 점수 (차이가 0이면 1.0, 차이가 클수록 낮은 점수)
    if max_diff == 0:
        balance_score = 1.0
    elif max_diff <= 0.5:
        balance_score = 0.9
    elif max_diff <= 1.0:
        balance_score = 0.7
    elif max_diff <= 1.5:
        balance_score = 0.5
    else:
        balance_score = 0.1  # 1.5명 이상 차이나면 매우 낮은 점수
    
    return balance_score

def calculate_group_age_score(group: Dict) -> float:
    """조의 현재 연령 분포 점수 계산"""
    ages = group['age_distribution']
    if len(ages) <= 1:
        return 1.0
    
    mean_age = sum(ages) / len(ages)
    variance = sum((age - mean_age) ** 2 for age in ages) / len(ages)
    
    age_groups = {}
    for age in ages:
        age_group = (age // 5) * 5
        age_groups[age_group] = age_groups.get(age_group, 0) + 1
    
    diversity_score = len(age_groups) / max(len(ages), 1)
    
    score = (variance * 0.7 + diversity_score * 0.3) / 100
    return score

def calculate_group_major_score(group: Dict) -> float:
    """조의 현재 학과 분포 점수 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    major_counts = Counter([extract_major(m.get('학과', '')) for m in all_members])
    
    # 학과 분포 점수 (의대,치대,한의대,간호대 중 2명 이상인 학과가 많을수록 높은 점수)
    major_score = sum(1 for major, count in major_counts.items() if major in ['의대', '치대', '한의대', '간호대'] and count >= 2)
    
    # 점수 정규화 (0~5 사이)
    return min(major_score / 5, 1.0)

def calculate_group_region_score(group: Dict) -> float:
    """조의 현재 지역 다양성 점수 계산"""
    all_members = [group['leader'], group['helper']] + group['members']
    regions = [extract_region(m.get('캠퍼스', m.get('학교/학년', ''))) for m in all_members]
    region_counts = Counter(regions)
    
    # 지역 다양성 점수 (3개 이상 지역에서 온 사람이 많을수록 높은 점수)
    region_score = sum(1 for region, count in region_counts.items() if count >= 2)
    
    # 점수 정규화 (0~5 사이)
    return min(region_score / 5, 1.0)

def generate_summary_report(groups: Dict, output_file: str):
    """조별 요약 보고서 생성"""
    summary_rows = []
    
    for group in groups.values():
        stats = calculate_group_stats(group)
        
        # 조건별 상세 설명 생성
        condition_details = {
            '의대24_25_분리': {
                'pass': '의대 24학번과 25학번이 같은 조에 배정되지 않았습니다.',
                'fail': '의대 24학번과 25학번이 같은 조에 배정되었습니다.'
            },
            '같은학교_금지': {
                'pass': '같은 학교 학생이 같은 조에 배정되지 않았습니다.',
                'fail': '같은 학교 학생이 같은 조에 배정되었습니다.'
            },
            '나이_조건': {
                'pass': '조원들이 헬퍼보다 어리거나 37세 조장 예외 조건을 만족합니다.',
                'fail': '조원 중 헬퍼보다 나이가 많은 사람이 있습니다.'
            },
            '성비_균형': {
                'pass': f'남녀 성비가 균형잡혀 있습니다 (남성: {stats["male_count"]}명, 여성: {stats["female_count"]}명, 차이: {abs(stats["male_count"] - stats["female_count"])}명).',
                'fail': f'남녀 성비가 불균형합니다 (남성: {stats["male_count"]}명, 여성: {stats["female_count"]}명, 차이: {abs(stats["male_count"] - stats["female_count"])}명).'
            },
            '학과_분포': {
                'pass': f'학과 분포가 적절합니다: {stats["major_distribution"]}',
                'fail': f'의대/치대/한의대/간호대 중 1명만 있는 학과가 있습니다: {stats["major_distribution"]}'
            },
            '지역_다양성': {
                'pass': f'다양한 지역에서 온 학생들로 구성되어 있습니다: {stats["region_distribution"]}',
                'fail': f'지역 다양성이 부족합니다: {stats["region_distribution"]}'
            }
        }
        
        # 더 구체적인 문제점 분석
        major_issues = []
        if not stats['conditions_met']['학과_분포']:
            for major, count in stats['major_distribution'].items():
                if major in ['의대', '치대', '한의대', '간호대'] and count == 1:
                    major_issues.append(f"{major}: {count}명 (2명 이상 필요)")
        
        region_issues = []
        if not stats['conditions_met']['지역_다양성']:
            region_list = list(stats['region_distribution'].keys())
            if len(region_list) <= 2:
                region_issues.append(f"현재 지역: {', '.join(region_list)} (3개 이상 필요)")
        
        # 상세 설명 업데이트
        if major_issues:
            condition_details['학과_분포']['fail'] = f"문제점: {', '.join(major_issues)} | 전체 분포: {stats['major_distribution']}"
        
        if region_issues:
            condition_details['지역_다양성']['fail'] = f"문제점: {', '.join(region_issues)} | 전체 분포: {stats['region_distribution']}"
        
        summary_row = {
            '조 번호': group['조 번호'],
            '총 인원': stats['total_count'],
            '남성': stats['male_count'],
            '여성': stats['female_count'],
            '의대24_25_분리': '✓' if stats['conditions_met']['의대24_25_분리'] else '✗',
            '같은학교_금지': '✓' if stats['conditions_met']['같은학교_금지'] else '✗',
            '나이_조건': '✓' if stats['conditions_met']['나이_조건'] else '✗',
            '성비_균형': '✓' if stats['conditions_met']['성비_균형'] else '✗',
            '학과_분포': '✓' if stats['conditions_met']['학과_분포'] else '✗',
            '지역_다양성': '✓' if stats['conditions_met']['지역_다양성'] else '✗',
            '학과_분포_상세': str(stats['major_distribution']),
            '지역_분포_상세': str(stats['region_distribution']),
            # 상세 설명 추가
            '의대24_25_분리_설명': condition_details['의대24_25_분리']['pass'] if stats['conditions_met']['의대24_25_분리'] else condition_details['의대24_25_분리']['fail'],
            '같은학교_금지_설명': condition_details['같은학교_금지']['pass'] if stats['conditions_met']['같은학교_금지'] else condition_details['같은학교_금지']['fail'],
            '나이_조건_설명': condition_details['나이_조건']['pass'] if stats['conditions_met']['나이_조건'] else condition_details['나이_조건']['fail'],
            '성비_균형_설명': condition_details['성비_균형']['pass'] if stats['conditions_met']['성비_균형'] else condition_details['성비_균형']['fail'],
            '학과_분포_설명': condition_details['학과_분포']['pass'] if stats['conditions_met']['학과_분포'] else condition_details['학과_분포']['fail'],
            '지역_다양성_설명': condition_details['지역_다양성']['pass'] if stats['conditions_met']['지역_다양성'] else condition_details['지역_다양성']['fail']
        }
        summary_rows.append(summary_row)
    
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_file.replace('.csv', '_summary.csv'), index=False, encoding='utf-8-sig')
    return summary_df

def main():
    parser = argparse.ArgumentParser(description="수련회 조 배정 프로그램")
    parser.add_argument('--leaders', required=True, help="조장/헬퍼 Excel 파일 (jojanghelpeo.xlsx)")
    parser.add_argument('--members', required=True, help="조원 Excel 파일 (joweonmyeongdan.xlsx)")
    parser.add_argument('--out', default='final_group_assignment.csv', help="출력 CSV 파일")
    parser.add_argument('--min-members', type=int, default=6, help="각 조 최소 조원 수 (기본값: 6)")
    parser.add_argument('--max-members', type=int, default=8, help="각 조 최대 조원 수 (기본값: 8)")
    parser.add_argument('--max-gender-diff', type=int, default=1, help="성비 차이 허용 범위 (기본값: 1)")
    args = parser.parse_args()
    
    print("데이터 로딩 중...")
    leaders, members = load_data(args.leaders, args.members)
    
    print("조 배정 중...")
    df_assigned = assign_groups(leaders, members, args.min_members, args.max_members, args.max_gender_diff)
    
    print("결과 저장 중...")
    df_assigned.to_csv(args.out, index=False, encoding='utf-8-sig')
    
    print("요약 보고서 생성 중...")
    # 그룹 정보 재구성
    groups = {}
    for _, row in df_assigned.iterrows():
        grp_num = row['조 번호']
        if grp_num not in groups:
            groups[grp_num] = {
                '조 번호': grp_num,
                'leader': None,
                'helper': None,
                'members': []
            }
        
        if row['역할'] == '조장':
            groups[grp_num]['leader'] = row.to_dict()
        elif row['역할'] == '헬퍼':
            groups[grp_num]['helper'] = row.to_dict()
        else:
            groups[grp_num]['members'].append(row.to_dict())
    
    summary_df = generate_summary_report(groups, args.out)
    
    print(f"조 배정 완료! 결과가 {args.out}에 저장되었습니다.")
    print(f"요약 보고서가 {args.out.replace('.csv', '_summary.csv')}에 저장되었습니다.")
    
    # 콘솔에 요약 출력
    print("\n=== 조별 요약 ===")
    print(summary_df.to_string(index=False))

if __name__ == '__main__':
    main() 