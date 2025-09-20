# -*- coding: utf-8 -*-
"""
搜索引擎 - 完全保持原有功能
从main.py中提取的搜索相关函数，功能完全不变
"""

import numpy as np
from zai import ZhipuAiClient
from neo4j import GraphDatabase
from ..config.settings import settings

# 保持原有的全局变量初始化
zhipu = ZhipuAiClient(api_key=settings.ai.zhipu_api_key)
driver = GraphDatabase.driver(settings.database.neo4j_uri, auth=(settings.database.neo4j_user, settings.database.neo4j_password))

# 如果不希望看到警告，可以过滤警告信息
if not settings.system.show_query_warnings:
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="neo4j")

def debug_print(*args, **kwargs):
    """受控的调试输出函数 - 保持原有功能"""
    if settings.system.show_debug_info:
        print(*args, **kwargs)

def l2_normalize(vec):
    """L2标准化 - 保持原有功能"""
    v = np.array(vec, dtype=np.float32)
    n = np.linalg.norm(v) + 1e-12
    return (v / n).tolist()

def embed_query_with_zhipu(text: str):
    """使用智谱AI进行文本嵌入 - 保持原有功能"""
    resp = zhipu.embeddings.create(model=settings.ai.embedding_model, input=text)
    vec = resp.data[0].embedding
    return l2_normalize(vec)

def extract_algorithm_keywords(question: str):
    """提取算法关键词 - 保持原有功能"""
    algorithm_keywords = [
        "动态规划", "dp", "贪心", "分治", "二分", "双指针", "滑动窗口", "前缀和", "差分",
        "线段树", "树状数组", "并查集", "最短路", "最小生成树", "拓扑排序", "强连通分量",
        "网络流", "最大流", "最小割", "二分图", "匹配", "匈牙利", "KM算法", "费用流",
        "莫队", "分块", "主席树", "可持久化", "平衡树", "红黑树", "AVL", "Treap",
        "哈希", "KMP", "AC自动机", "后缀数组", "后缀自动机", "回文树", "Manacher",
        "FFT", "NTT", "快速幂", "矩阵快速幂", "高斯消元", "线性基", "容斥原理",
        "组合数学", "数论", "欧拉函数", "莫比乌斯", "杜教筛", "min25筛", "洲阁筛",
        "几何", "凸包", "旋转卡壳", "半平面交", "圆", "多边形", "扫描线", "CDQ分治",
        "整体二分", "离线", "在线", "强制在线", "可持久化", "回滚", "撤销"
    ]
    
    found_keywords = []
    question_lower = question.lower()
    for keyword in algorithm_keywords:
        if keyword.lower() in question_lower:
            found_keywords.append(keyword)
    
    return found_keywords

def clean_query_text(text: str):
    """清理查询文本，移除可能导致Lucene解析错误的特殊字符 - 保持原有功能"""
    if not text or not text.strip():
        return "算法 题目"
    
    # 移除或替换Lucene特殊字符和可能导致问题的符号
    special_chars = [
        '[', ']', '(', ')', '{', '}', '~', '^', '"', '*', '?', '\\', 
        ':', '+', '-', '!', '/', '|', '&', '<', '>', '=', '@', '#',
        '$', '%', '。', '，', '；', '：', '！', '？', '、', '《', '》',
        '"', '"', ''', ''', '【', '】', '（', '）', '·', '…', '—',
        '`', "'", '\n', '\r', '\t'  # 新增一些可能导致问题的字符
    ]
    
    cleaned = text
    for char in special_chars:
        cleaned = cleaned.replace(char, ' ')
    
    # 移除连续的空格，保留单个空格
    cleaned = ' '.join(cleaned.split())
    
    # 移除前后空格
    cleaned = cleaned.strip()
    
    # 如果清理后的文本太短或为空，使用默认搜索词
    if len(cleaned) < 2:
        cleaned = "算法 题目"
    
    # 限制查询长度，避免过长的查询导致问题
    if len(cleaned) > 200:
        cleaned = cleaned[:200].strip()
    
    # 确保不以特殊字符结尾，这可能导致Lucene解析问题
    while cleaned and cleaned[-1] in '+-&|!(){}[]^"~*?:\\':
        cleaned = cleaned[:-1].strip()
    
    # 如果清理后为空，返回默认值
    if not cleaned:
        cleaned = "算法 题目"
    
    return cleaned

# 增强的混合检索Cypher查询 - 保持原有功能
CYPHER_ENHANCED_HYBRID = """
// 参数：$q (string), $qvec (list<float>), $keywords (list<string>)

// A. 全文候选（加权 0.3）
CALL ($q) {
  WITH $q AS q
  CALL db.index.fulltext.queryNodes('alg_fulltext', q) YIELD node, score
  RETURN collect({a: node, s: score * 0.3, route:'fulltext'}) AS T
}

// B. 向量候选（加权 0.5）
CALL ($qvec) {
  WITH $qvec AS qv
  CALL db.index.vector.queryNodes('chunk_vec_idx', 15, qv) YIELD node, score
  MATCH (node)<-[:HAS_CHUNK]-(alg:Algorithm)
  RETURN collect({a: alg, s: score * 0.5, route:'vector'}) AS V
}

// C. 关键词匹配候选（加权 0.2）
CALL ($keywords) {
  WITH $keywords AS kw
  UNWIND kw AS keyword
  MATCH (a:Algorithm)
  WHERE any(alias IN a.aliases WHERE toLower(alias) CONTAINS toLower(keyword))
     OR any(k IN a.keywords WHERE toLower(k) CONTAINS toLower(keyword))
     OR toLower(a.title) CONTAINS toLower(keyword)
  RETURN collect({a: a, s: 0.2, route:'keyword'}) AS K
}

// 合并三路候选并按算法聚合分数
WITH T + V + K AS R
UNWIND R AS r
WITH r.a AS a, collect(r) AS contribs
WITH a, reduce(s=0.0, x IN contribs | s + x.s) AS fused, contribs
ORDER BY fused DESC
LIMIT 8

// 图扩展 + 完整信息（增强示例代码获取）
OPTIONAL MATCH (a)-[:PREREQUISITE]->(p:Concept)
OPTIONAL MATCH (a)-[:APPLICATION]->(u:Concept)
OPTIONAL MATCH (a)-[:PITFALL]->(f:Concept)
OPTIONAL MATCH (a)-[:HAS_EXAMPLE]->(e:Example)
OPTIONAL MATCH (a)-[:HAS_CHUNK]->(c:Chunk)

// 获取详细的示例代码信息
WITH a, fused, contribs,
     collect(DISTINCT p.name)[0..8] AS prereq,
     collect(DISTINCT u.name)[0..8] AS apps,
     collect(DISTINCT f.name)[0..8] AS pitfalls,
     collect(DISTINCT e)[0..8] AS all_examples,
     [c IN collect(DISTINCT c)[0..5] | c.content] AS snippets

// 构建详细的示例信息，只包含确实存在的属性
WITH a, fused, contribs, prereq, apps, pitfalls, snippets,
     [ex IN all_examples | {
         id: ex.id,
         title: ex.title,
         description: ex.description,
         code: ex.code,
         solution: ex.solution
     }] AS detailed_examples

RETURN a.uid AS uid, a.title AS title,
       a.principle AS principle, a.cpx_time AS time, a.cpx_space AS space,
       a.intro AS intro, a.keywords AS keywords, a.aliases AS aliases,
       prereq, apps, pitfalls, detailed_examples, snippets, fused, contribs;
"""

def enhanced_hybrid_search(question: str, keywords_hint: str = ""):
    """增强的混合检索，支持AI提取的关键词提示 - 保持原有功能"""
    # 使用AI总结的内容进行查询，避免特殊字符问题
    if keywords_hint:
        # 如果有AI提取的关键词，优先使用这些关键词
        search_text = keywords_hint
        debug_print(f"【使用AI提取的关键词】{keywords_hint}")
    else:
        # 如果没有关键词提示，使用原来的清理方法
        search_text = clean_query_text(question)
        debug_print(f"【原始查询】{question[:50]}...")
        debug_print(f"【清理后查询】{search_text}")
    
    qvec = embed_query_with_zhipu(question)
    # 结合原始关键词提取和AI提取的关键词
    extracted_keywords = extract_algorithm_keywords(question)
    if keywords_hint:
        # 添加AI提取的关键词（保持权重顺序）
        ai_keywords = [kw.strip() for kw in keywords_hint.split(',') if kw.strip()]
        # 使用有序去重，保持AI关键词的权重顺序在前
        seen = set()
        merged_keywords = []
        # 首先添加AI关键词（按权重排序）
        for kw in ai_keywords:
            if kw not in seen:
                merged_keywords.append(kw)
                seen.add(kw)
        # 然后添加原始关键词
        for kw in extracted_keywords:
            if kw not in seen:
                merged_keywords.append(kw)
                seen.add(kw)
        extracted_keywords = merged_keywords
    
    debug_print(f"【合并关键词】{extracted_keywords}")
    
    # 验证查询字符串，避免空查询或有问题的查询
    if not search_text or search_text.strip() == "" or len(search_text.strip()) < 2:
        search_text = "算法 题目"
        debug_print(f"【查询修正】使用默认查询: {search_text}")
    
    # 额外检查：如果查询字符串包含可能导致Lucene问题的字符，直接使用备用查询
    lucene_problem_chars = ['[', ']', '(', ')', '{', '}', '<', '>', '"', "'"]
    has_lucene_issues = any(char in search_text for char in lucene_problem_chars)
    
    if has_lucene_issues:
        debug_print(f"【查询策略】检测到特殊字符，直接使用备用查询")
        use_backup_directly = True
    else:
        use_backup_directly = False
    
    # 如果没有Lucene问题，尝试主查询
    rows = []
    if not use_backup_directly:
        try:
            with driver.session(database=settings.database.neo4j_database) as sess:
                recs = sess.run(CYPHER_ENHANCED_HYBRID, {
                    "q": search_text,  # 使用处理后的搜索文本
                    "qvec": qvec,
                    "keywords": extracted_keywords
                })
                rows = [r.data() for r in recs]
                if rows:
                    debug_print("✅ 主查询成功")
        except Exception as e:
            debug_print(f"⚠️ 数据库查询失败：{e}")
            debug_print("🔄 尝试使用备用查询策略...")
            use_backup_directly = True
    
    # 使用备用查询
    if use_backup_directly or not rows:
        try:
            with driver.session(database=settings.database.neo4j_database) as sess:
                backup_query = """
                MATCH (a:Algorithm)
                WITH a, 
                     CASE 
                       WHEN size($keywords) = 0 THEN 0.1
                       WHEN any(keyword IN $keywords WHERE toLower(a.title) CONTAINS toLower(keyword)) THEN 0.8
                       WHEN any(keyword IN $keywords WHERE any(alias IN a.aliases WHERE toLower(alias) CONTAINS toLower(keyword))) THEN 0.6
                       WHEN any(keyword IN $keywords WHERE any(k IN a.keywords WHERE toLower(k) CONTAINS toLower(keyword))) THEN 0.4
                       ELSE 0.1
                     END AS score
                WHERE score > 0.1
                WITH a, score
                ORDER BY score DESC
                LIMIT 5
                
                OPTIONAL MATCH (a)-[:PREREQUISITE]->(p:Concept)
                OPTIONAL MATCH (a)-[:APPLICATION]->(u:Concept)
                OPTIONAL MATCH (a)-[:PITFALL]->(f:Concept)
                OPTIONAL MATCH (a)-[:HAS_EXAMPLE]->(e:Example)
                OPTIONAL MATCH (a)-[:HAS_CHUNK]->(c:Chunk)
                
                // 获取详细的示例代码信息（备用查询）
                WITH a, score,
                     collect(DISTINCT p.name)[0..8] AS prereq,
                     collect(DISTINCT u.name)[0..8] AS apps,
                     collect(DISTINCT f.name)[0..8] AS pitfalls,
                     collect(DISTINCT e)[0..8] AS all_examples,
                     [c IN collect(DISTINCT c)[0..5] | c.content] AS snippets

                // 构建详细的示例信息，只包含确实存在的属性（备用查询）
                WITH a, score, prereq, apps, pitfalls, snippets,
                     [ex IN all_examples | {
                         id: ex.id,
                         title: ex.title,
                         description: ex.description,
                         code: ex.code,
                         solution: ex.solution
                     }] AS detailed_examples
                
                RETURN a.uid AS uid, a.title AS title,
                       a.principle AS principle, a.cpx_time AS time, a.cpx_space AS space,
                       a.intro AS intro, a.keywords AS keywords, a.aliases AS aliases,
                       prereq, apps, pitfalls, detailed_examples, snippets, score AS fused, 
                       [{route: 'keyword', s: score}] AS contribs
                """
                
                recs = sess.run(backup_query, {"keywords": extracted_keywords})
                rows = [r.data() for r in recs]
                
                if rows:
                    debug_print("✅ 备用查询成功")
                else:
                    debug_print("⚠️ 备用查询也未找到结果，使用默认算法信息")
                    
        except Exception as backup_error:
            debug_print(f"❌ 备用查询也失败：{backup_error}")
            rows = []
    
    # 如果所有查询都失败，创建一个空的结果但让系统继续运行
    if not rows:
        debug_print("🔧 所有查询都失败，将使用基础上下文生成回答")
    
    debug_print(f"【检索结果】找到 {len(rows)} 个相关算法")
    for r in rows:
        routes = [c["route"] for c in (r.get("contribs") or [])]
        debug_print(f"[候选] {r['title']} | fused={r['fused']:.4f} | routes={routes}")
    
    return rows

