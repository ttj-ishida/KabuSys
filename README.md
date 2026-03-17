# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
J-Quants API や RSS フィードからのデータ取得、DuckDB によるスキーマ定義・ETL、ニュース収集、データ品質チェック、監査ログ（発注→約定トレース）などの基本機能を提供します。

## 主な機能
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX 市場カレンダーの取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
  - DuckDB への冪等保存（ON CONFLICT で更新）

- ニュース収集（RSS）
  - RSS から記事取得、URL 正規化（トラッキングパラメータ除去）、SHA-256 を用いた記事ID生成（先頭32文字）
  - SSRF 対策（スキーム検証・プライベートアドレス検出・リダイレクト検査）
  - レスポンスサイズ制限 / gzip 解凍検査（DoS 対策）
  - DuckDB に冪等保存（INSERT ... RETURNING）と銘柄コード抽出・紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層にわたるテーブル群とインデックスを定義
  - 監査ログ用スキーマ（signal_events / order_requests / executions 等）を別途初期化可能

- ETL パイプライン
  - 差分取得（最終取得日からの差分、バックフィルオプション）
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）

- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付整合性チェック
  - 問題は QualityIssue オブジェクトとして収集（error / warning）

- 監査ログ（トレーサビリティ）
  - シグナル→発注要求→約定まで UUID をチェーンして追跡可能
  - 発注要求は冪等キー（order_request_id）をサポート

---

## 必要な環境変数
アプリケーションは環境変数（または .env ファイル）から設定を読み込みます。主なキーは以下の通りです。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用途）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

自動的に .env, .env.local をプロジェクトルートから読み込みます（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の読み込み挙動:
- まず OS 環境変数を保持しつつ .env を補完（既存変数は上書きしない）
- 次に .env.local を読み込み、.env の設定を上書き。ただし OS 環境変数は保護され上書きされない

---

## セットアップ手順（開発環境向け）
1. Python 3.9+ をインストール
2. リポジトリをクローンし、プロジェクトルートに移動
3. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
4. 依存パッケージをインストール
   - 必須（少なくとも）: duckdb, defusedxml
   - 例: pip install duckdb defusedxml
   - （将来的に requirements.txt や poetry を用意してください）
5. 環境変数を設定（またはプロジェクトルートに .env を作成）
   - 例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

---

## 使い方（主要 API と実行例）

以下は Python REPL やバッチスクリプト内での利用例です。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 監査ログ（発注トレース）スキーマ初期化（既存接続に追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- 日次 ETL の実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 戻り値は ETLResult（フェッチ数／保存数／品質問題等を含む）

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出時に有効なコードセット（例: CSV から読み込んだ全銘柄）
  stats = run_news_collection(conn, sources=None, known_codes=known_codes_set)

- J-Quants トークン取得（通常は内部で処理される）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得

- 生データ保存関数の直接利用（テストやバッチ用）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  recs = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
  save_daily_quotes(conn, recs)

- 品質チェックの個別実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=some_date)

注意点:
- run_daily_etl は内部でカレンダー取得→株価取得→財務取得→品質チェックを順に実行します。各ステップは独立してエラーハンドリングされ、可能な限り処理を継続します。結果は ETLResult で返されます。
- HTTP リクエストはタイムアウトやリトライ制御、レート制限に配慮しています。
- ニュース収集では SSRF、XML インジェクション、Gzip Bomb などに対する防御を組み込んでいます。

---

## ディレクトリ構成（主要ファイル）
（リポジトリ内の src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数と設定管理（.env 自動読み込み・検証）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py        — RSS ニュース収集・前処理・DB保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py              — ETL パイプライン（差分更新、run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理・営業日判定ユーティリティ
    - audit.py                 — 監査ログ用スキーマ初期化（signal/order/execution）
    - quality.py               — データ品質チェック（欠損、スパイク、重複、日付整合性）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

この README はコードベースの機能概要と利用方法の抜粋です。実運用では以下点も検討してください:
- 実行環境（paper_trading / live）に応じた設定の切り替え
- secrets の安全な管理（環境変数・Secrets Manager 等）
- 定期ジョブ（cron / Airflow / systemd timer 等）による ETL・カレンダー更新・ニュース収集の自動化
- ロギング・監視・アラート（Slack 通知等）の導入

必要であれば、サンプル .env.example、CI 用の簡単な起動スクリプト、または各モジュールの詳細な使い方（関数の引数説明・例）を追加します。どの情報が欲しいか教えてください。