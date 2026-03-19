# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、DuckDB を用いたデータレイヤ、品質チェック、特徴量計算、リサーチ用ユーティリティ、ニュース収集、監査ログ（発注→約定のトレーサビリティ）などを含みます。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資 / 自動売買システムで必要となる以下の機能群を標準ライブラリ中心・軽量依存で提供します。

- J-Quants API クライアント（株価・財務・マーケットカレンダー）
- DuckDB を使ったデータスキーマ定義・初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 統計ユーティリティ（Z-スコア正規化、IC 計算 等）
- 監査ログ（signal → order_request → executions の追跡）
- 環境設定管理（.env 自動ロード、必須環境変数検証）

主な設計方針:
- DuckDB を中心に「Raw / Processed / Feature / Execution」層でスキーマを整理
- API 呼び出しはレート制御・リトライ・トークン自動更新を内包
- ETL は差分更新・バックフィル対応で後出し修正に耐性あり
- 可能な限り外部依存を抑え、標準ライブラリで実装（ただし DuckDB・defusedxml 等は必須）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API からのデータ取得（ページネーション、リトライ、トークン管理）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar）
- data/schema.py
  - DuckDB テーブル群（Raw / Processed / Feature / Execution）の DDL と初期化関数
- data/pipeline.py, data/etl.py
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
- data/quality.py
  - 欠損・スパイク・重複・日付不整合などの品質検査
- data/news_collector.py
  - RSS フィード取得、前処理、記事保存、銘柄抽出・紐付け
- data/calendar_management.py
  - 営業日判定、次/前営業日取得、カレンダー更新ジョブ
- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）の初期化・DB 操作
- data/stats.py, research/*
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、z-score 正規化
- config.py
  - .env 自動ロード（プロジェクトルートは .git または pyproject.toml を探索）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL 等の整合性チェック

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の union 型（|）などを使用）
- ネットワークアクセス（J-Quants API、RSS フィード）および DuckDB を使用できる環境

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   実運用では logging や requests 等の監視・実行用ライブラリを追加することを推奨します（プロジェクト内に requirements.txt がある場合はそれを利用してください）。

3. ソースからインストール（開発用）
   - pip install -e .  （pyproject.toml / setup がある場合）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と任意で `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する最低限の環境変数（.env 例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意:
- config.Settings は必須環境変数をチェックし、未設定時は ValueError を出します。

---

## 使い方（簡単な例）

Python REPL / スクリプトから主要機能を呼び出す例を示します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
```

2) 日次 ETL を実行（J-Quants トークンは環境変数経由で自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡すことも可能
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出時に有効な銘柄コードセットを渡す（None だと紐付けをスキップ）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # ソース名ごとの保存件数
```

4) 研究用ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) 環境設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live, settings.log_level)
```

6) 監査ログ（監査DB初期化）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

各関数は docstring に使用方法と前提（参照するテーブル名など）が詳述されています。API からのデータ取得・保存は冪等性（ON CONFLICT ...）を考慮しています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、development|paper_trading|live。デフォルト: development)
- LOG_LEVEL (任意、DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意、1 を設定すると .env 自動読み込みを無効化)

config.Settings クラスはこれらの検証・アクセスを提供します（未設定の必須値はエラーとなります）。

---

## ディレクトリ構成

主要ファイルと役割を抜粋します（パッケージルートは src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数/設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース収集・前処理・DB 保存
    - schema.py               -- DuckDB スキーマ定義・初期化
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - etl.py                  -- ETLResult 型の公開
    - quality.py              -- データ品質チェック
    - stats.py                -- 統計ユーティリティ（zscore_normalize 等）
    - features.py             -- 特徴量ユーティリティの公開インターフェース
    - calendar_management.py  -- 市場カレンダー管理ユーティリティ
    - audit.py                -- 監査ログ（signal/order_request/execution）初期化
  - research/
    - __init__.py
    - feature_exploration.py  -- 将来リターン / IC / サマリー等
    - factor_research.py      -- momentum/volatility/value の計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールには docstring と詳細な設計コメントが付いており、用途・副作用（どのテーブルにアクセスするか等）が明記されています。

---

## 開発・運用上の注意

- Python の型注釈（| union 等）を使用しているため Python 3.10 以上を推奨します。
- J-Quants API はレート制限（120 req/min）があります。本ライブラリは固定間隔スロットリングとリトライを組み込んでいますが、運用時は他プロセスとの競合に注意してください。
- DuckDB のバージョン差異による制約（ON DELETE CASCADE 非対応など）をコード内コメントに反映しています。運用環境の DuckDB バージョンを確認してください。
- ニュース収集は外部 HTTP を伴うため SSRF 対策や受信サイズ制限を実装していますが、運用時は追加の監視を推奨します。
- 本パッケージは API トークン等の機密情報を扱うため、.env ファイルや CI 設定の取り扱いに注意してください。

---

もし README に含めたい追加情報（例: requirements.txt の具体的内容、実運用向けの systemd / Airflow ジョブ定義、サンプル .env.example を明示する等）があれば教えてください。必要に応じて README を拡張します。