import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from math import pi

# Cấu hình đường dẫn
DATA_PATH = 'data/raw/behavioral_features.csv'
OUTPUT_DIR = 'reports/figures'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    try:
        df = pd.read_csv(DATA_PATH)
        print(f"📥 Đã tải dữ liệu: {df.shape}")
        return df
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file tại: {DATA_PATH}")
        return None

def plot_separation_boxplots(df):
    """Vẽ Boxplot so sánh các chỉ số quan trọng"""
    print("📊 Đang vẽ Boxplots...")
    
    # [FIX LỖI TÊN CỘT] Cập nhật đúng tên cột có trong file CSV
    key_features = [
        'chasing_score', 
        'drawdown_panic_sell_ratio',  # Sửa từ panic_sell_ratio -> drawdown_panic_sell_ratio
        'buy_sell_ratio', 
        'explosion_buy_ratio',
        'premature_exit_rate',
        'avg_profit'
    ]
    
    # Kiểm tra xem các cột này có tồn tại trong DF không trước khi vẽ
    existing_features = [col for col in key_features if col in df.columns]
    
    if not existing_features:
        print("⚠️ Không tìm thấy các cột feature cần vẽ!")
        return

    plt.figure(figsize=(15, 10))
    for i, feature in enumerate(existing_features):
        plt.subplot(2, 3, i+1)
        
        # [FIX WARNING] Thêm hue và legend=False để tránh warning của Seaborn mới
        sns.boxplot(
            data=df, 
            x='Investor_Type', 
            y=feature, 
            hue='Investor_Type',  # Gán hue bằng x
            palette="Set2", 
            legend=False          # Tắt legend để tránh lặp
        )
        plt.title(f'Phân phối: {feature}')
        plt.ylabel('Giá trị')
        plt.xlabel('')
        
    plt.tight_layout()
    output_path = f"{OUTPUT_DIR}/1_feature_separation.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ Đã lưu: {output_path}")

def plot_winrate_vs_profit(df):
    """Vẽ Scatter plot nghịch lý: Win Rate cao nhưng Lỗ"""
    print("📊 Đang vẽ Scatter Plot...")
    
    if 'win_rate' not in df.columns or 'total_return' not in df.columns:
        print("⚠️ Thiếu cột win_rate hoặc total_return, bỏ qua biểu đồ này.")
        return

    plt.figure(figsize=(10, 6))
    sns.scatterplot(
        data=df, 
        x='win_rate', 
        y='total_return', 
        hue='Investor_Type', 
        style='Investor_Type',
        palette={'FOMO': '#FF6B6B', 'RATIONAL': '#4ECDC4'}, 
        s=100, 
        alpha=0.7
    )
    
    plt.title('Nghịch lý FOMO: Win Rate cao nhưng Lỗ nặng', fontsize=14, fontweight='bold')
    plt.xlabel('Tỷ lệ thắng (Win Rate)', fontsize=12)
    plt.ylabel('Tổng lợi nhuận (Total Return)', fontsize=12)
    plt.axhline(0, color='gray', linestyle='--', linewidth=1) 
    plt.legend(title='Loại Nhà đầu tư')
    
    output_path = f"{OUTPUT_DIR}/2_profit_paradox.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ Đã lưu: {output_path}")

def plot_radar_chart(df):
    """Vẽ Radar Chart so sánh trung bình 2 nhóm"""
    print("📊 Đang vẽ Radar Chart...")
    
    # [FIX LỖI TÊN CỘT] Cập nhật đúng tên cột
    target_features = [
        'chasing_score', 
        'drawdown_panic_sell_ratio', # Sửa tên cột ở đây nữa
        'premature_exit_rate', 
        'buy_sell_ratio', 
        'trade_freq_cv'
    ]
    
    # Lọc chỉ lấy các cột tồn tại
    features = [col for col in target_features if col in df.columns]
    
    if not features:
        print("⚠️ Không đủ cột để vẽ Radar Chart.")
        return

    # Tính mean theo nhóm
    summary = df.groupby('Investor_Type')[features].mean()
    
    # Chuẩn hóa Min-Max để vẽ lên Radar cho đẹp
    # (Tránh trường hợp biến thì giá trị 100, biến thì giá trị 0.1)
    normalized_summary = (summary - summary.min()) / (summary.max() - summary.min())
    normalized_summary = normalized_summary.fillna(0) 
    
    categories = list(normalized_summary.columns)
    N = len(categories)
    
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1] 
    
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    
    plt.xticks(angles[:-1], categories, color='grey', size=10)
    
    # Vẽ FOMO
    if 'FOMO' in normalized_summary.index:
        values_fomo = normalized_summary.loc['FOMO'].values.flatten().tolist()
        values_fomo += values_fomo[:1]
        ax.plot(angles, values_fomo, linewidth=2, linestyle='solid', label='FOMO', color='#FF6B6B')
        ax.fill(angles, values_fomo, '#FF6B6B', alpha=0.25)
    
    # Vẽ RATIONAL
    if 'RATIONAL' in normalized_summary.index:
        values_rational = normalized_summary.loc['RATIONAL'].values.flatten().tolist()
        values_rational += values_rational[:1]
        ax.plot(angles, values_rational, linewidth=2, linestyle='solid', label='RATIONAL', color='#4ECDC4')
        ax.fill(angles, values_rational, '#4ECDC4', alpha=0.25)
    
    plt.title('Dấu vân tay hành vi (Behavioral Fingerprint)', size=15, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    
    output_path = f"{OUTPUT_DIR}/3_radar_persona.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ Đã lưu: {output_path}")

def main():
    df = load_data()
    if df is not None:
        sns.set_style("whitegrid")
        plot_separation_boxplots(df)
        plot_winrate_vs_profit(df)
        plot_radar_chart(df)
        print(f"\n✨ HOÀN TẤT! Mở folder '{OUTPUT_DIR}' để xem ảnh báo cáo.")

if __name__ == "__main__":
    main()
    