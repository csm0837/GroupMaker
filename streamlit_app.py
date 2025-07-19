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
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    .group-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #667eea;
    }
    .condition-pass {
        color: #28a745;
        font-weight: bold;
        background: rgba(40, 167, 69, 0.1);
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
    }
    .condition-fail {
        color: #dc3545;
        font-weight: bold;
        background: rgba(220, 53, 69, 0.1);
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
    }
    .download-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 25px;
        text-decoration: none;
        display: inline-block;
        margin: 0.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .download-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    .stats-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
    .member-info {
        background: rgba(248, 249, 250, 0.8);
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid #667eea;
    }
    .leader-info {
        background: rgba(255, 193, 7, 0.1);
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid #ffc107;
    }
    .helper-info {
        background: rgba(23, 162, 184, 0.1);
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid #17a2b8;
    }
    .progress-container {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        border: 1px solid #e9ecef;
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
            # 진행 상황 표시
            progress_container = st.container()
            
            with progress_container:
                st.markdown("""
                <div class="progress-container">
                    <h4>🔄 조 배정 진행 상황</h4>
                </div>
                """, unsafe_allow_html=True)
            
            # 1단계: 파일 처리
            with progress_container:
                with st.spinner("📁 파일 처리 중..."):
                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_leaders:
                        tmp_leaders.write(leaders_file.getvalue())
                        leaders_path = tmp_leaders.name
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_members:
                        tmp_members.write(members_file.getvalue())
                        members_path = tmp_members.name
                    
                    st.success("✅ 파일 처리 완료")
            
            # 2단계: 데이터 로드
            with progress_container:
                with st.spinner("📊 데이터 로드 중..."):
                    leaders, members = load_data(leaders_path, members_path)
                    st.success(f"✅ 데이터 로드 완료 (조장/헬퍼: {len(leaders)}명, 조원: {len(members)}명)")
            
            # 3단계: 조 배정 실행
            with progress_container:
                with st.spinner("🎯 조 배정 알고리즘 실행 중..."):
                    df_assigned = assign_groups(leaders, members, min_members, max_members, max_gender_diff)
                    st.success("✅ 조 배정 완료")
            
            # 4단계: 결과 처리
            with progress_container:
                with st.spinner("📋 결과 정리 중..."):
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
                    st.success("✅ 결과 정리 완료")
            
            # 5단계: 임시 파일 정리
            with progress_container:
                with st.spinner("🧹 임시 파일 정리 중..."):
                    os.unlink(leaders_path)
                    os.unlink(members_path)
                    st.success("✅ 임시 파일 정리 완료")
            
            # 진행 상황 완료 표시
            with progress_container:
                st.markdown("""
                <div class="progress-container" style="background: rgba(40, 167, 69, 0.1); border-left: 4px solid #28a745;">
                    <h4>🎉 조 배정이 성공적으로 완료되었습니다!</h4>
                </div>
                """, unsafe_allow_html=True)
            
            # 결과 표시
            display_results(groups, summary_df, df_assigned, min_members, max_members, max_gender_diff)
                
        except Exception as e:
            st.error(f"조 배정 중 오류가 발생했습니다: {str(e)}")
            st.exception(e)

def display_results(groups, summary_df, df_assigned, min_members, max_members, max_gender_diff):
    """결과 표시"""
    
    # 요약 정보
    st.header("📊 배정 요약")
    
    # 메트릭 카드 스타일로 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📋 총 조 수</h3>
            <h2 style="color: #667eea;">{len(groups)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_members = sum(len(group['members']) for group in groups.values())
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 총 조원 수</h3>
            <h2 style="color: #28a745;">{total_members}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📏 조원 범위</h3>
            <h2 style="color: #ffc107;">{min_members}-{max_members}명</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_members = total_members / len(groups) if groups else 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 평균 조원 수</h3>
            <h2 style="color: #17a2b8;">{avg_members:.1f}명</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # 조건별 만족 현황
    st.header("✅ 조건별 만족 현황")
    
    conditions = ['의대24_25_분리', '같은학교_금지', '나이_조건', '성비_균형', '학과_분포', '지역_다양성']
    condition_names = {
        '의대24_25_분리': '의대 24/25학번 분리',
        '같은학교_금지': '같은 학교 금지',
        '나이_조건': '나이 조건',
        '성비_균형': '성비 균형',
        '학과_분포': '학과 분포',
        '지역_다양성': '지역 다양성'
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        for condition in conditions[:3]:
            pass_count = sum(1 for _, row in summary_df.iterrows() if row[condition] == '✓')
            total_count = len(summary_df)
            percentage = pass_count/total_count*100 if total_count > 0 else 0
            
            # 조건별 색상 설정
            if percentage >= 80:
                color = "#28a745"
                bg_color = "rgba(40, 167, 69, 0.1)"
            elif percentage >= 60:
                color = "#ffc107"
                bg_color = "rgba(255, 193, 7, 0.1)"
            else:
                color = "#dc3545"
                bg_color = "rgba(220, 53, 69, 0.1)"
            
            st.markdown(f"""
            <div class="stats-card" style="border-left-color: {color}; background: {bg_color};">
                <h4>{condition_names[condition]}</h4>
                <h3 style="color: {color};">{pass_count}/{total_count}</h3>
                <p style="color: {color}; font-weight: bold;">{percentage:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        for condition in conditions[3:]:
            pass_count = sum(1 for _, row in summary_df.iterrows() if row[condition] == '✓')
            total_count = len(summary_df)
            percentage = pass_count/total_count*100 if total_count > 0 else 0
            
            # 조건별 색상 설정
            if percentage >= 80:
                color = "#28a745"
                bg_color = "rgba(40, 167, 69, 0.1)"
            elif percentage >= 60:
                color = "#ffc107"
                bg_color = "rgba(255, 193, 7, 0.1)"
            else:
                color = "#dc3545"
                bg_color = "rgba(220, 53, 69, 0.1)"
            
            st.markdown(f"""
            <div class="stats-card" style="border-left-color: {color}; background: {bg_color};">
                <h4>{condition_names[condition]}</h4>
                <h3 style="color: {color};">{pass_count}/{total_count}</h3>
                <p style="color: {color}; font-weight: bold;">{percentage:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 요약 테이블
    st.header("📋 조별 요약 통계")
    
    # 툴팁 스타일 추가
    st.markdown("""
    <style>
        .tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 350px;
            background-color: #333;
            color: #fff;
            text-align: left;
            border-radius: 8px;
            padding: 12px;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 50%;
            margin-left: -175px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 13px;
            line-height: 1.5;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            white-space: pre-wrap;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        .condition-cell {
            cursor: help;
            padding: 8px 12px;
            border-radius: 6px;
            display: inline-block;
            min-width: 40px;
            text-align: center;
            font-weight: bold;
            margin: 2px;
        }
        .condition-pass-cell {
            background: rgba(40, 167, 69, 0.15);
            color: #28a745;
            border: 2px solid #28a745;
        }
        .condition-fail-cell {
            background: rgba(220, 53, 69, 0.15);
            color: #dc3545;
            border: 2px solid #dc3545;
        }
        .summary-table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        .summary-table th, .summary-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: center;
        }
        .summary-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .summary-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .summary-table tr:hover {
            background-color: #f0f0f0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 요약 테이블을 HTML로 생성하여 툴팁 포함
    table_html = """
    <table class="summary-table">
        <thead>
            <tr>
                <th>조 번호</th>
                <th>총 인원</th>
                <th>남성</th>
                <th>여성</th>
    """
    
    # 조건별 헤더 추가
    for condition in conditions:
        table_html += f'<th>{condition_names[condition]}</th>'
    
    table_html += """
            </tr>
        </thead>
        <tbody>
    """
    
    # 각 조별 데이터 추가
    for _, row in summary_df.iterrows():
        table_html += f"""
            <tr>
                <td><strong>조 {row['조 번호']}</strong></td>
                <td>{row['총 인원']}</td>
                <td>{row['남성']}</td>
                <td>{row['여성']}</td>
        """
        
        # 조건별 상태와 툴팁 추가
        for condition in conditions:
            condition_status = row[condition]
            detail_col = f"{condition}_설명"
            detail_info = row.get(detail_col, "상세 정보 없음")
            
            status_class = "condition-pass-cell" if condition_status == '✓' else "condition-fail-cell"
            status_icon = "✅" if condition_status == '✓' else "❌"
            
            table_html += f"""
                <td>
                    <div class="tooltip">
                        <span class="condition-cell {status_class}">
                            {status_icon}
                        </span>
                        <span class="tooltiptext">
                            <strong>조 {row['조 번호']} - {condition_names[condition]}</strong><br><br>
                            {detail_info}
                        </span>
                    </div>
                </td>
            """
        
        table_html += "</tr>"
    
    table_html += """
        </tbody>
    </table>
    """
    
    # 테이블 표시
    st.markdown(table_html, unsafe_allow_html=True)
    
    # 사용법 안내
    st.info("💡 **사용법**: 각 조건의 ✅ 또는 ❌ 아이콘에 마우스를 올리면 상세 정보를 확인할 수 있습니다.")
    
    # 조별 상세 정보
    st.header("👥 조별 상세 정보")
    
    for group_num in sorted(groups.keys()):
        group = groups[group_num]
        
        with st.expander(f"조 {group_num} (총 {len(group['members'])}명)", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("👥 조원 목록")
                
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
                
                st.markdown(f"""
                <div class="leader-info">
                    {leader_info}
                </div>
                """, unsafe_allow_html=True)
                
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
                
                st.markdown(f"""
                <div class="helper-info">
                    {helper_info}
                </div>
                """, unsafe_allow_html=True)
                
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
                    
                    st.markdown(f"""
                    <div class="member-info">
                        {member_info}
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                st.subheader("📊 조 통계")
                stats = calculate_group_stats(group)
                
                # 통계 카드들
                st.markdown(f"""
                <div class="stats-card">
                    <h4>👥 총 인원</h4>
                    <h3 style="color: #667eea;">{stats['total_count']}명</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="stats-card">
                    <h4>👨 남성</h4>
                    <h3 style="color: #007bff;">{stats['male_count']}명</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="stats-card">
                    <h4>👩 여성</h4>
                    <h3 style="color: #e83e8c;">{stats['female_count']}명</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # 조건 만족 여부
                st.subheader("✅ 조건 만족")
                for condition in conditions:
                    status = "✅" if stats['conditions_met'][condition] else "❌"
                    condition_name = condition_names[condition]
                    
                    if stats['conditions_met'][condition]:
                        st.markdown(f"""
                        <div class="condition-pass">
                            {status} {condition_name}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="condition-fail">
                            {status} {condition_name}
                        </div>
                        """, unsafe_allow_html=True)
    
    # 다운로드 섹션
    st.header("💾 결과 다운로드")
    
    st.markdown("""
    <div class="progress-container">
        <h4>💾 다운로드 옵션</h4>
        <p>조 배정 결과를 다양한 형식으로 다운로드할 수 있습니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 엑셀 파일 다운로드 (전체 결과)
        excel_href = create_excel_download(df_assigned, summary_df)
        st.markdown(excel_href, unsafe_allow_html=True)
        st.info("📊 엑셀 파일에는 조배정결과, 조별요약, 상세정보 시트가 포함됩니다.")
    
    with col2:
        # 조 배정 결과 다운로드 (CSV)
        csv = df_assigned.to_csv(index=False, encoding='utf-8-sig')
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="조배정결과.csv" class="download-button">📊 조 배정 결과 다운로드 (CSV)</a>'
        st.markdown(href, unsafe_allow_html=True)
        st.info("📋 CSV 형식으로 조 배정 결과를 다운로드합니다.")
    
    with col3:
        # 요약 보고서 다운로드 (CSV)
        csv_summary = summary_df.to_csv(index=False, encoding='utf-8-sig')
        b64_summary = base64.b64encode(csv_summary.encode()).decode()
        href_summary = f'<a href="data:file/csv;base64,{b64_summary}" download="조별요약.csv" class="download-button">📋 요약 보고서 다운로드 (CSV)</a>'
        st.markdown(href_summary, unsafe_allow_html=True)
        st.info("📈 조별 요약 통계를 CSV 형식으로 다운로드합니다.")

if __name__ == "__main__":
    main() 