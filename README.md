# KabuSys

日本株向けの自動売買システム基盤ライブラリ（KabuSys）。  
データ取得・ETL、マーケットカレンダー管理、ニュース収集、ファクター計算、監査ログなどを含むモジュール群を提供します。  
本リポジトリはライブラリ層（研究・データ基盤・発注監査等）の実装を目的としています。  

---

## プロジェクト概要

KabuSys は次の目的を持つ Python モジュール群です：

- J‑Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化
- ETL パイプライン（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 研究向けファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索（forward returns, IC 等）
- 監査ログ（シグナル〜約定までのトレーサビリティ）用スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

パッケージは複数モジュールに分かれており、実際の発注処理は各ユーザーの実環境に合わせて実装する想定です。

---

## 主な機能一覧

- 環境変数管理
  - `.env` / `.env.local` の自動読み込み（OS 環境変数優先）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- Data レイヤ
  - J‑Quants API クライアント（rate limit・リトライ・ID トークン管理）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（run_daily_etl、差分取得・backfill 対応）
  - News RSS 収集（fetch_rss / save_raw_news / extract_stock_codes）と SSRF 対策
  - Calendar 管理（is_trading_day / next_trading_day / calendar_update_job）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ（signal_events / order_requests / executions）
- Research レイヤ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - 統計ユーティリティ（zscore_normalize）
- その他
  - ETL 実行結果クラス（ETLResult）で集約された情報を返却
  - DuckDB に対する冪等性を考慮した save_* 関数群

---

## 要件

- Python 3.10 以上（PEP 604 の型記法・型ヒントを使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （環境に応じて）requests 等を追加することも可能ですが、現状は標準ライブラリ + 上記を想定して実装されています。

インストール例（仮）：
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 本パッケージをローカルで開発インストールする場合
pip install -e .
```

---

## 環境変数（必須 / 推奨）

必須（アプリケーション起動時に必要）:

- JQUANTS_REFRESH_TOKEN — J‑Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API パスワード（発注を行う場合）
- SLACK_BOT_TOKEN — Slack 通知を用いる場合の Bot トークン
- SLACK_CHANNEL_ID — 通知を送る Slack チャンネル ID

オプション:

- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 `.env` 読み込みを無効化（値が存在すれば無効）

プロジェクトルートに `.env.example` を用意し、それをコピーして `.env` を作成してください（本 README の例では .env.example は別途作成する想定）。

.env ファイルの取り扱いについて:
- 自動読み込み順: OS 環境 > .env.local > .env（.env.local が優先）
- `export KEY=val` 形式やクォート付き値にも対応します

---

## セットアップ手順（概要）

1. Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` または `.env.local` を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化（data.schema.init_schema）
5. （任意）監査ログDBを初期化（data.audit.init_audit_db / init_audit_schema）
6. ETL を実行してデータを取り込む（data.pipeline.run_daily_etl 等）

サンプルコマンド（Python スクリプト内）:
```python
from kabusys.data import schema, pipeline
from datetime import date

# DuckDB 初期化（ファイル）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（今日分を取得）
res = pipeline.run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

監査ログ専用 DB を作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

カレンダー更新ジョブの例:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved", saved)
```

ニュース収集ジョブの例:
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードの集合（例: {'7203', '6758', ...}）
result = run_news_collection(conn, sources=None, known_codes=known_codes)
print(result)
```

---

## 使い方（主要な API の例）

- DuckDB スキーマ初期化:
  - kabusys.data.schema.init_schema(db_path)

- ETL（差分・backfill を含む日次 ETL の実行）:
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=..., id_token=..., run_quality_checks=True)

- J‑Quants データ取得（直接利用したい場合）:
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - 保存は save_* 関数群（save_daily_quotes, save_financial_statements, save_market_calendar）

- ニュース収集:
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - kabusys.data.news_collector.extract_stock_codes(text, known_codes)

- カレンダー:
  - kabusys.data.calendar_management.is_trading_day(conn, d)
  - next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn)

- 品質チェック:
  - kabusys.data.quality.run_all_checks(conn, target_date=..., reference_date=...)

- 研究モジュール（Research）:
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(conn, target_date)
  - kabusys.research.calc_ic(...)
  - kabusys.data.stats.zscore_normalize(records, columns)

基本的に各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り、テーブルを参照／更新します。Production 環境で発注を行う場合は、kabu ステーション等の外部 API と連携する execution 層を実装してください（本コードベースでは発注ロジックの骨組み・監査スキーマを提供しています）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys 配下）の主要ファイル一覧です。各モジュールは README の各セクションに対応した機能を提供します。

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / .env ローダー（Settings）
  - data/
    - __init__.py
    - jquants_client.py                  — J‑Quants API クライアント（rate limit, retry, save_*）
    - news_collector.py                  — RSS 収集・前処理・保存・銘柄抽出
    - schema.py                          — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                           — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                        — ETL パイプライン（run_daily_etl など）
    - features.py                        — 特色の公開インターフェース（zscore 再エクスポート）
    - calendar_management.py             — カレンダー管理 / calendar_update_job
    - audit.py                           — 監査ログスキーマ（signal_events, order_requests, executions）
    - etl.py                             — ETL の公開 API（ETLResult 再エクスポート）
    - quality.py                         — データ品質チェック（missing/spike/duplicates/date）
  - research/
    - __init__.py
    - factor_research.py                 — ファクター計算（momentum, volatility, value）
    - feature_exploration.py             — forward returns, IC, summary, rank
  - strategy/
    - __init__.py                        — 戦略層のエントリ（拡張ポイント）
  - execution/
    - __init__.py                        — 発注/ブローカ連携のエントリ（拡張ポイント）
  - monitoring/
    - __init__.py                        — 監視／メトリクス（拡張ポイント）

---

## 開発上の注意・設計方針（抜粋）

- 外部 API 呼び出しはレート制限とリトライ（指数バックオフ）を厳密に扱う（J‑Quants クライアント）。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識。
- NewsCollector は SSRF と XML Attack（defusedxml）を考慮して堅牢化。
- research モジュールは DuckDB の prices_daily / raw_financials のみを参照し、本番発注 API にアクセスしない設計。
- カレンダー未取得時は曜日ベースでフォールバックし、関数の振る舞いが一貫するように調整。

---

## 例：最小ワークフロー

1. DuckDB スキーマ初期化
2. 日次 ETL 実行
3. ファクター計算（研究用）

```python
from kabusys.data import schema, pipeline
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")

# ETL（市場カレンダ・株価・財務を取得）
res = pipeline.run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

# 研究: ファクター計算（今日）
mom = calc_momentum(conn, date.today())
vol = calc_volatility(conn, date.today())
val = calc_value(conn, date.today())

print(len(mom), len(vol), len(val))
```

---

## ライセンス / 貢献

本 README はコードベースの説明にフォーカスしています。ライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載のない詳細な使い方や拡張方法（発注連携、Slack 通知統合、運用ジョブのスケジュール等）については、必要に応じて追加ドキュメントを作成します。必要な箇所があれば教えてください。