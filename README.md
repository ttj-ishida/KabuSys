# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
DuckDB をデータレイク／特徴量格納に使い、J-Quants API や RSS を取り込み、特徴量算出から発注監査までの基盤処理を提供します。

主な設計方針：
- データ取得 → 加工 → 特徴量生成 → 発注管理 の 3 層＋監査レイヤを想定
- DuckDB を中心に冪等（ON CONFLICT）で保存
- J-Quants API はレート制御・リトライ・トークン自動更新を内蔵
- Research / Strategy 層は本番 API にアクセスしない（分析専用）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml`）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- データ取得 / 保存
  - J-Quants API クライアント（株価日足・財務・市場カレンダー取得）
    - レート制限（120 req/min）対応
    - リトライ（指数バックオフ）、401 でリフレッシュトークン自動更新
    - ページネーション対応
  - RSS ニュース収集器（SSRF 対策、トラッキングパラメータ除去、gzip 上限・デフューズドXML）
  - DuckDB 用スキーマ定義・初期化（raw / processed / feature / execution / audit 等のテーブル群）
  - ETL パイプライン（差分取得・backfill・品質チェック）
- データ品質チェック
  - 欠損・重複・スパイク（前日比）・日付不整合検出（QualityIssue 型で返却）
- 特徴量・リサーチ
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 監査（Audit）
  - シグナル→発注→約定までのトレース用監査テーブル群と初期化関数
- 発注 / 実行関連の雛形（execution/strategy/monitoring パッケージのプレースホルダ）

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒントに | を使っているため 3.10 以降を推奨）
- DuckDB を使用（pip でインストール）

推奨手順（仮想環境を使う）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトによっては他に logging/requests 等を追加で使うことがあります）

3. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置します。`src/kabusys/config.py` は自動でプロジェクトルートを探して `.env` を読み込みます（OS 環境変数 > .env.local > .env の優先順位）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API パスワード)
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - その他オプション:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視DB 等。デフォルト: data/monitoring.db)
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - 自動 env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化（DuckDB）
   - Python REPL などからスキーマを作成します（例は後述）。

---

## 使い方（サンプル／API）

以下は代表的な利用例です。実行前に環境変数と DuckDB パスが正しく設定されていることを確認してください。

1. DuckDB スキーマの初期化
   - 例:
     ```python
     import duckdb
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # 指定パスにファイルがなければディレクトリを作成して初期化
     ```

2. 監査データベース初期化（監査専用DBを用意する場合）
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

3. 日次 ETL の実行
   - 例:
     ```python
     from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)  # target_date を指定しないと今日の処理を実行（内部で営業日に調整）
     print(result.to_dict())
     ```

4. ニュース収集ジョブを実行（既知銘柄コードセットを渡して紐付け）
   - 例:
     ```python
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     known_codes = {"7203", "6758", "9433"}  # 例: 有効な銘柄リスト
     res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
     print(res)
     ```

5. J-Quants クライアントを直接使ってデータ取得
   - 例:
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

     token = get_id_token()  # settings.jquants_refresh_token を使って idToken を取得
     records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = save_daily_quotes(conn, records)
     ```

6. リサーチ用ファクター計算・IC
   - 例:
     ```python
     from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
     from datetime import date

     target = date(2024, 1, 31)
     mom = calc_momentum(conn, target)
     vol = calc_volatility(conn, target)
     val = calc_value(conn, target)
     fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
     ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
     summary = factor_summary(mom, ["mom_1m", "ma200_dev"])
     normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
     ```

7. データ品質チェック
   - 例:
     ```python
     from kabusys.data.quality import run_all_checks
     issues = run_all_checks(conn, target_date=target)
     for i in issues:
         print(i)
     ```

---

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- オプション（デフォルト値あり）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

.env ファイルの読み込み順:
- OS 環境変数（最優先）
- .env.local（存在すれば上書き）
- .env（最後に読み込まれる）

config モジュールはプロジェクトルートを .git または pyproject.toml を基準に探索して .env を読み込みます。プロジェクト配布後もカレントディレクトリに依存しません。

---

## 主要モジュール紹介（概要）

- kabusys.config
  - 環境変数管理、.env ファイルのパース／自動ロード
- kabusys.data.jquants_client
  - J-Quants API のラッパー（fetch / save 関数、認証、リトライ、レート制御）
- kabusys.data.news_collector
  - RSS 取得、前処理、記事ID生成、DuckDB 保存、銘柄抽出
- kabusys.data.schema
  - DuckDB の全スキーマ DDL 定義と初期化関数（init_schema / get_connection）
- kabusys.data.pipeline
  - ETL パイプライン（run_daily_etl, 個別 ETL ジョブ）
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.audit
  - 監査ログ用のテーブル定義・初期化（signal_events / order_requests / executions）
- kabusys.research
  - ファクター計算・統計ユーティリティ（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 発注・戦略・監視用のパッケージ（雛形、拡張用）

---

## ディレクトリ構成（主要ファイル）

（ソースのルートが `src/kabusys` の想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - (戦略ロジックを実装)
  - execution/
    - __init__.py
    - (発注/ブローカー連携)
  - monitoring/
    - __init__.py
    - (監視/アラート関連)

---

## 注意点・運用上のヒント

- DuckDB のファイルパスは共有ストレージ / バックアップ戦略を検討してください。:memory: も利用可能ですが永続性はありません。
- J-Quants API の利用にはトークン管理とレート制限遵守が必須です。本ライブラリは基本的な制御を行いますが、大量並列実行は避けるかユーザ側でも調整してください。
- ETL は各ステップで例外を局所的にハンドリングして継続する設計です。戻り値（ETLResult）で問題の有無を確認し、必要ならアラートや再実行の判断を行ってください。
- research モジュールの関数は prices_daily / raw_financials などの DB テーブルのみを参照し、本番の発注 API へはアクセスしないため、安全に解析が可能です。
- news_collector は外部 URL を扱うため SSRF / XML Bomb / 大きなレスポンスに対する保護を組み込んでいますが、運用環境のネットワークポリシーも見直してください。
- production 環境（KABUSYS_ENV=live）では、必ず Slack 通知・監査ログ・発注の安全性チェックを有効にしてください。

---

## 追加情報・拡張

- Strategy / Execution 層はプロジェクト固有のロジックに合わせて実装してください（ポジション管理、リスク制約、ブローカー API ラッパー等）。
- Feature 層（features テーブル）や AI スコア（ai_scores）はモデルに応じて拡張してください。
- テストを作成する際、config の自動 .env ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

---

ご不明点や README の追加項目（例: CI 用のセットアップ、サンプル .env.example、より詳細な API リファレンス）を希望される場合は教えてください。必要に応じてサンプルスクリプトや初期化手順を追記します。