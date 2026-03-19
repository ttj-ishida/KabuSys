# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータ層に採用し、J-Quants API からのデータ取得、ETL、品質チェック、特徴量生成、ニュース収集、監査ログなどの機能を提供します。

---

## プロジェクト概要

KabuSys は次の目的で設計されています。

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム / バリュー / ボラティリティ 等）の計算（Research 用）
- RSS ベースのニュース収集と記事⇄銘柄の紐付け
- 発注/監査ログ用スキーマ（監査トレーサビリティ）
- 設定は環境変数／.env で管理

「本番の発注処理」や「証券会社への発注」は別モジュール（execution 等）で扱う想定です。本リポジトリはデータ基盤と研究・特徴量計算に重点を置いています。

---

## 主な機能一覧

- data/
  - jquants_client：J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - schema：DuckDB スキーマ定義と初期化
  - pipeline：差分 ETL（価格 / 財務 / カレンダー）と日次 ETL エントリポイント
  - quality：データ品質チェック
  - news_collector：RSS 収集、正規化、DB保存、銘柄抽出
  - calendar_management：JPX カレンダー管理と営業日ロジック
  - audit：監査ログ（signal → order_request → executions のトレーサビリティ）
  - stats / features：Zスコア正規化などの統計ユーティリティ
- research/
  - feature_exploration：将来リターン計算・IC（Information Coefficient）・基本統計
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算
- config：環境変数読み込み・設定ラッパー（.env の自動ロード機能あり）
- monitoring, execution, strategy 等のプレースホルダーパッケージ

---

## セットアップ手順

前提：
- Python 3.9 以上（typing の挙動や型注釈に依存）
- DuckDB を利用可能な環境
- J-Quants API のリフレッシュトークン等の取得

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール
   （プロジェクトに pyproject.toml / requirements.txt がある想定。最低依存は duckdb, defusedxml）
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発用途:
   # pip install -e .
   ```

4. 環境変数 / .env を準備  
   プロジェクトルートの `.env` / `.env.local`（ローカル上書き）を自動的に読み込みます（config モジュールがプロジェクトルート（.git または pyproject.toml）を探索して読み込みます）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須は README 内で明示）:
   - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID（必須）
   - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで実行します。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルの親ディレクトリは自動作成されます
   # 監査ログ専用 DB を作る場合:
   # from kabusys.data import audit
   # audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要ユースケース）

以下は代表的な操作のサンプルです。各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取って処理します。

1. 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出に用いる有効な銘柄コードの集合（例: 証券一覧）
   res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
   print(res)  # {source_name: 新規保存件数}
   ```

3. ファクター計算（Research）
   ```python
   from datetime import date
   import duckdb
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

   conn = duckdb.connect("data/kabusys.duckdb")
   t = date(2025, 1, 10)
   momentum = calc_momentum(conn, t)
   volatility = calc_volatility(conn, t)
   value = calc_value(conn, t)
   forward = calc_forward_returns(conn, t, horizons=[1,5,21])
   # IC の例（factor_records と forward_records を code キーで照合）
   ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
   print("IC:", ic)
   ```

4. J-Quants API を直接呼んでデータを取得・保存する
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
   token = get_id_token()
   records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
   saved = save_daily_quotes(conn, records)
   print(saved)
   ```

5. Z スコア正規化ユーティリティ
   ```python
   from kabusys.data.stats import zscore_normalize
   normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
   ```

---

## 設定の挙動（.env 自動ロード）

- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動ロードします。
- ロード優先度: OS 環境変数 > .env.local > .env
- テストや特別な理由で自動ロードを無効にする場合、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数が欠けると Settings のプロパティアクセス時に ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。

---

## よく使う API 一覧（モジュール指針）

- kabusys.config.settings — 環境変数ラッパー（settings.jquants_refresh_token, settings.env, settings.is_live など）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化（冪等）
- kabusys.data.jquants_client — J-Quants API クライアント（fetch_*/save_*、get_id_token）
- kabusys.data.pipeline.run_daily_etl — 日次 ETL の実行（品質チェック含む）
- kabusys.data.news_collector.run_news_collection — RSS からのニュース収集 & DB 保存
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary — 研究用ファクター・分析ユーティリティ

---

## ディレクトリ構成

以下は主要ファイルの抜粋（リポジトリの src/kabusys 配下）。実際のツリーはリポジトリに依存しますが、本 README はコードベースに現れる構成を反映しています。

- src/
  - kabusys/
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
      - etl.py
      - quality.py
      - audit.py
      - audit.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 運用上の注意 / ベストプラクティス

- DuckDB ファイルはバックアップ・スナップショットを推奨。ETL 実行はトランザクション単位で行われますが、運用上のスナップショットは別途用意してください。
- J-Quants API のレート制限（デフォルト 120 req/min）に従う実装になっています。大量データの取得は時間をかけて行ってください。
- News Collector は SSRF 対策や XML 攻撃対策（defusedxml）を組み込んでいますが、外部フィード追加時は信頼性を確認してください。
- 本番発注（kabu など）を組み合わせる場合は、paper_trading 環境での十分な検証を行ってください（KABUSYS_ENV を活用）。

---

## 貢献・拡張

- 新たなファクターや品質チェック、ニュースソースの追加はモジュール毎の設計方針に沿って実装してください（各モジュールの docstring に設計方針が記載されています）。
- 発注/ブローカー統合は execution 層で扱う想定です。監査ログ（audit）を必ず保存するようにしてください。

---

必要でしたら、README の英語版、具体的な .env.example（テンプレート）、あるいはCI/CD 用の実行例（cron / Airflow 用タスク例）も作成します。どれを用意しましょうか？