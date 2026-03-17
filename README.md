# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
J-Quants API や RSS フィード等からデータを取得して DuckDB に蓄積し、ETL／品質チェックやニュース収集、監査ログを提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株自動売買システム向けのデータ基盤・ユーティリティ群です。  
主に以下を目的とします。

- J-Quants API から株価、財務、JPX カレンダーを安全に取得する（レート制御・リトライ・トークン自動更新）
- RSS などからニュースを収集して前処理・正規化し DuckDB に保存する（SSRF 対策・XML セキュリティ考慮）
- DuckDB 上に「Raw / Processed / Feature / Execution / Audit」層のスキーマを提供し、ETL パイプラインで差分更新する
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行う
- 発注〜約定の監査ログ（トレーサビリティ）用スキーマを提供する

設計で重視している点: 冪等性、安全性（SSRF・XML攻撃対策）、再現性（fetched_at 等の追跡）、テスト容易性。

---

## 主な機能
- J-Quants API クライアント（jquants_client）
  - 日足（OHLCV）/ 財務（四半期）/ マーケットカレンダー取得
  - API レート制御（120 req/min）・指数バックオフリトライ・401 時のトークン自動リフレッシュ
  - DuckDB へ冪等性のある保存関数（ON CONFLICT ... DO UPDATE）
- ニュース収集（news_collector）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト時の検査）
  - DuckDB へのまとめて保存（トランザクション・INSERT ... RETURNING）
- DuckDB スキーマ（schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema(db_path) で初期化可能
- ETL パイプライン（pipeline）
  - 差分取得（最終取得日から backfill を含めて再取得）
  - run_daily_etl によりカレンダー→株価→財務→品質チェックを順に実行
- カレンダー管理（calendar_management）
  - 営業日判定・前後の営業日探索・夜間カレンダー更新ジョブ
- 品質チェック（quality）
  - 欠損 / 重複 / スパイク / 日付不整合 を検出し QualityIssue を返す
- 監査ログ（audit）
  - signal / order_request / execution を追跡する監査用スキーマ群
  - init_audit_schema / init_audit_db を提供

---

## セットアップ手順（ローカルでの例）
1. Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール  
   本リポジトリに requirements.txt が無い想定のため、主要依存を個別に入れる例：
   - pip install duckdb defusedxml

   （実際のプロジェクトでは pyproject.toml や requirements.txt を参照してインストールしてください）

3. パッケージを開発インストール（リポジトリ直下に setup 構成がある場合）
   - pip install -e .

4. 環境変数の準備  
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を作成します（下記参照）。

5. DuckDB スキーマ初期化（例）
   Python REPL またはスクリプト内で:
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

6. 必要に応じて監査ログスキーマ初期化:
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

---

## 環境変数（.env の例）
自動ロード機能について:
- config モジュールはプロジェクトルートの `.env` と `.env.local` を自動で読み込みます（OS 環境変数優先）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

最低限必要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN=...      （J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD=...          （kabuステーション API パスワード）
- SLACK_BOT_TOKEN=...            （Slack 通知用 Bot Token）
- SLACK_CHANNEL_ID=...           （Slack チャンネル ID）

任意 / デフォルトあり
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL   （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1               （自動 .env 読み込みを無効化）
- KABUSYS_...（その他必要に応じて）

データベースパス（デフォルト）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

.env の最小例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## 使い方（代表的な呼び出し例）

- DuckDB スキーマの初期化
  - Python:
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）
  - Python:
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

  run_daily_etl は ETLResult を返します。各ステップは独立エラーハンドリングされ、品質チェック結果やエラー一覧を確認できます。

- ニュース収集ジョブ
  - Python:
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection
    conn = get_connection(settings.duckdb_path)
    known_codes = {"7203", "6758", ...}  # 必要なら銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)  # ソースごとの新規保存数

- カレンダー夜間更新ジョブ
  - Python:
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved:", saved)

- 監査スキーマのみ初期化
  - Python:
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn)

- J-Quants API を直接呼ぶ例
  - Python:
    from kabusys.data.jquants_client import fetch_daily_quotes
    quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    # fetch_* 関数はページネーション対応、ID トークンは自動でキャッシュ・更新されます

---

## 実装上の注意点 / 仕様の要点
- J-Quants API:
  - レート制限: 120 req/min（固定間隔スロットリングで制御）
  - リトライ: 指数バックオフ、最大 3 回（408/429/5xx 等）、401 はリフレッシュして1回リトライ
  - fetched_at を UTC で保存し、Look-ahead bias のトレースを容易にする
- news_collector:
  - XML の安全パース（defusedxml）を使用
  - レスポンスサイズや gzip 解凍後のサイズを制限して DoS 攻撃を緩和
  - リダイレクト時にスキーム・プライベートIPをチェックして SSRF を防止
- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution / Audit の 3 層（設計上の分類）を実装
  - ON CONFLICT を使った冪等保存を基本とする
- 品質チェック:
  - Fail-Fast ではなく全チェックを行い、呼び出し元が重大度に応じて判断する
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込む
  - テストなどで無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD が使える

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
  - パッケージ定義（version 等）

- config.py
  - 環境変数の読み込みと Settings クラス（必須変数取得、.env 自動ロード、KABUSYS_ENV/LOG_LEVEL 等）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ、token refresh）
  - news_collector.py
    - RSS フィード収集・前処理・記事保存・銘柄抽出（SSRF 対策、defusedxml）
  - schema.py
    - DuckDB の DDL 定義および init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（差分取得・保存・品質チェック、run_daily_etl）
  - calendar_management.py
    - マーケットカレンダー関連のユーティリティ（営業日判定、next/prev_trading_day、calendar_update_job）
  - audit.py
    - 監査ログスキーマ定義（signal_events / order_requests / executions）、init_audit_schema
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - その他: 複数の補助関数・型定義

- strategy/
  - __init__.py
  - （戦略関連の実装を格納する想定のモジュール群）

- execution/
  - __init__.py
  - （発注・約定・ブローカー連携に関する実装を格納する想定のモジュール群）

- monitoring/
  - __init__.py
  - （監視・メトリクス収集等の実装を格納する想定のモジュール群）

---

## 運用・デプロイの補足
- 日次処理は cron やワークフロー（Airflow 等）で run_daily_etl を呼び出す形で自動化可能。
- カレンダー更新は nightly バッチ（calendar_update_job）で定期実行推奨。
- 本番環境では KABUSYS_ENV=live、ログレベルや Slack 通知を適切に設定してください。
- DuckDB ファイルはバックアップ・スナップショットを定期的に取ることを推奨します。

---

この README はコードベースから抽出した利用方法・設計要点をまとめたものです。追加で「具体的なインストール手順（pyproject の利用）」「CI / デプロイ例」「サンプルデータでの動作確認手順」などが必要であればご指示ください。