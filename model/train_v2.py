import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve, auc
import gc

DB_PATH = "data/ghostbus.db"

print("Loading data...")
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM labeled_stops_v2_final", conn)
conn.close()
print(f"Loaded {df.shape}")

df['hour'] = pd.to_datetime(df['last_polled_at'], unit='s', utc=True).dt.hour
df['day_of_week'] = pd.to_datetime(df['service_date'], format='%Y%m%d').dt.dayofweek
df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

trip_max_seq = df.groupby(['service_date', 'trip_id'])['stop_sequence'].transform('max')
df['stops_remaining'] = trip_max_seq - df['stop_sequence']

df_sorted = df.sort_values(['service_date', 'trip_id', 'stop_sequence']).reset_index(drop=True)
df_sorted['prev_delay'] = df_sorted.groupby(['service_date', 'trip_id'])['last_known_delay'].shift(1)
df_sorted['delay_trend'] = df_sorted['last_known_delay'] - df_sorted['prev_delay'].fillna(0)
df = df_sorted
del df_sorted
gc.collect()

df = df.reset_index(drop=True)

service_dates = df['service_date'].astype(str)
test_dates = ['20260824', '20260825']
train_mask = ~service_dates.isin(test_dates)
test_mask = service_dates.isin(test_dates)

y = df['is_skip'].astype('int8')

print("Building train-only historical features (leak-free)...")
train_df = df[train_mask][['stop_id', 'route_id', 'hour', 'is_skip']].copy()

stop_stats = train_df.groupby('stop_id')['is_skip'].agg(['mean', 'count'])
stop_stats.columns = ['stop_skip_rate', 'stop_count']
df = df.merge(stop_stats, on='stop_id', how='left')

route_stats = train_df.groupby('route_id')['is_skip'].agg(['mean', 'count'])
route_stats.columns = ['route_skip_rate', 'route_count']
df = df.merge(route_stats, on='route_id', how='left')

route_hour_stats = train_df.groupby(['route_id', 'hour'])['is_skip'].agg(['mean', 'count'])
route_hour_stats.columns = ['route_hour_skip_rate', 'route_hour_count']
df = df.merge(route_hour_stats, on=['route_id', 'hour'], how='left')

del train_df, stop_stats, route_stats, route_hour_stats
gc.collect()

feature_cols = ['hour', 'day_of_week', 'is_weekend', 'prior_skips_this_trip',
                'last_known_delay', 'has_known_delay', 'stops_remaining',
                'route_skip_rate', 'route_count',
                'route_hour_skip_rate', 'route_hour_count',
                'stop_skip_rate', 'stop_count', 'delay_trend']

X = df[feature_cols].copy()
for col in X.columns:
    X[col] = X[col].fillna(0).astype('float32')

print("Alignment check:", X.index.equals(df.index), train_mask.index.equals(df.index))

X_train, X_test = X[train_mask], X[test_mask]
y_train, y_test = y[train_mask], y[test_mask]
print(f"Train: {X_train.shape}, Test: {X_test.shape}")
print(f"Train skip rate: {y_train.mean():.6f}, Test skip rate: {y_test.mean():.6f}")

print("Training...")
model = xgb.XGBClassifier(
    n_estimators=200, max_depth=5,
    scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
    eval_metric='logloss', tree_method='hist'
)
model.fit(X_train, y_train)

probs = model.predict_proba(X_test)[:, 1]
preds = model.predict(X_test)

print(classification_report(y_test, preds))
print("ROC-AUC:", roc_auc_score(y_test, probs))

precision, recall, thresholds = precision_recall_curve(y_test, probs)
pr_auc = auc(recall, precision)
print("PR-AUC:", pr_auc)

thresholds_to_check = [0.99, 0.95, 0.90, 0.75, 0.50, 0.25, 0.10, 0.05]
print("\nThreshold sweep:")
for t in thresholds_to_check:
    pred_t = (probs >= t).astype(int)
    tp = ((pred_t == 1) & (y_test == 1)).sum()
    fp = ((pred_t == 1) & (y_test == 0)).sum()
    fn = ((pred_t == 0) & (y_test == 1)).sum()
    alerts = pred_t.sum()
    prec = tp / alerts if alerts > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    print(f"  t={t}: alerts={alerts}, TP={tp}, FP={fp}, precision={prec:.4f}, recall={rec:.4f}")

model.save_model("model/skip_model_v2.json")
print("\nModel saved to model/skip_model_v2.json")