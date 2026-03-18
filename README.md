# KabuSys

日本株向けの自動売買・データプラットフォーム基盤ライブラリです。  
データ取得（J‑Quants）、DuckDBベースのデータスキーマ、ETLパイプライン、ニュース収集、ファクター／リサーチユーティリティ、監査ログ（発注トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダーなどの取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB によるデータレイヤ（Raw / Processed / Feature / Execution / Audit）のスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索（将来リターン、IC 計算、統計サマリ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

パッケージルート: `src/kabusys`（パッケージは PEP 形式でモジュール分割されています）。

---

## 主な機能一覧

- config
  - 環境変数読み込み（.env / .env.local、自動ロード。ルート判定は .git または pyproject.toml）
  - 必須設定の取得ユーティリティ（例: JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN 等）
- data
  - jquants_client: API クライアント（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（全テーブルとインデックス）
  - pipeline / etl: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出（SSRF 対策、gzip/サイズ制限、XML 安全化）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats / features: 統計・正規化ユーティリティ（Zスコア）
  - calendar_management: JPX カレンダーの管理（営業日判定 / next/prev / 夜間更新ジョブ）
  - audit: 監査ログ用テーブル群と初期化ユーティリティ
- research
  - factor_research: momentum / volatility / value ファクター計算
  - feature_exploration: 将来リターン計算、IC、サマリ、ランク関数

---

## セットアップ手順（開発環境向け）

※プロジェクトに requirements ファイルが無い場合は最低限の依存を明示します。必要に応じて追加してください。

1. Python 仮想環境の作成（例）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   実運用ではログ周りや HTTP クライアント（requests 等）、Slack 通知等の依存を追加してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN (必須) — Slack ボットトークン
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（DuckDB）
   - Python REPL またはスクリプトで実行:
     ```python
     import duckdb
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
     ```
   - 監査ログ専用 DB を使う場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要ユースケース）

以下は代表的な呼び出し例です。詳細は各モジュールの docstring を参照してください。

1. ETL（日次パイプライン）の実行
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 市場カレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("saved:", saved)
   ```

3. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は記事中の 4 桁銘柄コード抽出に使う有効銘柄セット
   known_codes = {"7203", "6758", "9984"}
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

4. J-Quants から生データ取得（テスト等）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   ```

5. ファクター / リサーチ
   ```python
   from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary
   from datetime import date

   # DuckDB 接続を渡して計算
   momentum = calc_momentum(conn, date(2024,1,31))
   forward = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
   ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
   summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
   ```

6. 設定の取得
   ```python
   from kabusys.config import settings
   token = settings.jquants_refresh_token
   duckdb_path = settings.duckdb_path
   is_live = settings.is_live
   ```

---

## 環境変数と自動 .env ロードの挙動

- 自動ロード対象ファイル: プロジェクトルートの `.env`（上書きなし）、`.env.local`（上書き許可）。プロジェクトルートは当該ファイルから親方向に `.git` または `pyproject.toml` を探して決定されます。
- テストなどで自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 必須変数が参照された場合（Settings のプロパティ呼び出し）、未設定だと ValueError を投げます。`.env.example` を参考に必要な変数を用意してください。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - features.py
      - stats.py
      - quality.py
      - calendar_management.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（詳細ファイルは README 上部の「機能一覧」に挙げたとおり）

---

## 運用上の注意 / 設計方針（要点）

- J-Quants API のレート制限（120 req/min）に対応するため固定間隔スロットリングとリトライ実装が組み込まれています。
- API から取得した生データは fetched_at を付け、Look‑ahead bias を追跡可能にしています。
- DuckDB への保存は冪等（ON CONFLICT）で行うことを想定。
- ニュース収集では SSRF 対策、XML の脆弱性対策（defusedxml）、受信サイズ制限、トラッキングパラメータ除去などを実施しています。
- 市場カレンダーのデータがある場合は DB の値を優先し、ない場合は曜日ベースのフォールバック（平日＝営業日）を使用します。
- 監査ログ（audit）を用いることで signal → order → execution のトレーサビリティを保証できます（全時刻は UTC 保存）。

---

## 貢献 / 拡張案

- Slack 通知・監視用の監視ジョブ / CLI ラッパーの追加
- strategy モジュールでの戦略定義とポジション管理ロジックの実装
- kabu ステーション連携（execution 層）の実装と実運用モードのテスト
- CI による品質チェック（flake8 / mypy / unit tests）追加

---

必要に応じて README に追記します。たとえば、実運用用の依存リスト（requirements.txt）、CLI／systemd ジョブの設定例、.env.example のテンプレートなどを追加できます。どれを優先して追加しますか？