# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（ミニマム実装）。

このリポジトリはデータ取得・ETL・品質チェック・監査ログ・カレンダー管理・ニュース収集など、戦略実行に必要な基盤機能を提供します。内部データストアには DuckDB を使用します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件・依存関係
- セットアップ手順
- 使い方（主要 API とサンプル）
- ディレクトリ構成
- 環境変数一覧（主な必須/任意キー）
- 補足・運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な「データ基盤」と「ETL / 品質チェック」および「監査・トレーサビリティ」を提供するライブラリ群です。J-Quants API や RSS ニュースフィードなどからデータを収集し、DuckDB に冪等的に保存します。さらに品質チェックやマーケットカレンダー管理、監査ログ用スキーマも備え、戦略層や実行層へデータを安全に供給します。

設計上のポイント：
- J-Quants API のレート制限 / リトライ / トークン自動リフレッシュに対応
- RSS ニュースの収集は SSRF 防御・XML 安全パース・レスポンスサイズ制限を実装
- DuckDB へは冪等保存（ON CONFLICT）でデータ重複を防止
- データ品質チェックを複数用意し、ETL 後の監査に利用可能

---

## 機能一覧

- 設定（環境変数）管理
  - .env / .env.local の自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
  - settings オブジェクト経由で型安全に値取得

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダー取得
  - 固定間隔レートリミッタ（120 req/min）
  - 再試行（指数バックオフ、最大 3 回）
  - 401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_*）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL 除去、空白正規化）
  - defusedxml での安全な XML パース
  - SSRF 対策（スキーム検証、リダイレクト検査、プライベートアドレス拒否）
  - レスポンスサイズ制限（デフォルト 10MB）
  - raw_news / news_symbols への保存（チャンク INSERT、INSERT ... RETURNING）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義
  - init_schema(db_path) による初期化（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー→株価→財務→品質チェックを順次実行
  - 差分更新（DB の最終取得日に基づく自動差分）
  - バックフィル（日数指定で後出し修正を吸収）
  - 品質チェック統合（kabusys.data.quality）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義
  - init_audit_db による監査専用 DB 初期化（UTC タイムゾーン固定）

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出
  - 前日比スパイク検出
  - 重複（主キー）検出
  - 日付整合性（未来日付、非営業日のデータ）検出
  - QualityIssue 型で問題を返却（severity: error/warning）

---

## 前提条件・依存関係

必須:
- Python 3.9+（コードに型注釈や一部標準ライブラリの使用を想定）
- DuckDB
- defusedxml

例（pip）:
pip install duckdb defusedxml

（実運用ではその他の依存関係やパッケージセットをプロジェクトの pyproject.toml / requirements.txt に記載してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows の場合は .venv\Scripts\activate

3. 依存関係をインストール
   pip install duckdb defusedxml

   （プロジェクトで配布する場合は pip install -e . 等を用意してください）

4. 環境変数の準備
   プロジェクトルートに .env または .env.local を作成します。自動的に読み込まれます（ただしテスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット）。

   最低限必要なキー（後述の「環境変数一覧」を参照）

5. DuckDB スキーマ初期化（例）
   Python REPL で:
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

   これで data/kabusys.duckdb（デフォルト）に全テーブルが作成されます。

---

## 使い方（主要 API とサンプル）

以下はライブラリの主要な利用例です。実際はアプリケーションのエントリポイントやバッチスクリプトから呼び出します。

- 設定の参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

- DB 初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数で target_date, id_token 等を渡せます
  print(result.to_dict())

- 市場カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)

- ニュース収集
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758"}  # など：有効な銘柄コードセットを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- 監査 DB 初期化（監査専用 DB を別途作る場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 品質チェック単体実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

- J-Quants から直接データ取得（テスト等）
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings の refresh token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)

---

## ディレクトリ構成

主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数 / .env の自動読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py           : J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py           : RSS 収集・前処理・DB 保存
    - schema.py                   : DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py                 : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      : マーケットカレンダー管理・営業日判定
    - audit.py                    : 監査ログスキーマ初期化（signal/order/execution）
    - quality.py                  : データ品質チェック
  - strategy/                      : 戦略モジュール用パッケージ（空の __init__）
  - execution/                     : 発注実行モジュール用パッケージ（空の __init__）
  - monitoring/                    : 監視モジュール（空の __init__）

---

## 環境変数一覧（主なキー）

必須（実行する機能に依存します）:
- JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン（get_id_token に利用）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（実行層が必要な場合）
- SLACK_BOT_TOKEN        : Slack 通知を使用する場合の Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : environment（development|paper_trading|live、デフォルト: development）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化する場合に 1 をセット

ヒント: .env.example を用意してコピーする運用が推奨です（このリポジトリでは実ファイルは含まれていません）。

---

## 補足・運用上の注意

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を探索して行います。テスト環境や特殊なセットアップ時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- J-Quants API 呼び出しは内部でレート制御とリトライを行いますが、外部で大量の並列リクエストを発生させないよう注意してください（API の公平利用）。
- RSS 収集は外部ネットワークにアクセスするため、ネットワークポリシー（プロキシ / ファイアウォール）や SSRF 防御に注意してください。news_collector には基本的な SSRF 防御が実装されていますが、運用環境のポリシーも確認してください。
- DuckDB に格納されたデータは永続化先のファイルパスに依存します。バックアップおよびアクセス制御（ファイル権限）を適切に設定してください。
- 監査ログ（audit）は削除しない前提で設計されています。処理のトレーサビリティ確保のため、運用上のアクセス権限管理を厳格にしてください。

---

必要に応じて README にサンプル .env.example、CI / デプロイ手順、より詳細な API リファレンスやユニットテストの実行方法を追記できます。追加で記載したい項目があれば教えてください。