# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API と RSS 等からデータを収集し、DuckDB に蓄積、ETL（差分取得・品質チェック）やカレンダー管理、ニュース収集、監査ログ（発注〜約定のトレーサビリティ）をサポートします。

---

## 概要

KabuSys は以下を目的とする内部用ライブラリです。

- J-Quants API から株価（日足）・財務データ・市場カレンダーを安全に取得
  - レート制限厳守、リトライ、トークン自動リフレッシュなどを備えたクライアント実装
- RSS などからニュースを収集し前処理して DuckDB に保存（SSRF 対策・サイズ制限あり）
- ETL パイプライン（差分取得、バックフィル、品質チェック）を提供
- 市場カレンダーの管理（営業日判定、前後営業日検索、夜間更新ジョブ）
- DuckDB 上のスキーマ定義および監査ログ（order_request / executions 等）
- 品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント：
- Idempotent な DB 書き込み（ON CONFLICT を利用）
- Look-ahead bias を避けるために fetched_at / created_at を利用
- セキュリティ対策（XML の defusedxml、SSRF 対策、レスポンスサイズ制限 等）

---

## 主な機能一覧

- jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レートリミッタ、指数バックオフ、401 時のトークン自動リフレッシュ

- data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl：日次 ETL（差分取得 + 品質チェック）を一括実行

- data.schema
  - init_schema: DuckDB スキーマ（Raw / Processed / Feature / Execution 層）を初期化
  - get_connection: 既存 DB への接続取得

- data.news_collector
  - fetch_rss: RSS 取得＋前処理（URL除去、ホワイトスペース正規化）
  - save_raw_news, save_news_symbols: DuckDB への保存（チャンク・トランザクション）
  - extract_stock_codes: 本文から 4 桁銘柄コード抽出（既知の銘柄セットを使う）

- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job: 夜間バッチで市場カレンダーを更新

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks: 品質チェックの一括実行（QualityIssue を返す）

- data.audit
  - init_audit_schema / init_audit_db: 監査ログ（signal_events, order_requests, executions）用スキーマ初期化

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに PEP 604 の | を使用）
- ネットワークアクセス（J-Quants API、RSS など）

1. リポジトリをチェックアウト／配置（src レイアウト）
2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（最低限）:
   - pip install duckdb defusedxml
   - 追加でテストや運用で必要なパッケージがある場合は適宜インストールしてください。

4. 環境変数 (.env) を準備
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（コードで _require されているもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

.env の例:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易ガイド）

以下は Python REPL やスクリプトからの利用例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリが自動作成されます）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは環境変数から取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # オプションで target_date や id_token を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う既知コード集合（ある場合）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

5) 監査ログ用スキーマ初期化（追記）
```python
from kabusys.data.audit import init_audit_schema
# 既存 conn に監査テーブルを追加
init_audit_schema(conn, transactional=True)
```

補足:
- jquants_client の get_id_token を明示的に呼ぶこともできますが、fetch_* 系はデフォルトで内部トークンキャッシュを使い、401 時は自動リフレッシュします。
- ニュース収集は SSRF や XML 攻撃対策、レスポンスサイズの上限チェックを備えています。

---

## ディレクトリ構成

リポジトリ（src 配下）の主なファイル／モジュール:
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、設定値アクセス（settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 等）
    - news_collector.py
      - RSS 取得・パース・前処理・DuckDB 保存
    - pipeline.py
      - ETL パイプライン（差分取得、日次ジョブ）
    - schema.py
      - DuckDB スキーマ定義・初期化
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、next/prev 等）
    - audit.py
      - 監査ログ（signal / order_request / executions）スキーマ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py  （戦略モジュール置き場）
  - execution/
    - __init__.py  （注文実行・ブローカー連携の実装置き場）
  - monitoring/
    - __init__.py  （監視・メトリクス関連の実装置き場）

---

## 運用・開発上の注意

- 環境変数自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を探索し、.env / .env.local を自動で読み込みます。テスト時などに自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB 書き込みは冪等性を考慮していますが、外部から DB を操作した場合やスキーマを変更した場合は品質チェック（data.quality）や重複チェックを実行してください。

- ネットワークや API 呼び出しはレート制限・リトライ・サイズ制限等に対処していますが、本番運用ではログやメトリクス（例: 取得件数、失敗回数）を監視してください。

- Python バージョン互換性：このコードは Python 3.10+ を想定しています（PEP 604 型ヒント使用）。

---

## 参考・拡張案

- Slack 連携や通知（settings で Slack トークン/チャンネルを要求）を実装して ETL 結果や品質警告を通知する。
- execution 層にブローカー（kabuステーション等）との連携を実装し、audit テーブルと連携する。
- strategy パッケージに特徴量計算・シグナル生成ロジックを追加する。
- 単体テストや統合テストのために、_urlopen 等の外部アクセス箇所をモックする設計が既に想定されています。

---

この README はコードベースの主要機能と利用手順を簡潔にまとめたものです。細かい API 使用法やスキーマの詳細は各モジュール（src/kabusys/data/*.py）をご参照ください。必要であれば、具体的なユースケース（cron での ETL 実行例、systemd / container 化手順、CI 設定例 等）も追加で作成します。どの情報が必要か教えてください。