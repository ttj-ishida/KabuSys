# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（軽量プロトタイプ）

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムとデータプラットフォームを構築するためのモジュール群です。  
主に以下を目的としたユーティリティとドメインロジックを提供します。

- J-Quants API からの市場データ取得（OHLCV、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマ管理と冪等な保存処理
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- ニュース（RSS）収集・前処理・銘柄抽出
- 研究（ファクター計算・特徴量探索）ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ
- 市場カレンダー管理、発注・実行周りのスキーマ設計（実装の土台）

設計方針としては「DuckDB を中心に、外部ライブラリ依存を極力抑えた純粋 Python 実装」「API レート・SSRF などの安全性対策」「冪等性（ON CONFLICT）」「Look-ahead bias の防止（fetched_at の記録）」を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み
  - 設定オブジェクト（settings）による環境変数取得と検証
- kabusys.data.jquants_client
  - J-Quants API の認証・ページネーション・再試行・レート制御
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) による DB 初期化
- kabusys.data.pipeline
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェックの統合実行（quality モジュールと連携）
- kabusys.data.news_collector
  - RSS フィード取得・XML パース（defusedxml）・URL 正規化・記事保存（raw_news）
  - 銘柄コード抽出と news_symbols への紐付け
- kabusys.data.quality
  - 欠損、重複、スパイク（急変）、日付不整合などの品質チェック
- kabusys.research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - data.stats の zscore_normalize の再エクスポート
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions 等）と初期化 helper
- kabusys.data.calendar_management
  - market_calendar の更新ジョブ、営業日判定ユーティリティ

---

## 必要条件

- Python 3.10+（typing の一部表記から想定）
- パッケージ依存（最低限）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS）

（実際にパッケージ化されている場合は pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. リポジトリを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数を設定（.env をプロジェクトルートに作成することで自動的に読み込まれます）
   - 簡易テンプレートは下記参照

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # conn は duckdb.DuckDBPyConnection
     ```

---

## 環境変数 (.env) の例

プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

例（.env.example）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API（必要に応じて）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development|paper_trading|live
LOG_LEVEL=INFO
```

必須となるキー（実行部分により変わります）:
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD（発注系を使う場合）

設定は `from kabusys.config import settings` で取得できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # pathlib.Path オブジェクト
```

---

## 使い方（代表的なユースケース）

以下は主要な API と実行例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) 研究用のファクター計算 / 特徴量探索
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 30)

momentum = calc_momentum(conn, target)
forwards = calc_forward_returns(conn, target)
ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

5) J-Quants からの生データ取得（単体呼び出し）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
import duckdb
from datetime import date

token = get_id_token()  # settings から refresh token を使って idToken を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
conn = duckdb.connect("data/kabusys.duckdb")
saved = save_daily_quotes(conn, records)
```

6) 監査スキーマの初期化（order/exec 用）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## ディレクトリ構成（主要ファイル）

以下は codebase の主要ファイル一覧（src/kabusys 配下）：

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存）
    - news_collector.py             -- RSS ニュース収集・正規化・保存
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - features.py                   -- 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py        -- market_calendar 管理 / 営業日判定
    - audit.py                      -- 監査ログスキーマ（signal/order/execution）
    - etl.py                        -- 公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py                   -- 研究用関数をエクスポート
    - feature_exploration.py        -- 将来リターン / IC / summary
    - factor_research.py            -- momentum/value/volatility 等の計算
  - strategy/                       -- 戦略層（雛形）
  - execution/                      -- 発注 / 実行関連（雛形）
  - monitoring/                     -- 監視 / モニタリング（雛形）

各モジュールはドキュメント文字列（docstring）で設計意図・注意点が記載されています。実運用で使う場合は設定（.env）や DB パス、API レートの調整、ログ設定、運用フロー（paper/live）に応じた追加実装が必要です。

---

## 運用・注意点

- API レート制限と再試行:
  - J-Quants クライアントはレート制御・再試行・トークン自動更新を備えていますが、実運用時は環境（API制限）に応じてパラメータや同時実行数を調整してください。
- データの冪等性:
  - save_* 系関数は ON CONFLICT DO UPDATE / DO NOTHING を使い冪等性を意識しています。
- セキュリティ:
  - RSS の取得では SSRF 対策、XML パースは defusedxml を使用しています。外部からの入力を扱う場合は引き続き注意してください。
- 本番発注:
  - Kabu ステーションや証券会社 API と連携する場合は、paper_trading/live の環境分離と十分なテストを行ってください。
- 時刻・タイムゾーン:
  - fetched_at や監査ログは UTC 基準で保存する設計です。タイムゾーン混入に注意してください。

---

## 貢献 / 開発

- バグ修正や機能追加は Pull Request を送ってください。  
- tests は現状読み込み対象や統合テストを別途整備してください。特にネットワークや DB を使うコードは DI（id_token 注入や _urlopen のモック等）を活用してテスト可能です。

---

必要であれば、README に次の追加を作成します:
- CI / テスト実行手順
- さらに詳細な API リファレンス（関数一覧・引数説明）
- 運用手順（cron/airflow での ETL スケジューリング例）
ご希望があれば教えてください。