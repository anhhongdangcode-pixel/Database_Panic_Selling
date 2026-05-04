import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from config import DATA_RAW_DIR

def train_fomo_detector():
    """
    Train Random Forest model để phát hiện FOMO
    Output: FOMO Score (xác suất 0-1), không phải label binary
    """
    
    print("🔄 Đang tải features...")
    feature_path = DATA_RAW_DIR / 'behavioral_features.csv'
    df = pd.read_csv(feature_path)
    
    print(f"✅ Đã tải {len(df)} investors")
    
    # =============================================
    # 1. PREPARE DATA
    # =============================================
    
    # Tách labels ra TRƯỚC (quan trọng!)
    investor_ids = df['Investor_ID'].copy()
    true_labels = df['Investor_Type'].copy()
    
    # Drop cả ID và Type để tránh data leakage
    X = df.drop(['Investor_ID', 'Investor_Type'], axis=1)
    
    # Binary classification: FOMO (1) vs Non-FOMO (0)
    y = true_labels.map({
        'FOMO': 1, 
        'RATIONAL': 0, 
        'NOISE': 0
    })
    
    print(f"\n📊 CLASS DISTRIBUTION:")
    print(f"FOMO: {(y == 1).sum()} ({(y == 1).sum() / len(y) * 100:.1f}%)")
    print(f"Non-FOMO: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")
    
    # Handle missing values
    X = X.fillna(0)
    
    # Feature names (lưu lại để sau này dùng)
    feature_names = X.columns.tolist()
    
    # Train-test split (stratified để giữ tỉ lệ class)
    X_train, X_test, y_train, y_test, ids_train, ids_test, labels_train, labels_test = train_test_split(
        X, y, investor_ids, true_labels,
        test_size=0.2, 
        random_state=42, 
        stratify=y
    )
    
    print(f"\n✅ Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"   Train FOMO: {(y_train == 1).sum()} ({(y_train == 1).sum() / len(y_train) * 100:.1f}%)")
    print(f"   Test FOMO:  {(y_test == 1).sum()} ({(y_test == 1).sum() / len(y_test) * 100:.1f}%)")
    
    # =============================================
    # 2. TRAIN MODEL
    # =============================================
    
    print("\n⚙️ Đang train Random Forest...")
    
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    rf.fit(X_train, y_train)
    
    print("✅ Training completed!")
    
    # =============================================
    # 3. EVALUATE ON TEST SET (CHƯA THẤY BAO GIỜ!)
    # =============================================
    
    print("\n" + "="*60)
    print("📊 EVALUATING ON TEST SET (UNSEEN DATA)")
    print("="*60)
    
    # Predictions
    y_pred_class = rf.predict(X_test)  # Class prediction (0 or 1)
    y_pred_proba = rf.predict_proba(X_test)[:, 1]  # ← FOMO SCORE (0-1)
    
    # Tạo DataFrame kết quả để dễ phân tích
    results_df = pd.DataFrame({
        'Investor_ID': ids_test,
        'True_Type': labels_test,
        'True_Binary': y_test,
        'Predicted_Class': y_pred_class,
        'FOMO_Score': y_pred_proba  # ← ĐÂY MỚI LÀ FOMO SCORE THẬT!
    })
    
    # Phân loại level
    results_df['FOMO_Level'] = results_df['FOMO_Score'].apply(
        lambda x: 'High' if x >= 0.7 else ('Medium' if x >= 0.4 else 'Low')
    )
    
    # =============================================
    # 4. METRICS
    # =============================================
    
    # A. Classification Metrics
    print("\n" + "="*60)
    print("A. CLASSIFICATION METRICS (Threshold = 0.5)")
    print("="*60)
    print(classification_report(
        y_test, y_pred_class, 
        target_names=['Non-FOMO', 'FOMO'],
        digits=3
    ))
    
    # B. Confusion Matrix
    cm = confusion_matrix(y_test, y_pred_class)
    print("\nCONFUSION MATRIX:")
    print(f"{'':15} Predicted Non-FOMO  Predicted FOMO")
    print(f"True Non-FOMO  {cm[0,0]:^17d}  {cm[0,1]:^14d}")
    print(f"True FOMO      {cm[1,0]:^17d}  {cm[1,1]:^14d}")
    
    tn, fp, fn, tp = cm.ravel()
    print(f"\n  True Negatives:  {tn} (Non-FOMO correctly identified)")
    print(f"  False Positives: {fp} (Non-FOMO mislabeled as FOMO)")
    print(f"  False Negatives: {fn} (FOMO missed)")
    print(f"  True Positives:  {tp} (FOMO correctly caught)")
    
    # C. ROC-AUC (Quan trọng nhất cho probability model!)
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n🎯 ROC-AUC Score: {auc:.4f}")
    
    if auc >= 0.95:
        print("   → EXCELLENT! Model phân biệt cực tốt!")
    elif auc >= 0.85:
        print("   → GOOD! Model hoạt động tốt!")
    elif auc >= 0.75:
        print("   → ACCEPTABLE! Có thể cải thiện thêm!")
    else:
        print("   → POOR! Cần điều chỉnh features hoặc model!")
    
    # D. Cross-validation
    print("\n⚙️ Cross-Validation (5-fold Stratified)...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(rf, X_train, y_train, cv=skf, scoring='roc_auc', n_jobs=-1)
    print(f"CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"Individual folds: {[f'{s:.3f}' for s in cv_scores]}")
    
    # =============================================
    # 5. ANALYZE FOMO SCORE DISTRIBUTION
    # =============================================
    
    print("\n" + "="*60)
    print("B. FOMO SCORE DISTRIBUTION ANALYSIS")
    print("="*60)
    
    # Phân tích theo True Label
    fomo_true = results_df[results_df['True_Binary'] == 1]['FOMO_Score']
    non_fomo_true = results_df[results_df['True_Binary'] == 0]['FOMO_Score']
    
    print(f"\nTrue FOMO investors (n={len(fomo_true)}):")
    print(f"  Mean Score: {fomo_true.mean():.3f}")
    print(f"  Median:     {fomo_true.median():.3f}")
    print(f"  Min-Max:    {fomo_true.min():.3f} - {fomo_true.max():.3f}")
    print(f"  Std:        {fomo_true.std():.3f}")
    
    print(f"\nTrue Non-FOMO investors (n={len(non_fomo_true)}):")
    print(f"  Mean Score: {non_fomo_true.mean():.3f}")
    print(f"  Median:     {non_fomo_true.median():.3f}")
    print(f"  Min-Max:    {non_fomo_true.min():.3f} - {non_fomo_true.max():.3f}")
    print(f"  Std:        {non_fomo_true.std():.3f}")
    
    # Separation Score
    separation = fomo_true.mean() - non_fomo_true.mean()
    print(f"\n📏 Separation: {separation:.3f} (càng cao càng tốt, >0.5 là excellent)")
    
    # =============================================
    # 6. FEATURE IMPORTANCE
    # =============================================
    
    print("\n" + "="*60)
    print("C. FEATURE IMPORTANCE")
    print("="*60)
    
    feature_importance = pd.DataFrame({
        'Feature': feature_names,
        'Importance': rf.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    print("\n🔝 Top 15 Features:")
    for idx, row in feature_importance.head(15).iterrows():
        print(f"  {row['Feature']:35s} {row['Importance']:.4f}")
    
    # =============================================
    # 7. ERROR ANALYSIS
    # =============================================
    
    print("\n" + "="*60)
    print("D. ERROR ANALYSIS")
    print("="*60)
    
    # False Positives (Non-FOMO được gán nhầm là FOMO)
    false_positives = results_df[
        (results_df['True_Binary'] == 0) & 
        (results_df['Predicted_Class'] == 1)
    ].sort_values('FOMO_Score', ascending=False)
    
    if len(false_positives) > 0:
        print(f"\n❌ FALSE POSITIVES (n={len(false_positives)}):")
        print("   Top 5 most confident mistakes:")
        for idx, row in false_positives.head(5).iterrows():
            print(f"   {row['Investor_ID']}: Score={row['FOMO_Score']:.3f}, True={row['True_Type']}")
    
    # False Negatives (FOMO bị bỏ sót)
    false_negatives = results_df[
        (results_df['True_Binary'] == 1) & 
        (results_df['Predicted_Class'] == 0)
    ].sort_values('FOMO_Score')
    
    if len(false_negatives) > 0:
        print(f"\n❌ FALSE NEGATIVES (n={len(false_negatives)}):")
        print("   Top 5 FOMO investors missed:")
        for idx, row in false_negatives.head(5).iterrows():
            print(f"   {row['Investor_ID']}: Score={row['FOMO_Score']:.3f} (missed!)")
    
    # =============================================
    # 8. VISUALIZATIONS
    # =============================================
    
    print("\n📊 Creating visualizations...")
    
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Plot 1: Feature Importance
    ax1 = fig.add_subplot(gs[0, :2])
    top_features = feature_importance.head(15)
    ax1.barh(range(len(top_features)), top_features['Importance'])
    ax1.set_yticks(range(len(top_features)))
    ax1.set_yticklabels(top_features['Feature'])
    ax1.set_xlabel('Importance')
    ax1.set_title('Top 15 Feature Importance', fontsize=14, fontweight='bold')
    ax1.invert_yaxis()
    
    # Plot 2: ROC Curve
    ax2 = fig.add_subplot(gs[0, 2])
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
    ax2.plot(fpr, tpr, linewidth=2, label=f'ROC (AUC={auc:.3f})')
    ax2.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random')
    ax2.set_xlabel('False Positive Rate')
    ax2.set_ylabel('True Positive Rate')
    ax2.set_title(f'ROC Curve (AUC={auc:.3f})', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Confusion Matrix
    ax3 = fig.add_subplot(gs[1, 0])
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax3, cbar=False)
    ax3.set_title('Confusion Matrix', fontsize=14, fontweight='bold')
    ax3.set_ylabel('True Label')
    ax3.set_xlabel('Predicted Label')
    ax3.set_xticklabels(['Non-FOMO', 'FOMO'])
    ax3.set_yticklabels(['Non-FOMO', 'FOMO'])
    
    # Plot 4: FOMO Score Distribution (QUAN TRỌNG!)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.hist(non_fomo_true, bins=30, alpha=0.6, label='True Non-FOMO', color='blue', edgecolor='black')
    ax4.hist(fomo_true, bins=30, alpha=0.6, label='True FOMO', color='red', edgecolor='black')
    ax4.axvline(0.5, color='black', linestyle='--', linewidth=2, label='Threshold=0.5')
    ax4.set_xlabel('FOMO Score (Probability)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('FOMO Score Distribution', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Score by True Type (Boxplot)
    ax5 = fig.add_subplot(gs[1, 2])
    results_df.boxplot(column='FOMO_Score', by='True_Type', ax=ax5)
    ax5.set_title('FOMO Score by True Type', fontsize=14, fontweight='bold')
    ax5.set_xlabel('True Investor Type')
    ax5.set_ylabel('FOMO Score')
    plt.sca(ax5)
    plt.xticks(rotation=45)
    
    # Plot 6: Threshold Analysis
    ax6 = fig.add_subplot(gs[2, :])
    thresholds_test = np.linspace(0, 1, 100)
    precisions = []
    recalls = []
    f1_scores = []
    
    for thresh in thresholds_test:
        y_pred_thresh = (y_pred_proba >= thresh).astype(int)
        tp = ((y_test == 1) & (y_pred_thresh == 1)).sum()
        fp = ((y_test == 0) & (y_pred_thresh == 1)).sum()
        fn = ((y_test == 1) & (y_pred_thresh == 0)).sum()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
    
    ax6.plot(thresholds_test, precisions, label='Precision', linewidth=2)
    ax6.plot(thresholds_test, recalls, label='Recall', linewidth=2)
    ax6.plot(thresholds_test, f1_scores, label='F1-Score', linewidth=2)
    ax6.axvline(0.5, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax6.axvline(0.7, color='red', linestyle='--', linewidth=1, alpha=0.5, label='High FOMO threshold')
    ax6.set_xlabel('Threshold')
    ax6.set_ylabel('Score')
    ax6.set_title('Metrics vs Threshold', fontsize=14, fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.savefig(DATA_RAW_DIR / 'model_evaluation.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {DATA_RAW_DIR / 'model_evaluation.png'}")
    
    # =============================================
    # 9. SAVE MODEL & ARTIFACTS
    # =============================================
    
    print("\n💾 Saving model and artifacts...")
    
    # Save model
    model_path = DATA_RAW_DIR / 'fomo_detector_model.pkl'
    joblib.dump(rf, model_path)
    print(f"✅ Model: {model_path}")
    
    # Save feature names
    feature_names_path = DATA_RAW_DIR / 'feature_names.txt'
    with open(feature_names_path, 'w') as f:
        f.write('\n'.join(feature_names))
    print(f"✅ Features: {feature_names_path}")
    
    # Save test results
    results_path = DATA_RAW_DIR / 'test_results.csv'
    results_df.to_csv(results_path, index=False)
    print(f"✅ Results: {results_path}")
    
    # Save feature importance
    importance_path = DATA_RAW_DIR / 'feature_importance.csv'
    feature_importance.to_csv(importance_path, index=False)
    print(f"✅ Importance: {importance_path}")
    
    # =============================================
    # 10. DEMONSTRATE FOMO SCORE USAGE
    # =============================================
    
    print("\n" + "="*60)
    print("E. FOMO SCORE EXAMPLES (10 RANDOM TEST INVESTORS)")
    print("="*60)
    
    sample = results_df.sample(min(10, len(results_df)))
    
    for idx, row in sample.iterrows():
        true_type = row['True_Type']
        fomo_score = row['FOMO_Score']
        fomo_level = row['FOMO_Level']
        
        # Confidence
        confidence = abs(fomo_score - 0.5) * 2
        
        print(f"\n{'─'*60}")
        print(f"Investor ID: {row['Investor_ID']}")
        print(f"  True Type:     {true_type}")
        print(f"  FOMO Score:    {fomo_score:.1%} {'🔴' if fomo_score >= 0.7 else '🟡' if fomo_score >= 0.4 else '🟢'}")
        print(f"  FOMO Level:    {fomo_level}")
        print(f"  Confidence:    {confidence:.1%}")
        
        # Interpretation
        if fomo_score >= 0.8:
            print(f"  💬 Investor này có khả năng RẤT CAO là FOMO!")
        elif fomo_score >= 0.6:
            print(f"  💬 Investor này có xu hướng FOMO rõ rệt")
        elif fomo_score >= 0.4:
            print(f"  💬 Investor này có dấu hiệu FOMO nhẹ")
        elif fomo_score >= 0.2:
            print(f"  💬 Investor này khá lý trí, ít FOMO")
        else:
            print(f"  💬 Investor này rất kỷ luật, không FOMO!")
    
    print("\n" + "="*60)
    print("✅ TRAINING & EVALUATION COMPLETED!")
    print("="*60)
    
    return rf, feature_importance, results_df


if __name__ == "__main__":
    model, feature_importance, test_results = train_fomo_detector()