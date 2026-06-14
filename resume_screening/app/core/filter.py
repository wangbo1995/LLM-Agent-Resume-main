from typing import List, Dict, Any
import json
from app.models.metadata import ResumeMetadata, QueryMetadata
from loguru import logger


class HardFilter:
    """
    硬性条件过滤器，用于根据硬性条件过滤简历
    """

    def __init__(self):
        """
        初始化硬性条件过滤器
        """
        logger.info("Initialized HardFilter")

    @staticmethod
    def _parse_list_field(value: Any) -> list:
        """
        将字符串类型的字段解析为列表，支持 JSON 数组和逗号分隔两种格式。

        Args:
            value: 原始字段值（可能是 None / list / str）

        Returns:
            list: 解析后的列表
        """
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            # 优先尝试 JSON 解析（处理 '["a","b"]' 或 '[{"k":"v"}]' 格式）
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # 回退：逗号分隔的纯文本
            return [item.strip() for item in stripped.split(',') if item.strip()]
        return []

    def filter_resumes(self, resumes: List[Dict[str, Any]], query_metadata: QueryMetadata) -> List[Dict[str, Any]]:
        """
        根据查询元数据过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            query_metadata (QueryMetadata): 查询元数据
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        try:
            # 添加日志来调试问题
            logger.info(f"Resume filter input type: {type(resumes)}")
            logger.info(f"Resume filter input length: {len(resumes) if isinstance(resumes, list) else 'N/A'}")
            if isinstance(resumes, list) and resumes:
                logger.info(f"First resume type: {type(resumes[0])}")
                logger.info(f"First resume content: {resumes[0]}")
                
                # 过滤掉非字典类型的简历
                resumes = [r for r in resumes if isinstance(r, dict)]
                logger.info(f"Filtered non-dict resumes, remaining: {len(resumes)}")
                
            filtered_resumes = resumes.copy() if isinstance(resumes, list) else []
            
            # 根据所需经验年限过滤
            if query_metadata.min_experience_years is not None and isinstance(filtered_resumes, list):
                logger.info(f"Before experience filter: {len(filtered_resumes)}")
                filtered_resumes = self._filter_by_experience(filtered_resumes, query_metadata.min_experience_years)
                logger.info(f"After experience filter: {len(filtered_resumes)}")
            
            # 根据所需学历过滤
            if query_metadata.required_education is not None and isinstance(filtered_resumes, list):
                logger.info(f"Before education filter: {len(filtered_resumes)}")
                filtered_resumes = self._filter_by_education(filtered_resumes, query_metadata.required_education)
                logger.info(f"After education filter: {len(filtered_resumes)}")
            
            # 根据所需技能过滤
            if query_metadata.required_skills and isinstance(filtered_resumes, list):
                logger.info(f"Before skills filter: {len(filtered_resumes)}")
                filtered_resumes = self._filter_by_skills(filtered_resumes, query_metadata.required_skills)
                logger.info(f"After skills filter: {len(filtered_resumes)}")
            
            # 根据工作地点过滤
            if query_metadata.locations and isinstance(filtered_resumes, list):
                logger.info(f"Before locations filter: {len(filtered_resumes)}")
                filtered_resumes = self._filter_by_locations(filtered_resumes, query_metadata.locations)
                logger.info(f"After locations filter: {len(filtered_resumes)}")
            
            # 根据语言要求过滤
            if query_metadata.required_languages and isinstance(filtered_resumes, list):
                logger.info(f"Before languages filter: {len(filtered_resumes)}")
                filtered_resumes = self._filter_by_languages(filtered_resumes, query_metadata.required_languages)
                logger.info(f"After languages filter: {len(filtered_resumes)}")
            
            # 根据证书要求过滤
            if query_metadata.required_certifications and isinstance(filtered_resumes, list):
                logger.info(f"Before certifications filter: {len(filtered_resumes)}")
                filtered_resumes = self._filter_by_certifications(filtered_resumes, query_metadata.required_certifications)
                logger.info(f"After certifications filter: {len(filtered_resumes)}")
            
            logger.info(f"Filtered resumes from {len(resumes)} to {len(filtered_resumes)}")
            return filtered_resumes
            
        except Exception as e:
            logger.error(f"Failed to filter resumes: {e}")
            raise

    def _filter_by_experience(self, resumes: List[Dict[str, Any]], min_experience_years: int) -> List[Dict[str, Any]]:
        """
        根据经验年限过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            min_experience_years (int): 最少经验年限
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        filtered_resumes = []
        
        for resume in resumes:
            # 检查resume是否为字典类型
            if not isinstance(resume, dict):
                logger.warning(f"Skipping non-dict resume: {type(resume)}")
                continue
            
            # 从元数据中提取工作经验
            metadata = resume.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Skipping resume with non-dict metadata: {type(metadata)}")
                continue
                
            work_experience = self._parse_list_field(metadata.get("work_experience", []))
            
            # 计算总工作经验年限
            total_experience = 0
            for exp in work_experience:
                if not isinstance(exp, dict):
                    logger.warning(f"Skipping non-dict work experience entry: {type(exp)}")
                    continue
                    
                start_date = exp.get("start_date")
                end_date = exp.get("end_date")
                if start_date and end_date:
                    # 简单计算年份差（实际项目中可能需要更精确的计算）
                    start_year = int(start_date.split("-")[0]) if "-" in start_date else 0
                    end_year = int(end_date.split("-")[0]) if "-" in end_date else 2025
                    total_experience += end_year - start_year
            
            # 如果总经验满足要求，则保留该简历
            if total_experience >= min_experience_years:
                filtered_resumes.append(resume)
                
        return filtered_resumes

    def _filter_by_education(self, resumes: List[Dict[str, Any]], required_education: str) -> List[Dict[str, Any]]:
        """
        根据学历过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            required_education (str): 所需学历
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        # 学历等级映射
        education_levels = {
            "大专": 1,
            "本科": 2,
            "硕士": 3,
            "博士": 4
        }
        
        required_level = education_levels.get(required_education, 0)
        filtered_resumes = []
        
        for resume in resumes:
            # 检查resume是否为字典类型
            if not isinstance(resume, dict):
                logger.warning(f"Skipping non-dict resume: {type(resume)}")
                continue
            
            # 从元数据中提取教育背景
            metadata = resume.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Skipping resume with non-dict metadata: {type(metadata)}")
                continue
                
            education_list = self._parse_list_field(metadata.get("education", []))
            
            # 检查是否有满足要求的学历
            meets_requirement = False
            for edu in education_list:
                if not isinstance(edu, dict):
                    logger.warning(f"Skipping non-dict education entry: {type(edu)}")
                    continue
                    
                degree = edu.get("degree", "")
                if education_levels.get(degree, 0) >= required_level:
                    meets_requirement = True
                    break
            
            if meets_requirement:
                filtered_resumes.append(resume)
                
        return filtered_resumes

    def _filter_by_skills(self, resumes: List[Dict[str, Any]], required_skills: List[str]) -> List[Dict[str, Any]]:
        """
        根据技能过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            required_skills (List[str]): 所需技能列表
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        filtered_resumes = []
        
        for resume in resumes:
            # 检查resume是否为字典类型
            if not isinstance(resume, dict):
                logger.warning(f"Skipping non-dict resume: {type(resume)}")
                continue
            
            # 从元数据中提取技能
            metadata = resume.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Skipping resume with non-dict metadata: {type(metadata)}")
                continue
                
            skills = self._parse_list_field(metadata.get("skills", []))
            
            # 检查是否包含所有必需技能
            meets_requirement = True
            for skill in required_skills:
                if skill.lower() not in [str(s).lower() for s in skills]:
                    meets_requirement = False
                    break
            
            if meets_requirement:
                filtered_resumes.append(resume)
                
        return filtered_resumes

    def _filter_by_locations(self, resumes: List[Dict[str, Any]], locations: List[str]) -> List[Dict[str, Any]]:
        """
        根据工作地点过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            locations (List[str]): 工作地点列表
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        filtered_resumes = []
        
        for resume in resumes:
            # 检查resume是否为字典类型
            if not isinstance(resume, dict):
                logger.warning(f"Skipping non-dict resume: {type(resume)}")
                continue
            
            # 从元数据中提取期望工作地点
            metadata = resume.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Skipping resume with non-dict metadata: {type(metadata)}")
                continue
                
            preferred_locations = self._parse_list_field(metadata.get("preferred_locations", []))
            
            # 检查是否有匹配的地点
            meets_requirement = False
            for location in locations:
                if location in [str(loc) for loc in preferred_locations]:
                    meets_requirement = True
                    break
            
            if meets_requirement:
                filtered_resumes.append(resume)
                
        return filtered_resumes

    def _filter_by_languages(self, resumes: List[Dict[str, Any]], required_languages: List[str]) -> List[Dict[str, Any]]:
        """
        根据语言要求过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            required_languages (List[str]): 语言要求列表
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        filtered_resumes = []
        
        for resume in resumes:
            # 检查resume是否为字典类型
            if not isinstance(resume, dict):
                logger.warning(f"Skipping non-dict resume: {type(resume)}")
                continue
            
            # 从元数据中提取语言能力
            metadata = resume.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Skipping resume with non-dict metadata: {type(metadata)}")
                continue
                
            languages = self._parse_list_field(metadata.get("languages", []))
            
            # 检查是否满足所有语言要求
            meets_requirement = True
            for language in required_languages:
                if language.lower() not in [str(l).lower() for l in languages]:
                    meets_requirement = False
                    break
            
            if meets_requirement:
                filtered_resumes.append(resume)
                
        return filtered_resumes

    def _filter_by_certifications(self, resumes: List[Dict[str, Any]], required_certifications: List[str]) -> List[Dict[str, Any]]:
        """
        根据证书要求过滤简历
        
        Args:
            resumes (List[Dict[str, Any]]): 简历列表
            required_certifications (List[str]): 证书要求列表
            
        Returns:
            List[Dict[str, Any]]: 过滤后的简历列表
        """
        filtered_resumes = []
        
        for resume in resumes:
            # 检查resume是否为字典类型
            if not isinstance(resume, dict):
                logger.warning(f"Skipping non-dict resume: {type(resume)}")
                continue
            
            # 从元数据中提取证书
            metadata = resume.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"Skipping resume with non-dict metadata: {type(metadata)}")
                continue
                
            certifications = self._parse_list_field(metadata.get("certifications", []))
            
            # 检查是否满足所有证书要求
            meets_requirement = True
            for certification in required_certifications:
                if certification.lower() not in [str(c).lower() for c in certifications]:
                    meets_requirement = False
                    break
            
            if meets_requirement:
                filtered_resumes.append(resume)
                
        return filtered_resumes