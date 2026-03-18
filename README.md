# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
主に以下を目的としたモジュールを含みます。

- J-Quants からの市場データ取得・保存（DuckDB）
- RSS ニュース収集と銘柄紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター（モメンタム / ボラティリティ / バリュー等）計算および特徴量探索
- 監査ログ（発注 → 約定のトレーサビリティ）スキーマ初期化

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株のデータ基盤と自動売買フローの基盤を提供する Python パッケージです。  
設計方針の要点：

- データ取得は J-Quants API を利用（レート制御・リトライ・トークン自動更新対応）
- データ保存は DuckDB に対して冪等に保存（ON CONFLICT / DO UPDATE）
- ETL は差分更新・バックフィル・品質チェックを組み合わせた日次パイプライン
- Research（特徴量探索 / IC 計算等）は外部ライブラリに依存せず実装（標準ライブラリ）
- ニュース収集は RSS を安全に取得し記事IDを正規化して保存（SSRF対策・XML安全化）
- 監査ログは発注〜約定までUUIDチェーンでトレーサビリティを確保

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、リトライ、レート制御、トークン自動更新）
  - 日足・財務・マーケットカレンダーの取得と DuckDB への保存関数（save_*）
- data/news_collector.py
  - RSS 取得、安全な XML パース、記事ID生成、前処理、raw_news への冪等保存、銘柄抽出と紐付け
- data/schema.py / data/audit.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(), init_audit_schema(), init_audit_db() による初期化
- data/pipeline.py / data/etl.py
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次 ETL の統合エントリ run_daily_etl（品質チェック含む）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue 型で結果返却）
- data/stats.py / data/features.py
  - zscore_normalize（クロスセクション正規化）等の統計ユーティリティ
- research/factor_research.py / research/feature_exploration.py
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算、ファクター統計サマリ
- audit（監査ログ）モジュール
  - 発注要求・約定など監査用テーブルを提供（UTC タイムスタンプ、冪等性設計）
- config.py
  - 環境変数管理（.env/.env.local の自動ロードをサポート、必要な設定値は Settings で公開）

---

## 環境変数 / .env

自動的にプロジェクトルート（.git または pyproject.toml を起点）から `.env` / `.env.local` を読み込みます。必要な環境変数の例:

必須（Settings._require により未設定時にエラー）:
- JQUANTS_REFRESH_TOKEN: J-Quants の Refresh Token
- KABU_API_PASSWORD: kabuステーション等の API パスワード（発注モジュール利用時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動ロードを無効化
- KABUSYS の DB パス:
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
- KABU_API_BASE_URL: kabu API の base URL（デフォルトローカル）

簡単な .env.example:

```
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注意:
- テストなどで自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（Union 型 `X | Y` を使用しているため）
- git がインストールされていること

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 推奨依存（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - プロジェクトに requirements.txt / pyproject.toml があれば:
     - pip install -e .   または pip install -r requirements.txt

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか環境に設定します（上記参照）。

5. DuckDB スキーマ初期化（例）
   - Python スクリプト / REPL で:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成してスキーマを作成
conn.close()
```

6. （監査ログ用）audit DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
audit_conn.close()
```

---

## 使い方（主要利用例）

以下はライブラリを直接呼ぶ最小の例です。

1) 日次 ETL を実行してデータを取得・保存・品質チェックする

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に初期化済みなら init_schema は冪等）
conn = init_schema("data/kabusys.duckdb")

# run_daily_etl の実行（引数で id_token を渡せる）
result = run_daily_etl(conn)  # target_date を渡すことも可
print(result.to_dict())
conn.close()
```

2) ニュース収集ジョブ（既存の known_codes を渡して銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
conn.close()
```

3) ファクター / 研究用機能の利用例

```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d)
conn.close()
```

4) J-Quants クライアントを直接呼ぶ（テストや差分取得）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.config import settings

# settings.jquants_refresh_token により自動で id_token を取得
daily = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 主要 API の説明（簡潔）

- init_schema(db_path) -> DuckDB 接続
  - 全テーブルを作成する（冪等）

- run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - 市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック

- jquants_client.fetch_* / save_*
  - API 呼び出しと DuckDB 保存の低レイヤ実装

- news_collector.fetch_rss / save_raw_news / run_news_collection
  - RSS 取得・保存・銘柄紐付け

- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - 研究用ファクター計算と統計解析

- data.stats.zscore_normalize
  - クロスセクションの Z スコア正規化

---

## ディレクトリ構成（抜粋）

以下はパッケージ内部の主要ファイル / モジュール構成（src/kabusys 配下）です:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - news_collector.py              — RSS 収集・前処理・保存・銘柄紐付け
    - schema.py                      — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 公開 API（ETLResult 再エクスポート）
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - features.py                    — features の公開インターフェース
    - calendar_management.py         — 市場カレンダー管理・判定ユーティリティ
    - audit.py                       — 監査ログ（order_request / executions 等）初期化
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value 等
    - feature_exploration.py         — 将来リターン計算 / IC / サマリー
  - strategy/                         — 戦略関連（未実装枠 / 拡張ポイント）
  - execution/                        — 発注・ブローカ連携（未実装枠 / 拡張ポイント）
  - monitoring/                       — 監視用モジュール（拡張用）

---

## 注意点 / 運用上のヒント

- Python のバージョンは 3.10 以上を推奨します（typing の pipe 型などを使用）。
- J-Quants API のレート制御（120 req/min）やリトライロジックは jquants_client に組み込まれています。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）に依存します。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境を注入してください。
- DuckDB への INSERT は基本的に冪等 (ON CONFLICT) 設計です。外部から直接 DB を書き換える場合は整合性に注意してください。
- audit スキーマは UTC タイムゾーンを前提にしています（init_audit_schema は SET TimeZone='UTC' を実行します）。
- research モジュールは本番口座や発注 API にアクセスしない前提で設計されています（解析専用）。

---

## 拡張 / 貢献

- strategy / execution / monitoring ディレクトリは戦略実装やブローカ連携を統合するための拡張ポイントになっています。プルリクエストや Issue で提案を歓迎します。

---

もし README に含めてほしい具体的なコマンドやサンプル（CI ワークフロー、docker 化、cron ジョブ例、より詳細な .env.example 等）があれば教えてください。README をプロジェクトの style に合わせて調整できます。