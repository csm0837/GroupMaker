#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수련회 조 배정 웹 애플리케이션
Flask를 사용한 웹 인터페이스
"""

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import random
import tempfile
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
import json

# 기존 조 배정 로직 import
from camp_group_assignment import (
    load_data, canonical_school, extract_major, extract_region,
    can_assign_to_group, calculate_group_stats, assign_groups, generate_summary_report
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 실제 운영시에는 환경변수로 설정

# 업로드 폴더 설정
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

def allowed_file(filename):
    """파일 확장자 검증"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """파일 업로드 처리"""
    if 'leaders_file' not in request.files or 'members_file' not in request.files:
        flash('두 개의 파일을 모두 업로드해주세요.')
        return redirect(request.url)
    
    leaders_file = request.files['leaders_file']
    members_file = request.files['members_file']
    
    # 파일명 검증
    if leaders_file.filename == '' or members_file.filename == '':
        flash('파일을 선택해주세요.')
        return redirect(request.url)
    
    if not (allowed_file(leaders_file.filename) and allowed_file(members_file.filename)):
        flash('Excel 파일(.xlsx, .xls)만 업로드 가능합니다.')
        return redirect(request.url)
    
    # 인원 범위 설정 가져오기
    try:
        min_members = int(request.form.get('min_members', 6))
        max_members = int(request.form.get('max_members', 8))
        
        # 범위 검증
        if min_members < 3 or min_members > 10:
            flash('최소 인원은 3-10명 사이여야 합니다.')
            return redirect(request.url)
        
        if max_members < 5 or max_members > 12:
            flash('최대 인원은 5-12명 사이여야 합니다.')
            return redirect(request.url)
        
        if min_members > max_members:
            flash('최소 인원은 최대 인원보다 작거나 같아야 합니다.')
            return redirect(request.url)
            
    except ValueError:
        flash('인원 범위 설정이 올바르지 않습니다.')
        return redirect(request.url)
    
    try:
        # 고유한 세션 ID 생성
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        # 파일 저장
        leaders_path = os.path.join(session_folder, 'leaders.xlsx')
        members_path = os.path.join(session_folder, 'members.xlsx')
        
        leaders_file.save(leaders_path)
        members_file.save(members_path)
        
        # 조 배정 실행 (인원 범위 전달)
        result = process_group_assignment(leaders_path, members_path, session_id, min_members, max_members)
        
        if result['success']:
            return redirect(url_for('results', session_id=session_id))
        else:
            flash(f'조 배정 중 오류가 발생했습니다: {result["error"]}')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f'파일 처리 중 오류가 발생했습니다: {str(e)}')
        return redirect(url_for('index'))

def process_group_assignment(leaders_path, members_path, session_id, min_members, max_members):
    """조 배정 처리"""
    try:
        # 데이터 로드
        leaders, members = load_data(leaders_path, members_path)
        
        # 조 배정 실행
        df_assigned = assign_groups(leaders, members, min_members, max_members)
        
        # 결과 저장
        result_folder = os.path.join(RESULT_FOLDER, session_id)
        os.makedirs(result_folder, exist_ok=True)
        
        output_path = os.path.join(result_folder, 'final_group_assignment.csv')
        df_assigned.to_csv(output_path, index=False, encoding='utf-8-sig')
        
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
        summary_df = generate_summary_report(groups, output_path)
        
        # JSON 형태로 결과 저장 (웹 표시용)
        result_data = {
            'session_id': session_id,
            'total_groups': len(groups),
            'total_members': len(members),
            'groups': {},
            'summary': summary_df.to_dict('records'),
            'settings': {
                'min_members': min_members,
                'max_members': max_members
            }
        }
        
        for group in groups.values():
            result_data['groups'][group['조 번호']] = {
                '조 번호': group['조 번호'],
                'leader': group['leader'],
                'helper': group['helper'],
                'members': group['members'],
                'stats': calculate_group_stats(group)
            }
        
        with open(os.path.join(result_folder, 'result.json'), 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        return {'success': True, 'session_id': session_id}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error details: {error_details}")
        return {'success': False, 'error': str(e)}

@app.route('/results/<session_id>')
def results(session_id):
    """결과 페이지"""
    result_folder = os.path.join(RESULT_FOLDER, session_id)
    result_json_path = os.path.join(result_folder, 'result.json')
    
    if not os.path.exists(result_json_path):
        flash('결과를 찾을 수 없습니다.')
        return redirect(url_for('index'))
    
    try:
        with open(result_json_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        return render_template('results.html', result=result_data)
        
    except Exception as e:
        flash(f'결과 로딩 중 오류가 발생했습니다: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download/<session_id>/<file_type>')
def download_file(session_id, file_type):
    """파일 다운로드"""
    result_folder = os.path.join(RESULT_FOLDER, session_id)
    
    if file_type == 'results':
        file_path = os.path.join(result_folder, 'final_group_assignment.csv')
        filename = '조배정결과.csv'
    elif file_type == 'summary':
        file_path = os.path.join(result_folder, 'final_group_assignment_summary.csv')
        filename = '조별요약.csv'
    else:
        flash('잘못된 파일 타입입니다.')
        return redirect(url_for('results', session_id=session_id))
    
    if not os.path.exists(file_path):
        flash('파일을 찾을 수 없습니다.')
        return redirect(url_for('results', session_id=session_id))
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/api/validate_files', methods=['POST'])
def validate_files():
    """파일 유효성 검사 API"""
    if 'leaders_file' not in request.files or 'members_file' not in request.files:
        return jsonify({'valid': False, 'message': '두 개의 파일을 모두 업로드해주세요.'})
    
    leaders_file = request.files['leaders_file']
    members_file = request.files['members_file']
    
    # 파일명 검증
    if leaders_file.filename == '' or members_file.filename == '':
        return jsonify({'valid': False, 'message': '파일을 선택해주세요.'})
    
    if not (allowed_file(leaders_file.filename) and allowed_file(members_file.filename)):
        return jsonify({'valid': False, 'message': 'Excel 파일(.xlsx, .xls)만 업로드 가능합니다.'})
    
    try:
        # 임시 파일로 저장하여 데이터 검증
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_leaders:
            leaders_file.save(tmp_leaders.name)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_members:
            members_file.save(tmp_members.name)
        
        # 데이터 로드 테스트
        leaders, members = load_data(tmp_leaders.name, tmp_members.name)
        
        # 임시 파일 삭제
        os.unlink(tmp_leaders.name)
        os.unlink(tmp_members.name)
        
        return jsonify({
            'valid': True,
            'message': '파일이 유효합니다.',
            'leaders_count': len(leaders),
            'members_count': len(members)
        })
        
    except Exception as e:
        return jsonify({'valid': False, 'message': f'파일 검증 중 오류: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port) 