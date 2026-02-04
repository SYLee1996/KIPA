from uuid import uuid4
from subprocess import CalledProcessError, run
import json
import streamlit as st

if 'progressing' not in st.session_state:
    st.session_state.progressing = False

st.header('한국행정연구원 연구계획서 초안 생성 AI')

# 사용자 입력 필드
task_name = st.text_input("과제명", placeholder="예시) 돌봄 로봇의 사용자 경험 개선을 위한 인터페이스 디자인 연구")
research_leader = st.text_input("연구책임자", placeholder="예시) 홍길동")
policy_need = st.text_area("관련 정책현안 및 연구의 필요성", 
                           placeholder="예시) 기존 사회적 수용성을 저해하는 돌봄 로봇의 낙후된 인터페이스 디자인을 개선하기 위한 연구가 필요함.")
research_goal = st.text_area("연구 목적", 
                             placeholder="예시) 본 연구는 돌봄 로봇의 사용자 경험을 향상시키고 사회적 수용성을 높이고자 인터페이스 디자인을 개선하는 것을 목적으로 한다.")

# 입력 완료 버튼
if task_name and research_leader and policy_need and research_goal:
    if not st.session_state.progressing:
        button = st.button("Submit")
        if button:
            st.session_state.progressing = True
            st.rerun()
    else:
        session_name = uuid4()

        # 딕셔너리 형태로 입력 데이터 구성
        input_data = {
            '과제명': task_name,
            '연구책임자': research_leader,
            '관련 정책현안 및 연구의 필요성': policy_need,
            '연구 목적': research_goal,
        }

        # JSON 문자열로 변환
        input_data_str = json.dumps(input_data, ensure_ascii=False)

        try:
            with st.spinner('Wait for it...'):
                # JSON 데이터를 안전하게 subprocess로 전달
                result = run(
                    [
                        "python", "main.py",
                        "--input_json", input_data_str,
                        "--output_docx_path", "result.docx",
                        "--db_path", "utils/draft_gen.db"
                    ],
                    capture_output=True,  # 출력 캡처
                    text=True,
                    check=False  # 에러 발생 시에도 종료하지 않음
                )

                # 결과 확인
                if result.returncode != 0:
                    if "검색 결과가 비어 있습니다" in result.stdout:
                        st.error("유사한 자료가 없습니다. 검색 결과가 비어 있습니다.", icon="❌")
                    else:
                        st.error(f"오류 발생: {result.stderr}", icon="🚨")
                else:
                    # 결과 파일 다운로드 버튼
                    with open('result.docx', 'rb') as f:
                        st.download_button(
                            label="Download RFP draft",
                            data=f,
                            file_name="RFP_DRAFT.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                st.session_state.progressing = False
                button = None

        except CalledProcessError as e:
            st.error(f'RFP generation encountered unknown error: {str(e)}', icon="🚨")
else:
    st.info("모든 입력 필드를 채워주세요.")
