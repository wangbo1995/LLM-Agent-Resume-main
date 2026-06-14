"""
端到端集成测试
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from app.core.document_parser import DocumentParser
from app.core.extractor import MetadataExtractor
from app.core.llm_client import LLMClient
from app.core.query_parser import QueryParser
from app.core.vector_store import VectorStoreManager
from app.core.retriever import Retriever
from app.core.filter import HardFilter
from app.core.scorer import Scorer
from app.core.ranker import Ranker
from app.core.analyzer import CandidateAnalyzer
from app.core.result_formatter import ResultFormatter
from app.models.metadata import ResumeMetadata, QueryMetadata


def test_end_to_end_pipeline():
    """测试端到端流程"""
    # 创建临时目录用于向量数据库
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 初始化所有核心组件
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.url/v1",
            "EMBEDDING_API_KEY": "",
            "EMBEDDING_BASE_URL": "",
        }):
            llm_client = LLMClient()
            document_parser = DocumentParser()
            metadata_extractor = MetadataExtractor(llm_client)
            query_parser = QueryParser(llm_client)
            vector_store_manager = VectorStoreManager(persist_directory=temp_dir)
            retriever = Retriever(vector_store_manager)
            hard_filter = HardFilter()
            scorer = Scorer()
            ranker = Ranker()
            candidate_analyzer = CandidateAnalyzer(llm_client)
            result_formatter = ResultFormatter()
        
        # Mock LLM客户端的响应
        with patch.object(llm_client, 'generate_text') as mock_generate:
            # 设置不同的响应
            def generate_text_side_effect(prompt):
                if "简历文本中提取元数据" in prompt:
                    return '{"name": "张三", "email": "zhangsan@example.com", "skills": ["Python", "Django"]}'
                elif "自然语言查询解析" in prompt:
                    return '{"keywords": ["Python"], "required_skills": ["Python"], "min_experience_years": 0}'
                else:
                    return "这是一份详细的候选人评价报告..."
            
            mock_generate.side_effect = generate_text_side_effect
            
            # 1. 文档解析与元数据提取
            resume_text = "张三的简历，拥有5年Python开发经验，熟悉Django框架"
            metadata = metadata_extractor.extract_metadata(resume_text)
            
            # 验证元数据提取
            assert metadata.name == "张三"
            assert metadata.email == "zhangsan@example.com"
            assert "Python" in metadata.skills
            
            # 3. 查询理解
            query_text = "寻找3年以上经验的Python工程师"
            query_metadata = query_parser.parse_query(query_text)

            # 验证查询解析
            assert "Python" in query_metadata.keywords
            assert "Python" in query_metadata.required_skills
            assert query_metadata.min_experience_years == 0

            # Mock OpenAIEmbeddings 以避免真实 API 调用
            with patch('app.core.vector_store.OpenAIEmbeddings') as MockEmbeddings:
                mock_emb = MagicMock()
                mock_emb.embed_documents.return_value = [[0.1]*1024]
                MockEmbeddings.return_value = mock_emb

                # 重新创建依赖 Embedding 的组件
                vsm2 = VectorStoreManager(persist_directory=temp_dir)
                retriever2 = Retriever(vsm2)

                # 2. 向量索引
                resume_id = "resume_001"
                simple_metadata = {
                    "name": "张三",
                    "skills": "Python, Django",
                    "work_experience": '[{"start_date": "2020-01", "end_date": "2025-06"}]',
                    "education": '[{"degree": "本科"}]',
                }
                retriever2.add_resume(resume_id, resume_text, simple_metadata)

                # 4. 语义检索
                retrieved_resumes = retriever2.retrieve(query_metadata)

                # 验证检索结果
                assert len(retrieved_resumes) >= 1
                assert retrieved_resumes[0]["id"] == resume_id

                # 使用 retriever2 替换后续流程中使用的 retriever
                vector_store_manager = vsm2
                retriever = retriever2
            
            # 5. 硬性条件过滤
            filtered_resumes = hard_filter.filter_resumes(retrieved_resumes, query_metadata)
            
            # 验证过滤结果
            assert len(filtered_resumes) >= 1
            
            # 6. 多维度评分
            scored_resumes = scorer.score_resumes(filtered_resumes, query_metadata)
            
            # 验证评分结果
            assert len(scored_resumes) >= 1
            assert "scores" in scored_resumes[0]
            
            # 7. 综合评分与排序
            ranked_resumes = ranker.rank_resumes(scored_resumes, query_metadata)
            
            # 验证排序结果
            assert len(ranked_resumes) >= 1
            assert "rank" in ranked_resumes[0]
            
            # 8. 候选人分析
            analyzed_candidates = candidate_analyzer.analyze_candidates(ranked_resumes, query_metadata)
            
            # 验证分析结果
            assert len(analyzed_candidates) >= 1
            assert "analysis" in analyzed_candidates[0]
            
            # 9. 结果格式化
            formatted_results = result_formatter.format_results(analyzed_candidates, query_metadata)
            
            # 验证格式化结果
            assert formatted_results["total_candidates"] >= 1
            assert len(formatted_results["candidates"]) >= 1
            assert "query" in formatted_results
            assert "summary" in formatted_results
            
            # 验证整个流程完成
            assert formatted_results["candidates"][0]["name"] == "张三"
            assert formatted_results["candidates"][0]["analysis"] == "这是一份详细的候选人评价报告..."
            
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_end_to_end_pipeline()
    print("End-to-end integration test passed!")