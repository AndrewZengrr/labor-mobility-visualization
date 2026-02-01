"""
示例脚本：使用社区属性准备可视化数据

这个脚本展示了如何使用 ConnectionDataPreparerWithAttributes
从社区检测结果中提取属性并生成可视化数据
"""

from prepare_community_connections_with_attributes import ConnectionDataPreparerWithAttributes
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def example_basic_usage():
    """示例1: 基础用法"""
    print("\n" + "="*80)
    print("示例 1: 基础用法")
    print("="*80)

    # 配置文件路径
    similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
    community_data_dir = "./community_detection_results"
    output_file = "./output/community_connections_with_attributes.json"

    # 创建输出目录
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # 创建准备器
    preparer = ConnectionDataPreparerWithAttributes(
        similarity_file=similarity_file,
        community_data_dir=community_data_dir,
        output_file=output_file
    )

    # 运行
    try:
        data = preparer.run()
        if data:
            print(f"\n✓ 成功生成 {len(data['nodes'])} 个节点")
            print(f"✓ 输出文件: {output_file}")
    except FileNotFoundError as e:
        print(f"\n❌ 文件未找到: {e}")
        print("请确保以下文件/目录存在：")
        print(f"  - 相似度矩阵: {similarity_file}")
        print(f"  - 社区数据目录: {community_data_dir}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def example_custom_thresholds():
    """示例2: 自定义过滤阈值"""
    print("\n" + "="*80)
    print("示例 2: 自定义过滤阈值")
    print("="*80)

    similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
    community_data_dir = "./community_detection_results"
    output_file = "./output/community_connections_strict.json"

    # 创建输出目录
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    preparer = ConnectionDataPreparerWithAttributes(
        similarity_file=similarity_file,
        community_data_dir=community_data_dir,
        output_file=output_file
    )

    # 设置更严格的阈值
    preparer.min_overlap_size = 10  # 至少10个重叠节点
    preparer.min_retention_forward = 0.10  # 至少10%前向保留率
    preparer.min_retention_backward = 0.10  # 至少10%后向保留率
    preparer.min_jaccard = 0.05  # 至少0.05 Jaccard相似度

    print("使用严格阈值:")
    print(f"  - 最小重叠大小: {preparer.min_overlap_size}")
    print(f"  - 最小前向保留率: {preparer.min_retention_forward}")
    print(f"  - 最小后向保留率: {preparer.min_retention_backward}")
    print(f"  - 最小Jaccard: {preparer.min_jaccard}")

    try:
        data = preparer.run()
        if data:
            print(f"\n✓ 生成了更少但更可靠的连接")
            print(f"✓ 输出文件: {output_file}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


def example_check_attributes():
    """示例3: 检查提取的属性"""
    print("\n" + "="*80)
    print("示例 3: 检查提取的属性")
    print("="*80)

    similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
    community_data_dir = "./community_detection_results"
    output_file = "./output/community_connections_debug.json"

    # 创建输出目录
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    preparer = ConnectionDataPreparerWithAttributes(
        similarity_file=similarity_file,
        community_data_dir=community_data_dir,
        output_file=output_file
    )

    try:
        data = preparer.run()

        if data and len(data['nodes']) > 0:
            # 详细检查前几个节点的属性
            print("\n" + "-"*80)
            print("前3个节点的详细属性:")
            print("-"*80)

            for i, node in enumerate(data['nodes'][:3]):
                print(f"\n节点 {i+1}: {node['id']}")
                print(f"  年份: {node['year']}")
                print(f"  社区ID: {node['community']}")
                print(f"  大小: {node['size']}")
                print(f"  度数: {node['total_degree']} (入度:{node['in_degree']}, 出度:{node['out_degree']})")

                attrs = node['attributes']
                print(f"\n  属性:")
                print(f"    总劳动力: {attrs['total_workforce']:,}")

                if attrs['top3_states']:
                    print(f"    前3个州:")
                    for state in attrs['top3_states']:
                        print(f"      - {state['value']}: {state['count']} ({state['percentage']:.1f}%)")

                if attrs['top5_metros']:
                    print(f"    前5个都市区:")
                    for metro in attrs['top5_metros']:
                        print(f"      - {metro['value']}: {metro['count']} ({metro['percentage']:.1f}%)")

                if attrs['top3_naics_2digit']:
                    print(f"    前3个NAICS(2位):")
                    for naics in attrs['top3_naics_2digit']:
                        print(f"      - {naics['value']}: {naics['count']} ({naics['percentage']:.1f}%)")

            print("\n" + "-"*80)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def example_multiple_levels():
    """示例4: 为多个层级准备数据"""
    print("\n" + "="*80)
    print("示例 4: 为多个层级准备数据")
    print("="*80)

    community_data_dir = "./community_detection_results"

    levels = ['level1', 'level2', 'level3']

    for level in levels:
        similarity_file = f"./similarity_matrices_complete/similarity_matrix_{level}_complete.parquet"
        output_file = f"./output/community_connections_{level}_with_attributes.json"

        # 检查文件是否存在
        if not Path(similarity_file).exists():
            print(f"\n⚠ 跳过 {level}: 文件不存在 {similarity_file}")
            continue

        print(f"\n处理 {level}...")

        # 创建输出目录
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        preparer = ConnectionDataPreparerWithAttributes(
            similarity_file=similarity_file,
            community_data_dir=community_data_dir,
            output_file=output_file
        )

        try:
            data = preparer.run()
            if data:
                print(f"✓ {level}: {len(data['nodes'])} 节点, {len(data['links'])} 边")
        except Exception as e:
            print(f"❌ {level} 处理失败: {e}")


def verify_input_files():
    """验证输入文件是否存在"""
    print("\n" + "="*80)
    print("验证输入文件")
    print("="*80)

    # 检查相似度矩阵
    similarity_file = Path("./similarity_matrices_complete/similarity_matrix_level1_complete.parquet")
    if similarity_file.exists():
        print(f"✓ 相似度矩阵存在: {similarity_file}")
        print(f"  文件大小: {similarity_file.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"✗ 相似度矩阵不存在: {similarity_file}")

    # 检查社区数据目录
    community_data_dir = Path("./community_detection_results")
    if community_data_dir.exists():
        csv_files = list(community_data_dir.glob("*.csv"))
        print(f"\n✓ 社区数据目录存在: {community_data_dir}")
        print(f"  发现 {len(csv_files)} 个CSV文件:")
        for csv_file in csv_files:
            print(f"    - {csv_file.name} ({csv_file.stat().st_size / 1024:.2f} KB)")
    else:
        print(f"\n✗ 社区数据目录不存在: {community_data_dir}")
        print(f"  请创建目录并放入社区检测结果CSV文件")

    print("="*80)


def main():
    """主函数 - 运行所有示例"""
    print("\n" + "="*80)
    print("社区属性数据准备 - 示例脚本")
    print("="*80)

    # 首先验证输入文件
    verify_input_files()

    # 选择要运行的示例
    print("\n请选择要运行的示例:")
    print("1. 基础用法")
    print("2. 自定义过滤阈值")
    print("3. 检查提取的属性")
    print("4. 为多个层级准备数据")
    print("5. 运行所有示例")
    print("0. 退出")

    choice = input("\n请输入选项 (0-5): ").strip()

    if choice == '1':
        example_basic_usage()
    elif choice == '2':
        example_custom_thresholds()
    elif choice == '3':
        example_check_attributes()
    elif choice == '4':
        example_multiple_levels()
    elif choice == '5':
        example_basic_usage()
        example_custom_thresholds()
        example_check_attributes()
        example_multiple_levels()
    elif choice == '0':
        print("\n再见!")
    else:
        print("\n无效的选项，请重新运行")


if __name__ == "__main__":
    main()
