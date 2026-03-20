# KabuSys

日本株自動売買基盤（KabuSys）の Python パッケージ。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを含むモジュール群を提供します。

> 注意: 本 README はソースコード（src/kabusys 以下）の現状実装に基づいて作成しています。実運用時は個別ドキュメント（StrategyModel.md / DataPlatform.md 等）を参照してください。

---

目次
- プロジェクト概要
- 主な機能
- 前提（環境）
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（設定）
- よく使う API / ワークフロー
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買プラットフォームのコアライブラリです。J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、研究用ファクターを正規化・合成して特徴量（features）を構築、AI スコアやルールを組み合わせて売買シグナルを生成します。さらにニュースの収集・記事と銘柄の紐付け、発注用スキーマや監査ログ用スキーマも含まれます。

設計上の特徴:
- DuckDB をデータベース層に採用（ローカルファイルで高速に分析可能）
- J-Quants API 用のリトライ・レート制御・トークン自動リフレッシュを実装
- ETL / feature / signal の各処理は原則として冪等（idempotent）
- ルックアヘッドバイアス防止を考慮した時点ベースの処理

---

## 主な機能

- Data
  - J-Quants API クライアント（fetch / save）：日足価格、財務データ、マーケットカレンダー
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分更新／バックフィル／品質チェック）
  - ニュース収集（RSS → raw_news）、記事ID 正規化、銘柄抽出と紐付け
  - マーケットカレンダー管理・営業日判定ユーティリティ
  - 統計ユーティリティ（Z スコア正規化 等）

- Research / Strategy
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量構築（build_features）: 生ファクターの正規化・ユニバースフィルタ・features テーブル保存
  - シグナル生成（generate_signals）: features と ai_scores を統合し BUY / SELL を生成

- Execution / Audit（スキーマ）
  - signals / signal_queue / orders / trades / positions / audit 用テーブル定義（監査ログ・トレーサビリティ考慮）

---

## 前提（環境）

- Python 3.10 以上（ソース内で型注釈に `X | None` を使用）
- 必要な主要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS など）
- J-Quants や kabu API、Slack を使う場合は各種認証情報（環境変数）を設定

（実際の requirements.txt はプロジェクトに応じて整備してください）

---

## セットアップ手順

1. リポジトリをクローン（適宜）
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール（例）
   - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に従ってください。

4. 環境変数を準備
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定します。
   - 自動ロードはデフォルトで行われます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必要な主な環境変数（詳細は下記「環境変数」参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG/INFO/...）

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - これにより必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（簡単な例）

以下はライブラリの代表的な処理を実行する例です。実行前に環境変数と DB 初期化を済ませてください。

- DuckDB の初期化（1回だけ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

- 特徴量の構築（features テーブルを target_date で置換）
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date(2024, 1, 31))
print(f"built features: {count}")
```

- シグナル生成（features / ai_scores / positions を参照して signals に書き込む）
```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals created: {total}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 抽出可能な銘柄コードセット（例: prices_daily から集める）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

---

## 環境変数（設定）

src/kabusys/config.py の Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token に使われます。

- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード（発注連携に使用）

- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（既定: data/kabusys.duckdb）

- SQLITE_PATH (任意)
  - モニタリング用 SQLite パス（既定: data/monitoring.db）

- KABUSYS_ENV (任意)
  - development / paper_trading / live （デフォルト: development）
  - settings.is_live / is_paper / is_dev で利用

- LOG_LEVEL (任意)
  - DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動的に .env / .env.local をプロジェクトルートから読み込みます（CWD に依存しない検出）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使う API / ワークフロー（まとめ）

- DB 初期化
  - kabusys.data.schema.init_schema(db_path)

- ETL（差分・日次）
  - kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)

- J-Quants API 直接利用
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - save_daily_quotes / save_financial_statements / save_market_calendar を使って保存

- ニュース収集
  - kabusys.data.news_collector.fetch_rss(url, source)
  - save_raw_news / run_news_collection

- ファクター / 特徴量 / シグナル
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（src/kabusys 配下）:

- __init__.py
- config.py
  - 環境変数 / 設定取り回し（.env 自動読み込み、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py         : J-Quants API クライアント（取得・保存）
  - schema.py                 : DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py               : ETL パイプライン（run_daily_etl 等）
  - news_collector.py         : RSS 収集・前処理・保存・銘柄抽出
  - stats.py                  : zscore_normalize 等統計ユーティリティ
  - features.py               : 公開インターフェース（zscore の再エクスポート）
  - calendar_management.py    : market_calendar 管理・営業日判定
  - audit.py                  : 監査ログ（signal_events / order_requests / executions など）
  - (その他: quality モジュール等が想定される)
- research/
  - __init__.py
  - factor_research.py        : モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py    : forward returns / IC / summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py    : build_features（正規化・フィルタ・保存）
  - signal_generator.py       : generate_signals（final_score 計算・BUY/SELL 判定）
- execution/                  : 発注・実行層（スケルトン／拡張ポイント）
- monitoring/                 : 監視・モニタリング用 DB (SQLite) を想定

（上記はコード断片からの抜粋で、さらに細かい実装ファイルやドキュメントがプロジェクト内に存在する可能性があります）

---

## 備考 / 運用上の注意

- セキュリティ:
  - RSS 処理において SSRF を考慮した検証を実装していますが、運用環境ではプロキシやネットワーク制限も併用してください。
  - 環境変数（トークン等）は適切に管理してください。

- 冪等性:
  - save_* 系関数やスキーマ作成は冪等に設計されています（ON CONFLICT を使用）。

- ロギング／監査:
  - audit モジュールでは監査テーブルを備え、トレーサビリティを確保します。運用時は UTC を前提としたタイムゾーン設計に注意してください。

---

必要であれば README に「運用例（cron / Airflow / Prefect）」「監視アラート設計」「より詳細な設定例（.env.example）」などを追加できます。どの情報を優先して追加しましょうか？