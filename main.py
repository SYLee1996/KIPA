import json
import argparse
from time import time

from utils.collections import (process_docx, create_word_document, get_file_paths, read_data, perform_rag,
                               process_gen, prior_process_gen, llm_complete, examine_output_llm, 
                               MODE_SYS_LLM_COMP, MODE_SYS_PRIOR_LLM_COMP,
                               MODE_USR_PURPOSE_LLM_COMP, MODE_USR_METHOD_LLM_COMP, MODE_USR_CONTENT_LLM_COMP,
                               MODE_EXM_OUT_1, MODE_EXM_OUT_2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG pipeline with a Word document.")
    parser.add_argument('--input_json', required=True, help='JSON string containing input data')
    parser.add_argument("--output_docx_path", type=str, required=True, help="Path to the Word document.")
    parser.add_argument("--db_path", type=str)
    parser.add_argument("--rag_top_k", type=int, default=7, help="Number of top nodes to retrieve.")
    args = parser.parse_args()

    start = time()

    try:
        # JSON 파일 읽기
        doc_data_dict = json.loads(args.input_json)

        # print("--------------------------------")
        query = f"{doc_data_dict.get('과제명', '')}. {doc_data_dict.get('관련 정책현안 및 연구의 필요성', '')}. {doc_data_dict.get('연구 목적', '')}"
        nodes = perform_rag(query, args.rag_top_k, args.db_path)
        
        # nodes가 비어있는 경우 처리
        if not nodes:
            print("유사한 자료가 없습니다. 검색 결과가 비어 있습니다.")
            exit(1)  # 프로그램 종료
        
        all_titles = [node.metadata['title'] for node in nodes]
        unique_titles = list(set(all_titles))

        file_path_list = get_file_paths(unique_titles)
        raw_data_dict = {}
        for f_path in file_path_list:
            raw_txt_data = read_data(f_path=f_path)
            raw_data_dict[f_path.split('.txt')[0].split('_')[1:][0]] = raw_txt_data

    except Exception as e:
        print(f"Error: {e}")

    main_text_genetation = {}

    # 연구 필요성
    purpose1 = "관련 정책현안 및 연구의 필요성"
    prompt_kwargs = {'doc_data_dict': doc_data_dict, 'ref_data': nodes, 'top_k': args.rag_top_k, 'purpose': purpose1}
    answer1 = process_gen(max_tokens=2048, temperature=0.3, sys_mode=MODE_SYS_LLM_COMP, **prompt_kwargs)
    doc_data_dict[purpose1] = answer1 # 지우면 안됨
    
    # 연구 목적
    purpose2 = "연구 목적"
    prompt_kwargs = {'doc_data_dict': doc_data_dict, 'ref_data': nodes, 'top_k': args.rag_top_k, 'purpose': purpose2}
    answer2 = process_gen(max_tokens=2048, temperature=0.3, sys_mode=MODE_SYS_LLM_COMP, **prompt_kwargs)
    doc_data_dict[purpose2] = answer2 # 지우면 안됨
    
    
    
    # 선행연구 분석
    prior_list, prior_research_list = prior_process_gen(raw_data_dict=raw_data_dict, sys_mode=MODE_SYS_PRIOR_LLM_COMP)

    # 주요 연구내용
    purpose4 = "주요 연구내용"
    prompt_kwargs = {'doc_data_dict': doc_data_dict, 'ref_data': prior_research_list, 'top_k': None, 'purpose': purpose4}
    answer4 = process_gen(max_tokens=2048, temperature=0.6, sys_mode=MODE_SYS_LLM_COMP, **prompt_kwargs)

    # 연구 추진방법
    purpose5 = "연구 추진방법"
    prompt_kwargs = {'doc_data_dict': doc_data_dict, 'ref_data': answer4, 'top_k': None, 'purpose': purpose5}
    answer5 = process_gen(max_tokens=2048, temperature=0.3, sys_mode=MODE_SYS_LLM_COMP, **prompt_kwargs)
    
    # 기대효과
    purpose6 = "기대효과"
    prompt_kwargs = {'doc_data_dict': doc_data_dict, 'ref_data': answer4, 'top_k': None, 'purpose': purpose6}
    answer6 = process_gen(max_tokens=2048, temperature=0.3, sys_mode=MODE_SYS_LLM_COMP, **prompt_kwargs)
    
    
    main_text_genetation['과제명'] = doc_data_dict['과제명']
    main_text_genetation['연구책임자'] = doc_data_dict['연구책임자']
    main_text_genetation['관련 정책현안 및 연구의 필요성'] = doc_data_dict['관련 정책현안 및 연구의 필요성']
    main_text_genetation['연구 목적'] = answer2
    main_text_genetation['선행연구 현황 및 선행연구와 본연구의 차별성'] = []  # empty list

    answer4 = examine_output_llm(answer4, mode=MODE_EXM_OUT_1)
    answer5 = examine_output_llm(answer5, mode=MODE_EXM_OUT_1)

    main_text_genetation['주요 연구내용'] = answer4
    main_text_genetation['연구 추진방법'] = answer5
    main_text_genetation['기대효과'] = answer6
    
    main_dict = {}
    main_dict['구분'] = "본 연구"
    main_dict['연구목적'] = llm_complete(f"{answer2}", max_tokens=512, temperature=0.3, sys_mode=MODE_SYS_PRIOR_LLM_COMP, usr_mode=MODE_USR_PURPOSE_LLM_COMP)
    main_dict['연구방법'] = llm_complete(f"{answer5}", max_tokens=512, temperature=0.3, sys_mode=MODE_SYS_PRIOR_LLM_COMP, usr_mode=MODE_USR_METHOD_LLM_COMP)
    main_dict['주요연구내용'] = llm_complete(f"{answer4}", max_tokens=512, temperature=0.3, sys_mode=MODE_SYS_PRIOR_LLM_COMP, usr_mode=MODE_USR_CONTENT_LLM_COMP)

    main_dict['연구목적'] = examine_output_llm(main_dict['연구목적'], mode=MODE_EXM_OUT_2)
    main_dict['연구방법'] = examine_output_llm(main_dict['연구방법'], mode=MODE_EXM_OUT_2)
    main_dict['주요연구내용'] = examine_output_llm(main_dict['주요연구내용'], mode=MODE_EXM_OUT_2)


    # Save the document
    doc = create_word_document(main_text_genetation, prior_list, main_dict)
    doc.save(args.output_docx_path)


    end = time()
    print(end-start)