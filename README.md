# KabuSys

KabuSys は日本株を対象とした自動売買基盤のコアライブラリです。  
データ収集（J-Quants）、ETL（DuckDB）、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供し、研究→本番運用に耐えうる設計方針（冪等性、ルックアヘッド回避、トレーサビリティ）で実装されています。

主な想定用途：
- J-Quants からの株価・財務・カレンダー取得 → DuckDB に蓄積（差分更新）
- 研究環境で計算した生ファクターを正規化して特徴量テーブルへ保存
- 特徴量 + AI スコアを統合して売買シグナルを生成
- RSS からニュース収集し記事と銘柄の紐付けを行う
- 発注・約定・ポジション管理のスキーマと監査ログを提供（Execution 層）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local を自動読み込み（必要に応じて自動ロードを無効化可能）
- データ取得・保存（J-Quants クライアント）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得・DuckDB 保存（冪等）
  - レートリミット管理、リトライ、トークン自動更新
- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェックを含む日次 ETL（run_daily_etl）
- スキーマ管理
  - DuckDB のスキーマ定義と初期化（init_schema）
- 特徴量計算
  - research モジュールでの生ファクター計算（momentum, volatility, value）
  - feature_engineering.build_features による正規化＋features テーブル格納
- シグナル生成
  - strategy.signal_generator.generate_signals による final_score 計算、BUY/SELL 判定、signals テーブル格納
- ニュース収集
  - RSS フィード取得、安全対策（SSRF対策、gzip制限、XML サニタイズ）
  - raw_news / news_symbols への冪等保存
- 監査ログ（audit）
  - 信号→発注→約定のトレーサビリティ用テーブル定義（signal_events / order_requests / executions 等）
- ユーティリティ
  - 統計（z-score 正規化等）、マーケットカレンダー操作（次/前営業日取得）など

---

## セットアップ手順

前提：
- Python 3.9+（型注釈に union | 型を使用しているため 3.10 以上を推奨）
- DuckDB を利用（Python パッケージ duckdb）
- ネットワーク経由で J-Quants に接続するための資格情報

例: 仮想環境作成・パッケージインストール（最小）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 追加の依存がある場合は requirements.txt を用意して pip install -r requirements.txt
```

環境変数（必須 / 任意）:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（本プロジェクトでは Slack 連携設定が参照される箇所あり）
  - SLACK_CHANNEL_ID: 通知先チャネル ID
  - KABU_API_PASSWORD: kabuステーション API 用パスワード（execution 層で使用）
- 任意（デフォルトにフォールバック）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。

サンプル .env（.env.example）
```text
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DB スキーマ初期化:
Python REPL またはスクリプト内で DuckDB を初期化します。
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル作成＋スキーマ作成
```

---

## 使い方（主な操作例）

以下はライブラリ API のシンプルな利用例です。実運用はエラーハンドリングやログ出力、定期ジョブ化（cron / Airflow 等）を推奨します。

1) DuckDB 接続 + スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からのデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量構築（research の生ファクターを正規化して features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2025, 3, 15))
print(f"built features for {count} symbols")
```

4) シグナル生成（features + ai_scores → signals）
```python
from kabusys.strategy import generate_signals
from datetime import date
num_signals = generate_signals(conn, date(2025, 3, 15), threshold=0.6)
print(f"signals written: {num_signals}")
```

5) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203","6758", ...}  # 事前に有効銘柄セットを準備
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) J-Quants からのデータ取得をテスト的に行う場合
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from datetime import date
rows = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
```

注意:
- generate_signals / build_features は DuckDB 上の適切なテーブル（prices_daily, raw_financials, features, ai_scores, positions 等）が揃っていることを前提とします。
- J-Quants API 利用時はトークン（JQUANTS_REFRESH_TOKEN）を正しく設定してください。

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数管理・設定取得
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント（取得・保存関数）
    - schema.py                        # DuckDB スキーマ定義・初期化
    - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
    - news_collector.py                # RSS ニュース収集・保存
    - calendar_management.py           # カレンダー管理 utilities
    - stats.py                         # 統計ユーティリティ（zscore_normalize）
    - features.py                      # features の公開インターフェース（再エクスポート）
    - audit.py                         # 監査ログ用スキーマ定義
    - pipeline.py (ETL)
  - research/
    - __init__.py
    - factor_research.py               # Momentum / Volatility / Value 計算
    - feature_exploration.py           # IC / forward returns / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py           # build_features
    - signal_generator.py              # generate_signals
  - execution/                          # 発注・実行層（未実装のエンドポイント群）
    - __init__.py
  - monitoring/                         # 監視・アラート関連（パッケージ化用プレースホルダ）

ドキュメント参照（コード内に参照されている設計ドキュメントの存在を想定）:
- StrategyModel.md, DataPlatform.md, DataSchema.md など（実運用時に合わせて参照してください）

---

## 開発・運用上の注意

- ルックアヘッドバイアス対策：すべての戦略計算は target_date 時点で利用可能なデータのみを使用する設計になっています。
- 冪等性：J-Quants からの保存処理は ON CONFLICT / DO UPDATE を使用し、再実行可能です。
- 品質チェック：ETL 後に品質チェック（欠損・スパイク等）を実施する設計で、問題の検出はログに残りますが ETL を中断しない設計です。
- セキュリティ：
  - news_collector は SSRF 対策、XML サニタイズ、レスポンスサイズ制限を実装しています。
  - API トークンやパスワードは .env に保存する際は取り扱いに注意してください（アクセス権限の制御等）。
- 本番運用時は KABUSYS_ENV を適切に設定（paper_trading / live）しリスク制御・実際の発注フローを有効にしてください。

---

## 貢献・拡張

- 新しいデータソースの追加、execution 層の broker アダプタ実装、AI スコアの導入など拡張ポイントが多数あります。
- ユニットテスト・統合テストの整備、CI/CD によるスキーママイグレーションの管理を推奨します。

---

必要であれば README にサンプル .env.example ファイル、より詳しい API 参照（関数シグネチャ）、運用フロー（cron / Airflow の例）、FAQ、既知の制約一覧なども追加できます。どの情報を優先的に追加しますか？