#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수련회 조 배정 Streamlit 애플리케이션
Streamlit을 사용한 웹 인터페이스
"""

import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import random
import tempfile
import os
from datetime import datetime
import json
import base64
from io import BytesIO

# 기존 조 배정 로직 import
from camp_group_assignment import (
    load_data, canonical_school, extract_major, extract_region,
    can_assign_to_group, calculate_group_stats, assign_groups, generate_summary_report
)

# 페이지 설정
st.set_page_config(
    page_title="수련회 조 배정 시스템",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 추가
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .group-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .condition-pass {
        color: #28a745;
        font-weight: bold;
    }
    .condition-fail {
        color: #dc3545;
        font-weight: bold;
    }
    .download-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        text-decoration: none;
        display: inline-block;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def create_excel_download(df_assigned, summary_df):
    """엑셀 파일 생성 및 다운로드 링크 생성"""
    
    # 엑셀 파일 생성
    with BytesIO() as buffer:
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # 조 배정 결과 시트
            df_assigned.to_excel(writer, sheet_name='조배정결과', index=False)
            
            # 요약 보고서 시트
            summary_df.to_excel(writer, sheet_name='조별요약', index=False)
            
            # 조별 상세 정보 시트 생성
            detailed_data = []
            for _, row in df_assigned.iterrows():
                # 역할에 따라 다른 컬럼명 사용
                if row['역할'] in ['조장', '헬퍼']:
                    # 조장/헬퍼는 '학교/학년' 컬럼 사용
                    school_info = row.get('학교', '')
                else:
                    # 조원은 '지역' 컬럼 사용
                    school_info = row.get('지역', '')
                
                detailed_row = {
                    '조 번호': row['조 번호'],
                    '역할': row['역할'],
                    '이름': row['이름'],
                    '성별': row['성별'],
                    '나이': row['나이'],
                    '학과': row['학과'],
                    '학교/지역': school_info,  # 통합된 컬럼명
                    '전화번호': row.get('전화번호', ''),
                    '학번': row.get('학번', ''),
                    '트랙': row.get('트랙', 'EBS')
                }
                detailed_data.append(detailed_row)
            
            detailed_df = pd.DataFrame(detailed_data)
            detailed_df.to_excel(writer, sheet_name='상세정보', index=False)
        
        buffer.seek(0)
        excel_data = buffer.read()
    
    # 다운로드 링크 생성
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="수련회_조배정결과.xlsx" class="download-button">📊 엑셀 파일 다운로드 (전체 결과)</a>'
    return href

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown("""
    <div class="main-header">
        <h1>👥 수련회 조 배정 시스템</h1>
        <p>조장/헬퍼 명단과 조원 명단을 업로드하여 자동으로 조를 배정하세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바 설정
    with st.sidebar:
        st.header("⚙️ 조 배정 설정")
        
        min_members = st.slider(
            "각 조 최소 인원 (조장/헬퍼 제외)",
            min_value=3,
            max_value=10,
            value=6,
            help="조장과 헬퍼를 제외한 최소 조원 수"
        )
        
        max_members = st.slider(
            "각 조 최대 인원 (조장/헬퍼 제외)",
            min_value=5,
            max_value=12,
            value=8,
            help="조장과 헬퍼를 제외한 최대 조원 수"
        )
        
        if min_members > max_members:
            st.error("최소 인원은 최대 인원보다 작거나 같아야 합니다.")
            return
        
        st.info(f"조원 범위: {min_members}-{max_members}명")
        
        # 성비 설정
        st.subheader("🎯 성비 설정")
        
        max_gender_diff = st.slider(
            "성비 차이 허용 범위",
            min_value=0,
            max_value=3,
            value=1,
            help="전체 데이터 성비 대비 차이나는 인원수 허용 범위 (명)"
        )
        
        st.info(f"성비 설정: 전체 데이터 성비 기준, 최대 {max_gender_diff}명 차이 허용")
    
    # 파일 업로드
    st.header("📁 파일 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("조장/헬퍼 명단")
        leaders_file = st.file_uploader(
            "조장/헬퍼 Excel 파일 업로드",
            type=['xlsx', 'xls'],
            help="조장과 헬퍼 정보가 포함된 Excel 파일"
        )
        
        if leaders_file:
            st.success(f"✅ {leaders_file.name} 업로드 완료")
    
    with col2:
        st.subheader("조원 명단")
        members_file = st.file_uploader(
            "조원 Excel 파일 업로드",
            type=['xlsx', 'xls'],
            help="조원 정보가 포함된 Excel 파일"
        )
        
        if members_file:
            st.success(f"✅ {members_file.name} 업로드 완료")
    
    # 조 배정 실행
    if st.button("🚀 조 배정 시작", type="primary", use_container_width=True):
        if leaders_file is None or members_file is None:
            st.error("조장/헬퍼 명단과 조원 명단을 모두 업로드해주세요.")
            return
        
        try:
            with st.spinner("조 배정을 진행하고 있습니다..."):
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_leaders:
                    tmp_leaders.write(leaders_file.getvalue())
                    leaders_path = tmp_leaders.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_members:
                    tmp_members.write(members_file.getvalue())
                    members_path = tmp_members.name
                
                # 데이터 로드
                leaders, members = load_data(leaders_path, members_path)
                
                # 조 배정 실행
                df_assigned = assign_groups(leaders, members, min_members, max_members, max_gender_diff)
                
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
                
                # 요약 보고서 생성
                summary_df = generate_summary_report(groups, "temp_output.csv")
                
                # 임시 파일 삭제
                os.unlink(leaders_path)
                os.unlink(members_path)
                
                # 결과 표시
                display_results(groups, summary_df, df_assigned, min_members, max_members, max_gender_diff)
                
        except Exception as e:
            st.error(f"조 배정 중 오류가 발생했습니다: {str(e)}")
            st.exception(e)

def display_results(groups, summary_df, df_assigned, min_members, max_members, max_gender_diff):
    """결과 표시"""
    
    st.success("🎉 조 배정이 완료되었습니다!")
    
    # 요약 정보
    st.header("📊 배정 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 조 수", len(groups))
    
    with col2:
        total_members = sum(len(group['members']) for group in groups.values())
        st.metric("총 조원 수", total_members)
    
    with col3:
        st.metric("조원 범위", f"{min_members}-{max_members}명")
    
    with col4:
        avg_members = total_members / len(groups) if groups else 0
        st.metric("평균 조원 수", f"{avg_members:.1f}명")
    
    # 요약 테이블
    st.subheader("📋 조별 요약 통계")
    
    # 요약 데이터프레임 표시
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True
    )
    
    # 조건별 만족 현황
    st.subheader("✅ 조건별 만족 현황")
    
    conditions = ['의대24_25_분리', '같은학교_금지', '나이_조건', '성비_균형', '학과_분포', '지역_다양성']
    
    col1, col2 = st.columns(2)
    
    with col1:
        for condition in conditions[:3]:
            pass_count = sum(1 for _, row in summary_df.iterrows() if row[condition] == '✓')
            total_count = len(summary_df)
            st.metric(
                condition.replace('_', ' '),
                f"{pass_count}/{total_count}",
                f"{pass_count/total_count*100:.1f}%"
            )
    
    with col2:
        for condition in conditions[3:]:
            pass_count = sum(1 for _, row in summary_df.iterrows() if row[condition] == '✓')
            total_count = len(summary_df)
            st.metric(
                condition.replace('_', ' '),
                f"{pass_count}/{total_count}",
                f"{pass_count/total_count*100:.1f}%"
            )
    
    # 조별 상세 정보
    st.header("👥 조별 상세 정보")
    
    for group_num in sorted(groups.keys()):
        group = groups[group_num]
        
        with st.expander(f"조 {group_num} (총 {len(group['members'])}명)"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("조원 목록")
                
                # 조장
                leader = group['leader']
                phone = leader.get('전화번호', '')
                
                # 조장 정보 구성
                leader_school = leader.get('학교', '')
                leader_major = leader.get('학과', '')
                
                leader_info = f"**👑 조장**: {leader['이름']} ({leader['성별']}, {leader['나이']}세)"
                if leader_school:
                    leader_info += f" | 📍 {leader_school}"
                if leader_major:
                    leader_info += f" | 🎓 {leader_major}"
                if phone:
                    leader_info += f" | 📞 {phone}"
                
                st.markdown(leader_info)
                
                # 헬퍼
                helper = group['helper']
                phone = helper.get('전화번호', '')
                
                # 헬퍼 정보 구성
                helper_school = helper.get('학교', '')
                helper_major = helper.get('학과', '')
                
                helper_info = f"**⭐ 헬퍼**: {helper['이름']} ({helper['성별']}, {helper['나이']}세)"
                if helper_school:
                    helper_info += f" | 📍 {helper_school}"
                if helper_major:
                    helper_info += f" | 🎓 {helper_major}"
                if phone:
                    helper_info += f" | 📞 {phone}"
                
                st.markdown(helper_info)
                
                # 조원들
                for i, member in enumerate(group['members'], 1):
                    phone = member.get('전화번호', '')
                    
                    # 지역, 캠퍼스, 학과, 학년 정보 구성
                    region = member.get('지역', '')
                    campus = member.get('캠퍼스', '')
                    major = member.get('학과', '')
                    grade = member.get('학년', '')
                    
                    # 정보 조합 (예: 강원 연세원주 예2)
                    location_info = f"{region} {campus}".strip()
                    academic_info = f"{major}{grade}".strip()
                    
                    # 전체 정보 표시
                    member_info = f"**{i}.** {member['이름']} ({member['성별']}, {member['나이']}세)"
                    if location_info:
                        member_info += f" | 📍 {location_info}"
                    if academic_info:
                        member_info += f" | 🎓 {academic_info}"
                    if phone:
                        member_info += f" | 📞 {phone}"
                    
                    st.markdown(member_info)
            
            with col2:
                st.subheader("조 통계")
                stats = calculate_group_stats(group)
                
                st.metric("총 인원", stats['total_count'])
                st.metric("남성", stats['male_count'])
                st.metric("여성", stats['female_count'])
                
                # 조건 만족 여부
                st.subheader("조건 만족")
                for condition in conditions:
                    status = "✅" if stats['conditions_met'][condition] else "❌"
                    st.markdown(f"{status} {condition.replace('_', ' ')}")
    
    # 다운로드 섹션
    st.header("📥 결과 다운로드")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 엑셀 파일 다운로드 (전체 결과)
        excel_href = create_excel_download(df_assigned, summary_df)
        st.markdown(excel_href, unsafe_allow_html=True)
    
    with col2:
        # 조 배정 결과 다운로드 (CSV)
        csv = df_assigned.to_csv(index=False, encoding='utf-8-sig')
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="조배정결과.csv" class="download-button">📊 조 배정 결과 다운로드 (CSV)</a>'
        st.markdown(href, unsafe_allow_html=True)
    
    with col3:
        # 요약 보고서 다운로드 (CSV)
        csv_summary = summary_df.to_csv(index=False, encoding='utf-8-sig')
        b64_summary = base64.b64encode(csv_summary.encode()).decode()
        href_summary = f'<a href="data:file/csv;base64,{b64_summary}" download="조별요약.csv" class="download-button">📋 요약 보고서 다운로드 (CSV)</a>'
        st.markdown(href_summary, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 