# 简化的社区相似度矩阵构建器 - 分批处理+内存优化版
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from collections import defaultdict
import pickle
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import time
import gc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OptimizedSimilarityMatrixBuilder:
    """构建社区相似度矩阵 - 分批处理优化版"""
    
    def __init__(self, results_dir, level=1, output_dir=None, n_workers=None):
        self.results_dir = Path(results_dir)
        self.level = level
        self.community_col = f'community_level{level}'
        
        # 输出目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(results_dir).parent / "similarity_matrices"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 并行处理
        self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        
        self.yearly_data = {}
        self.yearly_communities = {}
        
        # 预计算并缓存属性分布
        self.attribute_distributions = {}
        
    def load_year_data(self, year):
        """加载指定年份的社区检测结果"""
        window_start = year - 1
        window_end = year
        
        result_dir = self.results_dir / f"results_{window_start}_{window_end}"
        result_file = result_dir / f"workforce_geo_community_{window_start}_{window_end}_results.parquet"
        
        if not result_file.exists():
            logging.warning(f"Year {year} data not found: {result_file}")
            return None
        
        df = pd.read_parquet(result_file)
        df_valid = df[df[self.community_col] != "-1"].copy()
        
        logging.info(f"Loaded year {year}: {len(df_valid)} nodes in {df_valid[self.community_col].nunique()} communities")
        
        return df_valid
    
    def load_all_years(self, year_range):
        """加载所有年份的数据"""
        logging.info(f"Loading data for years {year_range[0]}-{year_range[1]}...")
        
        available_years = []
        for year in range(year_range[0], year_range[1] + 1):
            data = self.load_year_data(year)
            if data is not None:
                self.yearly_data[year] = data
                available_years.append(year)
                
                # 构建社区字典：存储节点集合
                communities = {}
                for comm_id in data[self.community_col].unique():
                    comm_nodes = data[data[self.community_col] == comm_id]
                    communities[comm_id] = {
                        'nodes': set(comm_nodes['geo_rcid'].values),
                        'size': len(comm_nodes)
                    }
                self.yearly_communities[year] = communities
        
        logging.info(f"Successfully loaded {len(available_years)} years: {available_years}")
        return available_years
    
    def precompute_attribute_distributions(self, years):
        """
        预计算指定年份的属性分布（支持增量加载）
        """
        # 过滤掉已经计算过的年份
        years_to_compute = [y for y in years if y not in self.attribute_distributions]
        
        if not years_to_compute:
            return
        
        logging.info(f"Precomputing attribute distributions for {len(years_to_compute)} years: {years_to_compute}")
        
        for year in years_to_compute:
            if year not in self.yearly_data:
                continue
            
            self.attribute_distributions[year] = {}
            
            df = self.yearly_data[year]
            
            # 按社区分组，避免重复过滤
            grouped = df.groupby(self.community_col)
            
            for comm_id, comm_data in grouped:
                # 提取NAICS 2位码
                naics_values = comm_data['naics_code'].apply(
                    lambda x: str(x)[:2] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= 2 else None
                ).dropna()
                naics_dist = naics_values.value_counts(normalize=True).to_dict() if len(naics_values) > 0 else {}
                
                # 提取State
                state_values = comm_data['real_state'].replace('unknown', None).dropna()
                state_dist = state_values.value_counts(normalize=True).to_dict() if len(state_values) > 0 else {}
                
                # 提取Metro
                metro_values = comm_data['real_metro_area'].replace('unknown', None).dropna()
                metro_dist = metro_values.value_counts(normalize=True).to_dict() if len(metro_values) > 0 else {}
                
                # 预计算主导属性
                dominant_naics = max(naics_dist.items(), key=lambda x: x[1])[0] if naics_dist else None
                dominant_state = max(state_dist.items(), key=lambda x: x[1])[0] if state_dist else None
                
                self.attribute_distributions[year][comm_id] = {
                    'naics_dist': naics_dist,
                    'state_dist': state_dist,
                    'metro_dist': metro_dist,
                    'dominant_naics': dominant_naics,
                    'dominant_state': dominant_state
                }
            
            logging.info(f"  Precomputed distributions for year {year}: {len(self.attribute_distributions[year])} communities")
    
    def cleanup_batch_cache(self, years_to_cleanup):
        """清理已处理年份的预计算缓存"""
        for year in years_to_cleanup:
            if year in self.attribute_distributions:
                del self.attribute_distributions[year]
        
        gc.collect()
    
    def compute_distribution_similarity(self, dist1, dist2):
        """计算两个分布的相似度（余弦相似度）- 优化版"""
        if not dist1 or not dist2:
            return 0.0
        
        # 使用集合运算一次性获取所有键
        all_keys = list(set(dist1.keys()) | set(dist2.keys()))
        
        # 使用float32节省内存
        vec1 = np.array([dist1.get(k, 0.0) for k in all_keys], dtype=np.float32)
        vec2 = np.array([dist2.get(k, 0.0) for k in all_keys], dtype=np.float32)
        
        # 余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
        
        return float(dot_product / norm_product)
    
    def compute_overlap_index(self, dist1, dist2):
        """计算重叠指数（共同类别的占比）"""
        if not dist1 or not dist2:
            return 0.0
        
        common_keys = set(dist1.keys()) & set(dist2.keys())
        
        if len(common_keys) == 0:
            return 0.0
        
        # 计算共同类别在两个分布中的总权重
        overlap1 = sum(dist1[k] for k in common_keys)
        overlap2 = sum(dist2[k] for k in common_keys)
        
        # 返回平均重叠度
        return (overlap1 + overlap2) / 2.0
    
    def compute_similarity(self, year1, comm1, year2, comm2, 
                          nodes1, nodes2, size1, size2, dist1, dist2):
        """
        计算两个社区之间的完整相似度指标（预提取优化版）
        
        Returns:
        --------
        dict: 包含所有指标的字典
        """
        intersection = nodes1 & nodes2
        union = nodes1 | nodes2
        
        overlap_size = len(intersection)
        union_size = len(union)
        
        # 核心指标1: Jaccard相似度
        jaccard = overlap_size / union_size if union_size > 0 else 0.0
        
        # 核心指标2: 前向保留率（year1 → year2）
        retention_forward = overlap_size / size1 if size1 > 0 else 0.0
        
        # 核心指标3: 后向保留率（year2 ← year1）
        retention_backward = overlap_size / size2 if size2 > 0 else 0.0
        
        # 规模变化
        growth_rate = (size2 - size1) / size1 if size1 > 0 else None
        
        # 从预提取的分布计算相似度
        naics_dist1 = dist1['naics_dist']
        naics_dist2 = dist2['naics_dist']
        state_dist1 = dist1['state_dist']
        state_dist2 = dist2['state_dist']
        metro_dist1 = dist1['metro_dist']
        metro_dist2 = dist2['metro_dist']
        
        # 计算产业接近度（NAICS）
        naics_cosine_sim = self.compute_distribution_similarity(naics_dist1, naics_dist2)
        naics_overlap_index = self.compute_overlap_index(naics_dist1, naics_dist2)
        
        # 计算地理接近度（State）
        state_cosine_sim = self.compute_distribution_similarity(state_dist1, state_dist2)
        state_overlap_index = self.compute_overlap_index(state_dist1, state_dist2)
        
        # 计算地理接近度（Metro）
        metro_cosine_sim = self.compute_distribution_similarity(metro_dist1, metro_dist2)
        metro_overlap_index = self.compute_overlap_index(metro_dist1, metro_dist2)
        
        # 主导属性（直接从缓存获取）
        dominant_naics1 = dist1['dominant_naics']
        dominant_naics2 = dist2['dominant_naics']
        dominant_state1 = dist1['dominant_state']
        dominant_state2 = dist2['dominant_state']
        
        # 主导属性是否一致
        dominant_naics_match = (dominant_naics1 == dominant_naics2) if (dominant_naics1 and dominant_naics2) else None
        dominant_state_match = (dominant_state1 == dominant_state2) if (dominant_state1 and dominant_state2) else None
        
        return {
            # 核心节点重叠指标
            'jaccard': jaccard,
            'retention_forward': retention_forward,
            'retention_backward': retention_backward,
            'overlap_size': overlap_size,
            'union_size': union_size,
            'size1': size1,
            'size2': size2,
            'growth_rate': growth_rate,
            
            # 产业接近度（参考指标）
            'naics_cosine_similarity': naics_cosine_sim,
            'naics_overlap_index': naics_overlap_index,
            'dominant_naics_match': dominant_naics_match,
            
            # 地理接近度（参考指标）
            'state_cosine_similarity': state_cosine_sim,
            'state_overlap_index': state_overlap_index,
            'metro_cosine_similarity': metro_cosine_sim,
            'metro_overlap_index': metro_overlap_index,
            'dominant_state_match': dominant_state_match,
            
            # 主导属性
            'dominant_naics1': dominant_naics1,
            'dominant_naics2': dominant_naics2,
            'dominant_state1': dominant_state1,
            'dominant_state2': dominant_state2
        }
    
    def compute_year_pair_similarities(self, year1, year2):
        """
        计算两个年份之间所有社区对的相似度（预提取优化版）
        
        Returns:
        --------
        list: 相似度记录列表
        """
        logging.info(f"  Computing similarities: {year1} ↔ {year2}")
        
        year_gap = abs(year2 - year1)
        
        # 预提取nodes集合和属性分布（避免重复访问字典）
        comm1_nodes = {c: self.yearly_communities[year1][c]['nodes'] 
                      for c in self.yearly_communities[year1].keys()}
        comm2_nodes = {c: self.yearly_communities[year2][c]['nodes'] 
                      for c in self.yearly_communities[year2].keys()}
        
        comm1_sizes = {c: len(nodes) for c, nodes in comm1_nodes.items()}
        comm2_sizes = {c: len(nodes) for c, nodes in comm2_nodes.items()}
        
        dist1_cache = {c: self.attribute_distributions[year1][c] 
                      for c in self.yearly_communities[year1].keys()}
        dist2_cache = {c: self.attribute_distributions[year2][c] 
                      for c in self.yearly_communities[year2].keys()}
        
        similarities = []
        total_pairs = len(comm1_nodes) * len(comm2_nodes)
        
        # 批量构建记录
        for comm1 in comm1_nodes.keys():
            nodes1 = comm1_nodes[comm1]
            size1 = comm1_sizes[comm1]
            dist1 = dist1_cache[comm1]
            
            for comm2 in comm2_nodes.keys():
                nodes2 = comm2_nodes[comm2]
                size2 = comm2_sizes[comm2]
                dist2 = dist2_cache[comm2]
                
                result = self.compute_similarity(year1, comm1, year2, comm2,
                                                nodes1, nodes2, size1, size2,
                                                dist1, dist2)
                
                # 构建记录
                record = {
                    'year1': year1,
                    'community1': comm1,
                    'year2': year2,
                    'community2': comm2,
                    'year_gap': year_gap,
                    **result
                }
                
                similarities.append(record)
        
        logging.info(f"  Computed {len(similarities):,} pairs (total: {total_pairs:,})")
        return similarities
    
    def build_similarity_matrix(self, year_range, adjacent_only=True, parallel=False, batch_size=5):
        """
        构建相似度矩阵（分批处理版）
        
        Parameters:
        -----------
        year_range : tuple
            年份范围 (start, end)
        adjacent_only : bool
            是否只计算相邻年份
        parallel : bool
            是否使用并行计算
        batch_size : int
            每批处理的年份对数量
        
        Returns:
        --------
        pd.DataFrame: 相似度矩阵
        """
        logging.info("="*80)
        logging.info("Building Similarity Matrix (Batch Processing + Memory Optimized)")
        logging.info(f"Level: {self.level}")
        logging.info(f"Adjacent only: {adjacent_only}")
        logging.info(f"Batch size: {batch_size} year pairs per batch")
        logging.info("="*80)
        
        available_years = sorted(self.yearly_communities.keys())
        logging.info(f"Available years: {available_years}")
        
        # 生成年份对
        if adjacent_only:
            year_pairs = [(available_years[i], available_years[i+1]) 
                         for i in range(len(available_years)-1)]
            logging.info(f"Computing {len(year_pairs)} adjacent year pairs")
        else:
            from itertools import combinations
            year_pairs = list(combinations(available_years, 2))
            logging.info(f"Computing {len(year_pairs)} total year pairs")
        
        # 分批处理
        chunk_files = []
        
        for batch_idx in range(0, len(year_pairs), batch_size):
            batch_pairs = year_pairs[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            total_batches = (len(year_pairs) + batch_size - 1) // batch_size
            
            logging.info(f"\n{'='*60}")
            logging.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_pairs)} year pairs)")
            logging.info(f"{'='*60}")
            
            # 预计算当前批次需要的年份
            years_needed = set()
            for y1, y2 in batch_pairs:
                years_needed.add(y1)
                years_needed.add(y2)
            
            self.precompute_attribute_distributions(list(years_needed))
            
            # 计算当前批次的相似度
            batch_similarities = []
            
            for idx, (year1, year2) in enumerate(batch_pairs, 1):
                try:
                    pair_similarities = self.compute_year_pair_similarities(year1, year2)
                    batch_similarities.extend(pair_similarities)
                    
                    if idx % 2 == 0 or idx == len(batch_pairs):
                        logging.info(f"  Batch progress: {idx}/{len(batch_pairs)} pairs completed")
                
                except Exception as e:
                    logging.error(f"  Error computing {year1}-{year2}: {e}")
            
            # 立即保存当前批次
            if batch_similarities:
                batch_df = pd.DataFrame(batch_similarities)
                chunk_file = self.output_dir / f"_temp_chunk_{batch_idx:04d}.parquet"
                batch_df.to_parquet(chunk_file, engine='pyarrow', compression='snappy', index=False)
                chunk_files.append(chunk_file)
                
                logging.info(f"Batch {batch_num} saved: {len(batch_similarities):,} pairs -> {chunk_file.name}")
                
                # 清理内存
                del batch_similarities, batch_df
            
            # 清理已处理年份的缓存（保留可能被下一批次使用的年份）
            if batch_idx + batch_size < len(year_pairs):
                next_batch_pairs = year_pairs[batch_idx + batch_size:batch_idx + 2*batch_size]
                next_years_needed = set()
                for y1, y2 in next_batch_pairs:
                    next_years_needed.add(y1)
                    next_years_needed.add(y2)
                
                years_to_cleanup = years_needed - next_years_needed
                if years_to_cleanup:
                    logging.info(f"Cleaning up cache for {len(years_to_cleanup)} years: {sorted(years_to_cleanup)}")
                    self.cleanup_batch_cache(years_to_cleanup)
            
            gc.collect()
            logging.info(f"Batch {batch_num} memory cleaned")
        
        # 合并所有批次
        logging.info(f"\n{'='*80}")
        logging.info(f"Merging {len(chunk_files)} chunk files...")
        logging.info(f"{'='*80}")
        
        df_chunks = []
        for idx, chunk_file in enumerate(chunk_files, 1):
            chunk_df = pd.read_parquet(chunk_file)
            df_chunks.append(chunk_df)
            
            if idx % 5 == 0 or idx == len(chunk_files):
                logging.info(f"  Loaded {idx}/{len(chunk_files)} chunks")
        
        df = pd.concat(df_chunks, ignore_index=True)
        
        # 删除临时文件
        logging.info("Cleaning up temporary chunk files...")
        for chunk_file in chunk_files:
            chunk_file.unlink()
        
        # 清理所有剩余缓存
        self.cleanup_batch_cache(list(self.attribute_distributions.keys()))
        gc.collect()
        
        logging.info("="*80)
        logging.info(f"Similarity matrix built: {len(df):,} total pairs")
        logging.info("="*80)
        
        return df
    
    def analyze_similarity_matrix(self, df):
        """分析相似度矩阵的统计信息"""
        logging.info("\nAnalyzing similarity matrix...")

        if df.empty:
            logging.warning("Empty similarity matrix")
            return {}

        # 基础统计
        analysis = {
            'total_pairs': len(df),
            'year_pairs': {f"{k[0]}-{k[1]}": int(v) for k, v in df.groupby(['year1', 'year2']).size().to_dict().items()},
            'jaccard_stats': {
                'mean': float(df['jaccard'].mean()),
                'median': float(df['jaccard'].median()),
                'std': float(df['jaccard'].std()),
                'min': float(df['jaccard'].min()),
                'max': float(df['jaccard'].max()),
                'q25': float(df['jaccard'].quantile(0.25)),
                'q75': float(df['jaccard'].quantile(0.75))
            },
            'retention_forward_stats': {
                'mean': float(df['retention_forward'].mean()),
                'median': float(df['retention_forward'].median()),
                'std': float(df['retention_forward'].std())
            },
            'retention_backward_stats': {
                'mean': float(df['retention_backward'].mean()),
                'median': float(df['retention_backward'].median()),
                'std': float(df['retention_backward'].std())
            },
            'attribute_proximity': {
                'naics_cosine_mean': float(df['naics_cosine_similarity'].mean()),
                'state_cosine_mean': float(df['state_cosine_similarity'].mean()),
                'metro_cosine_mean': float(df['metro_cosine_similarity'].mean()),
                'naics_overlap_mean': float(df['naics_overlap_index'].mean()),
                'state_overlap_mean': float(df['state_overlap_index'].mean())
            }
        }

        # 打印统计信息
        print("\n" + "="*80)
        print("SIMILARITY MATRIX ANALYSIS")
        print("="*80)
        print(f"Total pairs: {analysis['total_pairs']:,}")

        print(f"\nJaccard similarity statistics:")
        print(f"  Mean: {analysis['jaccard_stats']['mean']:.4f}")
        print(f"  Median: {analysis['jaccard_stats']['median']:.4f}")
        print(f"  Std: {analysis['jaccard_stats']['std']:.4f}")
        print(f"  Range: [{analysis['jaccard_stats']['min']:.4f}, {analysis['jaccard_stats']['max']:.4f}]")

        print(f"\nRetention forward statistics:")
        print(f"  Mean: {analysis['retention_forward_stats']['mean']:.4f}")
        print(f"  Median: {analysis['retention_forward_stats']['median']:.4f}")

        print(f"\nRetention backward statistics:")
        print(f"  Mean: {analysis['retention_backward_stats']['mean']:.4f}")
        print(f"  Median: {analysis['retention_backward_stats']['median']:.4f}")

        print(f"\nAttribute proximity (reference):")
        print(f"  NAICS cosine similarity: {analysis['attribute_proximity']['naics_cosine_mean']:.4f}")
        print(f"  State cosine similarity: {analysis['attribute_proximity']['state_cosine_mean']:.4f}")
        print(f"  Metro cosine similarity: {analysis['attribute_proximity']['metro_cosine_mean']:.4f}")

        print("="*80 + "\n")

        return analysis
    
    def save_similarity_matrix(self, df, suffix='adjacent'):
        """
        保存相似度矩阵
        
        Parameters:
        -----------
        df : pd.DataFrame
            相似度矩阵
        suffix : str
            文件名后缀
        """
        logging.info(f"Saving similarity matrix to {self.output_dir}...")
        
        # 保存为parquet（主格式）
        parquet_file = self.output_dir / f"similarity_matrix_level{self.level}_{suffix}.parquet"
        df.to_parquet(parquet_file, engine='pyarrow', compression='snappy', index=False)
        logging.info(f"Saved parquet: {parquet_file} ({len(df):,} rows)")
        
        # 保存为pickle（用于快速加载）
        pickle_file = self.output_dir / f"similarity_matrix_level{self.level}_{suffix}.pkl"
        with open(pickle_file, 'wb') as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
        logging.info(f"Saved pickle: {pickle_file}")
        
        # 保存元数据
        metadata = {
            'level': self.level,
            'total_pairs': len(df),
            'columns': list(df.columns),
            'year_pairs_computed': {str(k): int(v) for k, v in df.groupby(['year1', 'year2']).size().to_dict().items()},
            'years_covered': sorted([int(x) for x in set(df['year1'].unique()) | set(df['year2'].unique())]),
            'creation_time': pd.Timestamp.now().isoformat(),
            'data_description': {
                'jaccard': 'Jaccard similarity coefficient (node overlap)',
                'retention_forward': 'Retention rate from year1 to year2',
                'retention_backward': 'Retention rate from year2 to year1',
                'naics_cosine_similarity': 'Cosine similarity of NAICS distributions (reference)',
                'state_cosine_similarity': 'Cosine similarity of state distributions (reference)',
                'metro_cosine_similarity': 'Cosine similarity of metro area distributions (reference)',
                'naics_overlap_index': 'Overlap index of NAICS categories (reference)',
                'state_overlap_index': 'Overlap index of states (reference)',
                'metro_overlap_index': 'Overlap index of metro areas (reference)'
            }
        }
        
        metadata_file = self.output_dir / f"similarity_matrix_metadata_level{self.level}_{suffix}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logging.info(f"Saved metadata: {metadata_file}")


def main():
    """主函数 - 构建优化的相似度矩阵"""
    
    results_dir = "./workforce_community_results_adaptive_4d"
    output_dir = "./similarity_matrices_complete"
    
    year_range = (2000, 2024)
    level = 2
    
    # 参数设置
    params = {
        'adjacent_only': False,    # True: 只计算相邻年份, False: 计算所有年份对
        'parallel': False,         # 预计算后串行更快
        'batch_size': 5,          # 每批处理5个年份对
        'n_workers': None
    }
    
    logging.info("="*80)
    logging.info("OPTIMIZED SIMILARITY MATRIX BUILDER (Batch Processing)")
    logging.info("="*80)
    logging.info(f"Results directory: {results_dir}")
    logging.info(f"Output directory: {output_dir}")
    logging.info(f"Year range: {year_range[0]}-{year_range[1]}")
    logging.info(f"Community level: {level}")
    logging.info(f"Parameters: {params}")
    logging.info("="*80 + "\n")
    
    # 创建构建器
    builder = OptimizedSimilarityMatrixBuilder(
        results_dir, 
        level=level, 
        output_dir=output_dir,
        n_workers=params['n_workers']
    )
    
    # 加载数据
    available_years = builder.load_all_years(year_range)
    
    if len(available_years) < 2:
        logging.error("Need at least 2 years of data")
        return
    
    # 构建相似度矩阵
    start_time = time.time()
    df_similarity = builder.build_similarity_matrix(
        year_range,
        adjacent_only=params['adjacent_only'],
        parallel=params['parallel'],
        batch_size=params['batch_size']
    )
    computation_time = time.time() - start_time
    
    logging.info(f"Computation completed in {computation_time:.2f} seconds")
    
    # 分析矩阵
    analysis = builder.analyze_similarity_matrix(df_similarity)
    
    # 保存结果
    suffix = 'adjacent' if params['adjacent_only'] else 'complete'
    builder.save_similarity_matrix(df_similarity, suffix=suffix)
    
    # 保存分析结果
    analysis['computation_time_seconds'] = computation_time
    with open(builder.output_dir / f"similarity_analysis_level{level}_{suffix}.json", 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    logging.info("\nOptimized similarity matrix construction completed successfully!")
    
    return df_similarity, analysis


if __name__ == "__main__":
    df_similarity, analysis = main()