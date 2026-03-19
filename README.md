# KabuSys

日本株向け自動売買基盤（リサーチ・データ基盤・戦略・実行層）のコアライブラリ

概要
- KabuSys は日本株のデータ取得、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査（注文／約定トレース）などを目的とした内部ライブラリ群です。
- 主に DuckDB をデータストアとして利用し、J-Quants API からのデータ取得や RSS ベースのニュース収集、戦略用の特徴量・シグナル生成までカバーします。
- モジュールは「data（データ収集・ETL）」「research（ファクター計算・解析）」「strategy（特徴量合成・シグナル生成）」「execution（発注・監査）」などに分かれています。

主な機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - raw データの DuckDB への冪等保存（ON CONFLICT 処理）
- ETL / パイプライン
  - 日次 ETL（market calendar / prices / financials の差分取得 + 品質チェック）
  - 差分更新（最終取得日に基づく自動差分取得・バックフィル対応）
- スキーマ管理
  - DuckDB のスキーマ初期化（init_schema）と接続ユーティリティ
  - Raw / Processed / Feature / Execution 層のテーブル群を定義
- 研究用ユーティリティ（research）
  - モメンタム・ボラティリティ・バリューファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量・シグナル生成（strategy）
  - build_features: 生ファクターを正規化・フィルタ適用し features テーブルへ保存
  - generate_signals: features と ai_scores を統合して BUY / SELL シグナルを生成
- ニュース収集
  - RSS フィードから記事取得・前処理・raw_news へ保存・銘柄抽出（SSRF 対策・gzip 制限・トラッキング除去）
- マーケットカレンダー管理
  - 営業日判定・next/prev_trading_day・期間内営業日取得・カレンダー差分更新ジョブ
- 監査（audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル群（order_request_id を冪等キーとして採用）

セットアップ手順（開発／実行環境）
1. 前提
   - Python 3.10+ を推奨（型注釈に union 型等を使用）
   - DuckDB（Python パッケージ）
   - defusedxml（RSS パースの安全化のため）
   - ネットワークアクセス（J-Quants API や RSS 取得）

2. インストール（仮想環境推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # パッケージ自身は開発環境ならインストールして import できるようにする
   # ルートに pyproject.toml / setup.cfg 等があれば `pip install -e .` を実行
   ```

3. 環境変数（.env ファイル）
   - プロジェクトルートに置いた `.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（Settings を参照している箇所で ValueError が投げられます）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを抑制
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - 例 `.env`（必要に応じて .env.local で上書き）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

初期化（データベース・スキーマ）
- DuckDB スキーマを初期化するには data.schema.init_schema を使用します。デフォルトの DB パスは settings.duckdb_path を参照します。

Python サンプル:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# settings.duckdb_path は Path を返すため str に変換せずそのまま渡せます
conn = init_schema(settings.duckdb_path)  # ファイル作成 + テーブル作成
# 既存 DB に接続するだけなら:
# conn = get_connection(settings.duckdb_path)
```

使い方（代表的な操作例）
- 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（strategy.build_features）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成（strategy.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes を与えると記事と銘柄の紐付けも実施します（例: 上場4桁コードセット）
known_codes = {"7203", "6758", "9984", "8306"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意点 / 設計ポリシー
- ルックアヘッドバイアス対策: 戦略・特徴量計算はいずれも target_date 時点で利用可能な情報のみを参照するように設計されています（fetched_at を保存する等）。
- 冪等性: データ保存は「ON CONFLICT DO UPDATE / DO NOTHING」を使っているため再実行可能です。
- ネットワーク安全性: RSS 取得では SSRF 対策・受信サイズ制限・gzip 解凍サイズチェックなどを実施しています。
- J-Quants API: レート制限（120 req/min）やリトライ、401 時のトークン自動リフレッシュを実装しています。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント + 保存 (save_*)
    - schema.py                      # DuckDB スキーマ定義 / init_schema
    - stats.py                       # zscore_normalize 等統計ユーティリティ
    - pipeline.py                    # ETL パイプライン（run_daily_etl など）
    - news_collector.py              # RSS 収集 / 前処理 / 保存
    - calendar_management.py         # カレンダー更新 / 営業日判定ユーティリティ
    - features.py                    # 公開エイリアス（zscore_normalize）
    - audit.py                       # 監査ログ用 DDL（signal_events / order_requests / executions）
    - ...（その他 raw / processed テーブル周り）
  - research/
    - __init__.py
    - factor_research.py             # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py         # calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py         # build_features
    - signal_generator.py            # generate_signals
  - execution/                        # 発注・監視系（空ファイルあり / 実装追加想定）
  - monitoring/                       # 監視 / メトリクス等（将来実装想定）
- pyproject.toml / setup.cfg / .gitignore（リポジトリルート）

開発時のヒント
- テストや一時実行には DuckDB の ":memory:" を使うと便利です（init_schema(":memory:")）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストでの副作用を避けるには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- logger（標準 logging）を適宜設定してデバッグログを確認してください（LOG_LEVEL 環境変数でも制御可能）。

ライセンス・貢献
- この README に記載の通り、プロジェクト本体にライセンス情報や貢献ガイド（CONTRIBUTING.md）がある場合はそちらを参照してください。

お問い合わせ
- 実装や使い方に関する質問はリポジトリ内の Issue / ドキュメントに記載の連絡先へお願いします。