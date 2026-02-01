# 使用DuckDB构建大规模职业转换图数据 - 更新属性版本
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from pathlib import Path
import gc
import os
import json
import psutil

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_dir(path: str) -> Path:
    """确保目录存在，不存在则创建"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def monitor_memory():
    """监控kernel内存使用"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    logger.info(f"Kernel memory usage: {memory_mb:.1f} MB")
    return memory_mb

def setup_duckdb_connection():
    """设置DuckDB连接，使用外部存储"""
    logger.info("Setting up DuckDB connection with external storage...")
    
    work_dir = ensure_dir('./duckdb_work')
    temp_dir = ensure_dir('./duckdb_temp') 
    
    db_path = work_dir / "graph_processing.duckdb"
    conn = duckdb.connect(str(db_path))
    
    try:
        conn.execute("SET threads = 2;")
        conn.execute(f"SET temp_directory = '{temp_dir}';")
        conn.execute("SET preserve_insertion_order = false;")
    except Exception as e:
        logger.warning(f"Could not set some DuckDB parameters: {e}")
    
    return conn

def get_target_users_in_window(conn, individual_file: str, window_start_year: int, window_end_year: int):
    """第一阶段：找出在窗口内有新职位开始的所有user_id"""
    logger.info(f"Stage 1: Finding users with new positions in window {window_start_year}-{window_end_year}...")
    
    base_date = datetime(1960, 1, 1)
    window_start_date = datetime(window_start_year, 1, 1)
    window_end_date = datetime(window_end_year, 12, 31)
    days_since_base_start = (window_start_date - base_date).days
    days_since_base_end = (window_end_date - base_date).days
    
    # 快速扫描找出目标用户
    conn.execute("DROP TABLE IF EXISTS target_users")
    conn.execute(f"""
    CREATE TABLE target_users AS
    SELECT DISTINCT user_id
    FROM read_parquet('{individual_file}')
    WHERE country LIKE '%United States%'
        AND rcid IS NOT NULL
        AND startdate IS NOT NULL
        AND startdate BETWEEN {days_since_base_start} AND {days_since_base_end}
    """)
    
    target_user_count = conn.execute("SELECT COUNT(*) FROM target_users").fetchone()[0]
    logger.info(f"Found {target_user_count:,} users with new positions in window")
    monitor_memory()
    return target_user_count

def load_company_geo_lookup(conn, company_file: str):
    """加载公司地理分布数据"""
    logger.info("Loading company geographic distribution data...")
    conn.execute("DROP TABLE IF EXISTS company_geo_lookup")
    conn.execute(f"""
    CREATE TABLE company_geo_lookup AS
    SELECT 
        rcid, geo_rcid, real_country, real_state, real_metro_area,
        company, naics_code, year_founded,
        ultimate_parent_rcid, child_rcid,
        rics_k50, rics_k200, rics_k400, employee_count
    FROM read_parquet('{company_file}')
    WHERE rcid IS NOT NULL AND geo_rcid IS NOT NULL
        AND real_country IS NOT NULL AND real_country != ''
        AND real_state IS NOT NULL AND real_state != ''
        AND real_metro_area IS NOT NULL AND real_metro_area != ''
    """)
    
    company_count = conn.execute("SELECT COUNT(*) FROM company_geo_lookup").fetchone()[0]
    logger.info(f"Loaded {company_count:,} company geographic records")

def process_user_batch(conn, individual_file: str, window_start_year: int, window_end_year: int, 
                      batch_offset: int, batch_size: int, max_overlap_days: int = 730):
    """处理一批用户的完整职业轨迹"""
    logger.info(f"Processing user batch: offset {batch_offset}, size {batch_size}")
    
    base_date = datetime(1960, 1, 1)
    window_start_date = datetime(window_start_year, 1, 1)
    window_end_date = datetime(window_end_year, 12, 31)
    days_since_base_start = (window_start_date - base_date).days
    days_since_base_end = (window_end_date - base_date).days
    
    # 获取当前批次的用户列表
    conn.execute("DROP TABLE IF EXISTS batch_users")
    conn.execute(f"""
    CREATE TABLE batch_users AS
    SELECT user_id FROM target_users 
    LIMIT {batch_size} OFFSET {batch_offset}
    """)
    
    batch_user_count = conn.execute("SELECT COUNT(*) FROM batch_users").fetchone()[0]
    if batch_user_count == 0:
        logger.info("No more users to process")
        return 0
    
    # 加载这批用户的完整职业轨迹
    conn.execute("DROP TABLE IF EXISTS batch_positions")
    conn.execute(f"""
    CREATE TABLE batch_positions AS
    SELECT 
        i.user_id, i.position_id, i.rcid as original_rcid, c.geo_rcid,
        i.startdate, i.enddate, i.state, i.role_k1500, i.metro_area, i.country,
        i.position_number, i.seniority, i.salary, i.total_compensation, i.remote_suitability,
        ROW_NUMBER() OVER (PARTITION BY i.user_id ORDER BY 
            COALESCE(i.startdate, 0), COALESCE(i.position_number, 999999)
        ) as time_rank,
        COUNT(*) OVER (PARTITION BY i.user_id) as total_positions_per_user
    FROM read_parquet('{individual_file}') i
    INNER JOIN company_geo_lookup c ON (
        i.rcid = c.rcid AND i.country = c.real_country
        AND i.state = c.real_state AND i.metro_area = c.real_metro_area
    )
    INNER JOIN batch_users bu ON i.user_id = bu.user_id
    WHERE i.country LIKE '%United States%'
        AND i.rcid IS NOT NULL AND i.country IS NOT NULL AND i.country != ''
        AND i.state IS NOT NULL AND i.state != '' 
        AND i.metro_area IS NOT NULL AND i.metro_area != ''
    """)
    
    # 添加下一职位信息
    conn.execute("DROP TABLE IF EXISTS batch_with_next")
    conn.execute("""
    CREATE TABLE batch_with_next AS
    SELECT *,
        LEAD(geo_rcid) OVER (PARTITION BY user_id ORDER BY time_rank) AS next_geo_rcid,
        LEAD(startdate) OVER (PARTITION BY user_id ORDER BY time_rank) AS next_startdate,
        LEAD(enddate) OVER (PARTITION BY user_id ORDER BY time_rank) AS next_enddate,
        LEAD(geo_rcid, 2) OVER (PARTITION BY user_id ORDER BY time_rank) AS next_next_geo_rcid
    FROM batch_positions
    """)
    
    # enddate推断
    conn.execute("DROP TABLE IF EXISTS batch_with_inference")
    conn.execute("""
    CREATE TABLE batch_with_inference AS
    SELECT *,
        CASE 
            WHEN enddate IS NULL AND next_startdate IS NOT NULL
                 AND geo_rcid != next_geo_rcid AND time_rank < total_positions_per_user
                 AND next_startdate - startdate BETWEEN 90 AND 7300
                 AND NOT (next_enddate IS NOT NULL AND next_next_geo_rcid = geo_rcid)
            THEN next_startdate - 1
            ELSE enddate
        END as inferred_enddate,
        CASE 
            WHEN enddate IS NULL AND next_startdate IS NOT NULL
                 AND geo_rcid != next_geo_rcid AND time_rank < total_positions_per_user
                 AND next_startdate - startdate BETWEEN 90 AND 7300
                 AND NOT (next_enddate IS NOT NULL AND next_next_geo_rcid = geo_rcid)
            THEN true
            ELSE false
        END as enddate_inferred
    FROM batch_with_next
    """)
    
    # 创建转换关系 - 按新职位startdate筛选
    conn.execute("DROP TABLE IF EXISTS batch_transitions")
    conn.execute(f"""
    CREATE TABLE batch_transitions AS
    SELECT 
        i1.user_id,
        i1.geo_rcid as geo_rcid_pre, i2.geo_rcid as geo_rcid_new,
        i1.original_rcid as rcid_pre, i2.original_rcid as rcid_new,
        i1.enddate, i2.startdate,
        i1.state as state_pre, i2.state as state_new,
        i1.role_k1500 as role_k1500_pre, i2.role_k1500 as role_k1500_new,
        i1.metro_area as metro_area_pre, i2.metro_area as metro_area_new,
        i1.position_number as position_number_pre, i2.position_number as position_number_new,
        i1.inferred_enddate, i1.enddate_inferred,
        i1.seniority as seniority_pre, i2.seniority as seniority_new,
        i1.salary as salary_pre, i2.salary as salary_new,
        i1.total_compensation as total_compensation_pre, i2.total_compensation as total_compensation_new,
        i1.remote_suitability as remote_suitability_pre, i2.remote_suitability as remote_suitability_new,
        CASE 
            WHEN i1.inferred_enddate IS NULL OR i2.startdate IS NULL THEN NULL
            ELSE i2.startdate - i1.inferred_enddate
        END as time_gap
    FROM batch_with_inference i1
    JOIN batch_with_inference i2 ON i1.user_id = i2.user_id AND i1.position_number + 1 = i2.position_number
    WHERE i1.country LIKE '%United States%' AND i2.country LIKE '%United States%'
        AND i2.startdate BETWEEN {days_since_base_start} AND {days_since_base_end}
        AND (i1.inferred_enddate IS NULL OR i2.startdate - i1.inferred_enddate >= -{max_overlap_days})
        AND i1.geo_rcid != i2.geo_rcid
    """)
    
    # 添加公司信息
    conn.execute("DROP TABLE IF EXISTS batch_final_transitions")
    conn.execute("""
    CREATE TABLE batch_final_transitions AS
    SELECT bt.*,
        c1.company as company_name_pre,
        c1.ultimate_parent_rcid as ultimate_parent_rcid_pre,
        c1.child_rcid as child_rcid_pre,
        c2.company as company_name_new,
        c2.ultimate_parent_rcid as ultimate_parent_rcid_new,
        c2.child_rcid as child_rcid_new
    FROM batch_transitions bt
    LEFT JOIN company_geo_lookup c1 ON bt.geo_rcid_pre = c1.geo_rcid
    LEFT JOIN company_geo_lookup c2 ON bt.geo_rcid_new = c2.geo_rcid
    WHERE c1.geo_rcid IS NOT NULL AND c2.geo_rcid IS NOT NULL
    """)
    
    # 插入到总表
    conn.execute("""
    INSERT INTO position_transitions 
    SELECT * FROM batch_final_transitions
    """)
    
    batch_transition_count = conn.execute("SELECT COUNT(*) FROM batch_final_transitions").fetchone()[0]
    logger.info(f"Batch processed: {batch_user_count:,} users, {batch_transition_count:,} transitions")
    
    # 清理批次临时表
    tables_to_drop = ['batch_users', 'batch_positions', 'batch_with_next', 
                     'batch_with_inference', 'batch_transitions', 'batch_final_transitions']
    for table in tables_to_drop:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    
    # 强制垃圾回收
    gc.collect()
    monitor_memory()
    
    return batch_transition_count

def create_position_transitions_batch_processing(conn, individual_file: str, company_file: str, 
                                               window_start_year: int, window_end_year: int,
                                               batch_size: int = 10000, max_overlap_days: int = 730):
    """使用分批处理创建职位转换表"""
    logger.info(f"Creating position transitions using batch processing for {window_start_year}-{window_end_year}...")
    logger.info(f"Batch size: {batch_size:,} users per batch")
    
    # 第一阶段：找出目标用户
    target_user_count = get_target_users_in_window(conn, individual_file, window_start_year, window_end_year)
    
    # 加载公司地理数据
    load_company_geo_lookup(conn, company_file)
    
    # 创建最终转换表
    conn.execute("DROP TABLE IF EXISTS position_transitions")
    conn.execute("""
    CREATE TABLE position_transitions (
        user_id BIGINT, geo_rcid_pre VARCHAR, geo_rcid_new VARCHAR,
        rcid_pre VARCHAR, rcid_new VARCHAR, enddate INTEGER, startdate INTEGER,
        state_pre VARCHAR, state_new VARCHAR, role_k1500_pre VARCHAR, role_k1500_new VARCHAR,
        metro_area_pre VARCHAR, metro_area_new VARCHAR, position_number_pre INTEGER, position_number_new INTEGER,
        inferred_enddate INTEGER, enddate_inferred BOOLEAN, 
        seniority_pre DOUBLE, seniority_new DOUBLE,
        salary_pre DOUBLE, salary_new DOUBLE,
        total_compensation_pre DOUBLE, total_compensation_new DOUBLE,
        remote_suitability_pre DOUBLE, remote_suitability_new DOUBLE,
        time_gap INTEGER,
        company_name_pre VARCHAR, ultimate_parent_rcid_pre VARCHAR, child_rcid_pre VARCHAR,
        company_name_new VARCHAR, ultimate_parent_rcid_new VARCHAR, child_rcid_new VARCHAR
    )
    """)
    
    # 分批处理
    total_transitions = 0
    batch_offset = 0
    batch_count = 0
    
    while True:
        batch_count += 1
        logger.info(f"Processing batch {batch_count}...")
        
        batch_transitions = process_user_batch(
            conn, individual_file, window_start_year, window_end_year,
            batch_offset, batch_size, max_overlap_days
        )
        
        if batch_transitions == 0:
            break
            
        total_transitions += batch_transitions
        batch_offset += batch_size
        
        logger.info(f"Cumulative transitions: {total_transitions:,}")
    
    # 清理
    conn.execute("DROP TABLE IF EXISTS target_users")
    
    logger.info(f"Batch processing completed: {total_transitions:,} transitions from {batch_count-1} batches")
    monitor_memory()

def build_workforce_statistics_for_nodes(conn, individual_file: str, window_start_year: int, window_end_year: int):
    """构建节点劳动力统计 - 统计窗口内在职的所有员工"""
    logger.info(f"Building node workforce statistics for window {window_start_year}-{window_end_year}...")
    
    base_date = datetime(1960, 1, 1)
    window_start_date = datetime(window_start_year, 1, 1)
    window_end_date = datetime(window_end_year, 12, 31)
    days_since_base_start = (window_start_date - base_date).days
    days_since_base_end = (window_end_date - base_date).days
    
    conn.execute("DROP TABLE IF EXISTS workforce_statistics")
    conn.execute(f"""
    CREATE TABLE workforce_statistics AS
    WITH time_filtered_positions AS (
        SELECT 
            i.user_id,
            i.rcid,
            i.state,
            i.metro_area,
            i.startdate,
            i.enddate,
            i.role_k1500,
            i.seniority,
            i.salary,
            i.total_compensation,
            i.remote_suitability,
            c.geo_rcid
        FROM read_parquet('{individual_file}') i
        LEFT JOIN company_geo_lookup c ON (
            i.rcid = c.rcid 
            AND i.state = c.real_state  
            AND i.metro_area = c.real_metro_area
        )
        WHERE i.country LIKE '%United States%'
            AND i.rcid IS NOT NULL
            AND i.state IS NOT NULL AND i.state != ''
            AND i.metro_area IS NOT NULL AND i.metro_area != ''
            AND c.geo_rcid IS NOT NULL
            AND (
                (i.startdate IS NOT NULL AND i.enddate IS NOT NULL AND 
                 i.startdate <= {days_since_base_end} AND i.enddate >= {days_since_base_start})
                OR
                (i.startdate IS NOT NULL AND i.enddate IS NULL AND 
                 i.startdate <= {days_since_base_end})
            )
    ),
    -- role_k1500分布向量（top30）
    role_distribution AS (
        SELECT 
            geo_rcid,
            role_k1500,
            COUNT(*) as role_count
        FROM time_filtered_positions
        WHERE role_k1500 IS NOT NULL AND role_k1500 != ''
        GROUP BY geo_rcid, role_k1500
    ),
    role_distribution_ranked AS (
        SELECT 
            geo_rcid,
            role_k1500,
            role_count,
            ROW_NUMBER() OVER (PARTITION BY geo_rcid ORDER BY role_count DESC) as rank
        FROM role_distribution
    ),
    role_distribution_top30 AS (
        SELECT 
            geo_rcid,
            STRING_AGG(role_k1500 || ':' || role_count, '|' ORDER BY rank) as role_k1500_vector
        FROM role_distribution_ranked
        WHERE rank <= 30
        GROUP BY geo_rcid
    ),
    -- role entropy计算
    role_entropy_calc AS (
        SELECT 
            rd.geo_rcid,
            -SUM((rd.role_count * 1.0 / total.total_roles) * 
                 LOG2(rd.role_count * 1.0 / total.total_roles)) as role_entropy
        FROM role_distribution rd
        JOIN (
            SELECT geo_rcid, SUM(role_count) as total_roles
            FROM role_distribution
            GROUP BY geo_rcid
        ) total ON rd.geo_rcid = total.geo_rcid
        GROUP BY rd.geo_rcid
    ),
    -- seniority统计
    seniority_stats AS (
        SELECT 
            geo_rcid,
            AVG(seniority) as avg_seniority,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY seniority) as seniority_p25,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY seniority) as seniority_median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seniority) as seniority_p75
        FROM time_filtered_positions
        WHERE seniority IS NOT NULL
        GROUP BY geo_rcid
    ),
    -- 薪资统计
    salary_stats AS (
        SELECT 
            geo_rcid,
            AVG(salary) as avg_salary,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) as median_salary,
            AVG(total_compensation) as avg_total_compensation,
            AVG(remote_suitability) as avg_remote_suitability
        FROM time_filtered_positions
        WHERE salary IS NOT NULL OR total_compensation IS NOT NULL OR remote_suitability IS NOT NULL
        GROUP BY geo_rcid
    )
    SELECT 
        c.geo_rcid,
        rd.role_k1500_vector,
        re.role_entropy,
        ss.avg_seniority,
        ss.seniority_p25,
        ss.seniority_median,
        ss.seniority_p75,
        sal.avg_salary,
        sal.median_salary,
        sal.avg_total_compensation,
        sal.avg_remote_suitability
    FROM (SELECT DISTINCT geo_rcid FROM time_filtered_positions) c
    LEFT JOIN role_distribution_top30 rd ON c.geo_rcid = rd.geo_rcid
    LEFT JOIN role_entropy_calc re ON c.geo_rcid = re.geo_rcid
    LEFT JOIN seniority_stats ss ON c.geo_rcid = ss.geo_rcid
    LEFT JOIN salary_stats sal ON c.geo_rcid = sal.geo_rcid
    """)
    
    stats = conn.execute("""
        SELECT COUNT(*) as nodes
        FROM workforce_statistics
    """).fetchone()
    
    logger.info(f"Node workforce statistics: {stats[0]:,} nodes")
    monitor_memory()

def build_nodes_table_external(conn):
    """构建节点表"""
    logger.info("Building nodes table...")
    
    conn.execute("DROP TABLE IF EXISTS nodes_pre")
    conn.execute("""
    CREATE TABLE nodes_pre AS
    SELECT DISTINCT
        geo_rcid_pre as geo_rcid, 
        first(rcid_pre) as rcid,
        first(company_name_pre) as company_name,
        first(ultimate_parent_rcid_pre) as ultimate_parent_rcid,
        first(child_rcid_pre) as child_rcid,
        first(state_pre) as real_state, 
        first(metro_area_pre) as real_metro_area
    FROM position_transitions 
    WHERE geo_rcid_pre IS NOT NULL 
    GROUP BY geo_rcid_pre
    """)
    
    conn.execute("DROP TABLE IF EXISTS nodes_new")
    conn.execute("""
    CREATE TABLE nodes_new AS
    SELECT DISTINCT
        geo_rcid_new as geo_rcid,
        first(rcid_new) as rcid,
        first(company_name_new) as company_name,
        first(ultimate_parent_rcid_new) as ultimate_parent_rcid,
        first(child_rcid_new) as child_rcid,
        first(state_new) as real_state,
        first(metro_area_new) as real_metro_area
    FROM position_transitions 
    WHERE geo_rcid_new IS NOT NULL 
    GROUP BY geo_rcid_new
    """)
    
    conn.execute("DROP TABLE IF EXISTS graph_nodes")
    conn.execute("""
    CREATE TABLE graph_nodes AS
    WITH all_nodes AS (
        SELECT * FROM nodes_pre UNION ALL SELECT * FROM nodes_new
    ),
    unique_nodes AS (
        SELECT 
            geo_rcid, 
            first(rcid) as rcid,
            first(company_name) as company_name,
            first(ultimate_parent_rcid) as ultimate_parent_rcid,
            first(child_rcid) as child_rcid,
            first(real_state) as real_state,
            first(real_metro_area) as real_metro_area
        FROM all_nodes
        WHERE real_state IS NOT NULL AND real_state != '' 
        AND real_metro_area IS NOT NULL AND real_metro_area != ''
        GROUP BY geo_rcid
    )
    SELECT 
        un.*,
        c.real_country,
        c.rics_k50,
        c.rics_k200,
        c.rics_k400,
        c.employee_count,
        c.year_founded,
        ws.role_k1500_vector,
        ws.role_entropy,
        ws.avg_seniority,
        ws.seniority_p25,
        ws.seniority_median,
        ws.seniority_p75,
        ws.avg_salary,
        ws.median_salary,
        ws.avg_total_compensation,
        ws.avg_remote_suitability
    FROM unique_nodes un
    LEFT JOIN company_geo_lookup c ON un.geo_rcid = c.geo_rcid
    LEFT JOIN workforce_statistics ws ON un.geo_rcid = ws.geo_rcid
    """)
    
    conn.execute("DROP TABLE nodes_pre")
    conn.execute("DROP TABLE nodes_new")
    
    stats = conn.execute("""
        SELECT count(*) as total_nodes, count(DISTINCT rcid) as unique_companies
        FROM graph_nodes
    """).fetchone()
    
    logger.info(f"Created nodes table: {stats[0]:,} nodes, {stats[1]:,} companies")
    monitor_memory()

def build_edges_table_external(conn):
    """构建边表"""
    logger.info("Building edges table...")
    
    conn.execute("DROP TABLE IF EXISTS graph_edges")
    conn.execute("""
    CREATE TABLE graph_edges AS
    WITH edge_transitions AS (
        SELECT 
            geo_rcid_pre as source, 
            geo_rcid_new as target,
            count(*) as flow_count,
            -- 薪资变化统计（排除空值）
            AVG(CASE WHEN salary_pre IS NOT NULL THEN salary_pre END) as avg_salary_pre,
            AVG(CASE WHEN salary_new IS NOT NULL AND salary_pre IS NOT NULL 
                THEN salary_new - salary_pre END) as avg_salary_change,
            AVG(CASE WHEN total_compensation_new IS NOT NULL AND total_compensation_pre IS NOT NULL 
                THEN total_compensation_new - total_compensation_pre END) as avg_total_compensation_change,
            -- seniority变化
            AVG(CASE WHEN seniority_new IS NOT NULL AND seniority_pre IS NOT NULL 
                THEN seniority_new - seniority_pre END) as avg_seniority_change,
            -- remote_suitability
            AVG(CASE WHEN remote_suitability_pre IS NOT NULL 
                THEN remote_suitability_pre END) as avg_remote_suitability_pre,
            AVG(CASE WHEN remote_suitability_new IS NOT NULL 
                THEN remote_suitability_new END) as avg_remote_suitability_new
        FROM position_transitions
        WHERE geo_rcid_pre IS NOT NULL AND geo_rcid_new IS NOT NULL
        GROUP BY geo_rcid_pre, geo_rcid_new
    ),
    -- 离职角色分布（top10）
    pre_role_distribution AS (
        SELECT 
            geo_rcid_pre as source, 
            geo_rcid_new as target, 
            role_k1500_pre,
            COUNT(*) as role_count
        FROM position_transitions
        WHERE geo_rcid_pre IS NOT NULL AND geo_rcid_new IS NOT NULL
        AND role_k1500_pre IS NOT NULL AND role_k1500_pre != ''
        GROUP BY geo_rcid_pre, geo_rcid_new, role_k1500_pre
    ),
    pre_role_ranked AS (
        SELECT 
            source, target, role_k1500_pre, role_count,
            ROW_NUMBER() OVER (PARTITION BY source, target ORDER BY role_count DESC) as rank
        FROM pre_role_distribution
    ),
    pre_role_top10 AS (
        SELECT 
            source, target,
            STRING_AGG(role_k1500_pre || ':' || role_count, '|' ORDER BY rank) as pre_role_distribution
        FROM pre_role_ranked
        WHERE rank <= 10
        GROUP BY source, target
    ),
    -- 入职角色分布（top10）
    new_role_distribution AS (
        SELECT 
            geo_rcid_pre as source, 
            geo_rcid_new as target, 
            role_k1500_new,
            COUNT(*) as role_count
        FROM position_transitions
        WHERE geo_rcid_pre IS NOT NULL AND geo_rcid_new IS NOT NULL
        AND role_k1500_new IS NOT NULL AND role_k1500_new != ''
        GROUP BY geo_rcid_pre, geo_rcid_new, role_k1500_new
    ),
    new_role_ranked AS (
        SELECT 
            source, target, role_k1500_new, role_count,
            ROW_NUMBER() OVER (PARTITION BY source, target ORDER BY role_count DESC) as rank
        FROM new_role_distribution
    ),
    new_role_top10 AS (
        SELECT 
            source, target,
            STRING_AGG(role_k1500_new || ':' || role_count, '|' ORDER BY rank) as new_role_distribution
        FROM new_role_ranked
        WHERE rank <= 10
        GROUP BY source, target
    )
    SELECT 
        et.*,
        prd.pre_role_distribution,
        nrd.new_role_distribution
    FROM edge_transitions et
    LEFT JOIN pre_role_top10 prd ON et.source = prd.source AND et.target = prd.target
    LEFT JOIN new_role_top10 nrd ON et.source = nrd.source AND et.target = nrd.target
    """)
    
    edge_stats = conn.execute("""
        SELECT 
            count(*) as unique_edges, 
            sum(flow_count) as total_transitions,
            avg(flow_count) as avg_flow_count, 
            max(flow_count) as max_flow_count
        FROM graph_edges
    """).fetchone()
    
    logger.info(f"Created edges table: {edge_stats[0]:,} edges, {edge_stats[1]:,} transitions")
    logger.info(f"Average flow count: {edge_stats[2]:.2f}, Max flow count: {edge_stats[3]}")
    monitor_memory()

def export_graph_data_rolling_window(conn, output_dir: str, window_start_year: int, window_end_year: int):
    """导出图数据"""
    output_path = ensure_dir(output_dir) / f"graph_{window_start_year}_{window_end_year}"
    output_path.mkdir(exist_ok=True)
    
    logger.info(f"Exporting graph data for window {window_start_year}-{window_end_year}...")
    
    # 导出节点和边
    nodes_file = output_path / "nodes_data.parquet"
    conn.execute(f"COPY graph_nodes TO '{nodes_file}' (FORMAT PARQUET);")
    
    edges_file = output_path / "edges_data.parquet"
    conn.execute(f"COPY graph_edges TO '{edges_file}' (FORMAT PARQUET);")
    
    # 生成元数据
    metadata = conn.execute("""
        SELECT 
            (SELECT count(*) FROM graph_nodes) as nodes_count,
            (SELECT count(*) FROM graph_edges) as edges_count,
            (SELECT sum(flow_count) FROM graph_edges) as total_flow_count,
            (SELECT avg(flow_count) FROM graph_edges) as avg_flow_count,
            (SELECT max(flow_count) FROM graph_edges) as max_flow_count,
            (SELECT count(DISTINCT rcid) FROM graph_nodes) as unique_original_companies
    """).fetchone()
    
    avg_degree = (2 * metadata[1]) / metadata[0] if metadata[0] > 0 else 0
    
    meta_data = {
        'nodes_count': int(metadata[0]),
        'edges_count': int(metadata[1]),
        'total_flow_count': int(metadata[2]),
        'avg_flow_count': float(metadata[3]),
        'max_flow_count': int(metadata[4]),
        'unique_original_companies': int(metadata[5]),
        'avg_node_degree': round(avg_degree, 2),
        'window_start_year': window_start_year,
        'window_end_year': window_end_year,
        'processing_method': 'DuckDB_Batch_Processing_Updated_Attributes',
        'node_attributes': [
            'geo_rcid', 'rcid', 'company_name', 'ultimate_parent_rcid', 'child_rcid',
            'real_country', 'real_state', 'real_metro_area',
            'rics_k50', 'rics_k200', 'rics_k400', 'employee_count', 'year_founded',
            'role_k1500_vector (top30)', 'role_entropy',
            'avg_seniority', 'seniority_p25', 'seniority_median', 'seniority_p75',
            'avg_salary', 'median_salary', 'avg_total_compensation', 'avg_remote_suitability'
        ],
        'edge_attributes': [
            'source', 'target', 'flow_count',
            'avg_salary_pre', 'avg_salary_change', 'avg_total_compensation_change',
            'avg_seniority_change',
            'pre_role_distribution (top10)', 'new_role_distribution (top10)',
            'avg_remote_suitability_pre', 'avg_remote_suitability_new'
        ],
        'nodes_file': 'nodes_data.parquet',
        'edges_file': 'edges_data.parquet'
    }
    
    metadata_file = output_path / "graph_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(meta_data, f, indent=2)
    
    logger.info(f"Graph exported: {meta_data['nodes_count']:,} nodes, {meta_data['edges_count']:,} edges")
    monitor_memory()
    return meta_data

def cleanup_external_storage(conn):
    """清理外部存储的临时表"""
    logger.info("Cleaning up external storage...")
    
    temp_tables = ['position_transitions', 'graph_nodes', 'graph_edges', 
                   'workforce_statistics', 'company_geo_lookup']
    for table in temp_tables:
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        except:
            pass
    
    gc.collect()
    logger.info("External storage cleaned up")

def process_single_year_window(individual_file: str, company_file: str, output_dir: str, 
                              target_year: int, batch_size: int = 10000, max_overlap_days: int = 730):
    """处理单个年份的两年滚动窗口"""
    window_start_year = target_year - 1
    window_end_year = target_year
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PROCESSING YEAR {target_year} WITH WINDOW {window_start_year}-{window_end_year}")
    logger.info(f"{'='*80}")
    monitor_memory()
    
    try:
        conn = setup_duckdb_connection()
        
        # 分批处理创建转换表
        create_position_transitions_batch_processing(conn, individual_file, company_file, 
                                                   window_start_year, window_end_year, batch_size, max_overlap_days)
        
        # 构建劳动力统计
        build_workforce_statistics_for_nodes(conn, individual_file, window_start_year, window_end_year)
        
        # 构建节点表
        build_nodes_table_external(conn)
        
        # 构建边表
        build_edges_table_external(conn)
        
        # 导出数据
        metadata = export_graph_data_rolling_window(conn, output_dir, window_start_year, window_end_year)
        
        # 清理
        cleanup_external_storage(conn)
        
        logger.info(f"Year {target_year} processing completed successfully!")
        return metadata
        
    except Exception as e:
        logger.error(f"Error during processing year {target_year}: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
        monitor_memory()

def main():
    """主函数 - 内存优化的滚动2年窗口图构建"""
    # 设置参数
    individual_file = '/workspace/LinkedIn/ext_disk/workforce_Parquet/individual_positions.parquet'  
    company_file = '/workspace/LinkedIn/ext_disk/workforce_Parquet/company_geo_distribution-Copy1.parquet'
    output_dir = './graph_data_rolling_windows_updated'
    
    # 处理年份范围
    start_year = 2000
    end_year = 2024
    
    # 批处理参数
    batch_size = 10000000  # 每批处理的用户数
    max_overlap_days = 730
    
    logger.info(f"Starting updated attribute graph processing for {start_year}-{end_year}")
    logger.info(f"Batch size: {batch_size:,} users per batch")
    monitor_memory()
    
    all_metadata = {}
    
    try:
        for target_year in range(start_year, end_year + 1):
            try:
                metadata = process_single_year_window(
                    individual_file, company_file, output_dir, 
                    target_year, batch_size, max_overlap_days
                )
                all_metadata[target_year] = metadata
                
                print(f"\n年份 {target_year} 完成:")
                print(f"  节点数量: {metadata['nodes_count']:,}")
                print(f"  边数量: {metadata['edges_count']:,}")
                print(f"  流动总数: {metadata['total_flow_count']:,}")
                
            except Exception as e:
                logger.error(f"Failed to process year {target_year}: {str(e)}")
                continue
        
        # 生成汇总报告
        summary_file = ensure_dir(output_dir) / "processing_summary.json"
        summary_data = {
            'processing_completed': True,
            'method': 'memory_optimized_batch_processing_updated_attributes',
            'years_processed': list(all_metadata.keys()),
            'total_years': len(all_metadata),
            'batch_size': batch_size,
            'year_metadata': all_metadata
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info("Updated attribute graph processing completed successfully!")
        
        print("\n" + "="*80)
        print("UPDATED ATTRIBUTE GRAPH CONSTRUCTION COMPLETED")
        print("="*80)
        print(f"Years processed: {start_year}-{end_year} ({len(all_metadata)} years)")
        print(f"Batch processing: {batch_size:,} users per batch")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        raise
    finally:
        monitor_memory()

if __name__ == "__main__":
    main()
