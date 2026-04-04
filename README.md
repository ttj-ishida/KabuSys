# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants API を用いたデータ取得・ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレース）など、取引システム・リサーチ環境で必要となる機能群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時は継続）」で、安全かつ再現性の高いデータ処理と分析を目指しています。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクトで設定値にアクセス可能（例: settings.jquants_refresh_token）

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー取得）
  - 差分 ETL / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の統合エントリ run_daily_etl

- ニュース収集 / NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント（score_news）
  - マクロニュースの LLM 評価と ETF MA を組み合わせた市場レジーム判定（score_regime）

- リサーチ / ファクター
  - モメンタム、バリュー、ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化

- 市場カレンダー管理
  - market_calendar を用いた営業日判定・次営業日/前営業日の取得・夜間バッチ更新

- 監査（オーディット）
  - signal_events / order_requests / executions のテーブル定義、初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注フローを UUID ベースでトレース可能にするスキーマ

- ユーティリティ
  - DuckDB を使った保存（冪等 INSERT / ON CONFLICT DO UPDATE）
  - レートリミッター、リトライ（J-Quants / OpenAI への呼び出しで利用）
  - データ品質チェック（quality モジュール）

---

## セットアップ手順

前提: Python 3.10+（型アノテーションの union | を使用しているため）

1. リポジトリをクローン、パッケージをインストール（開発環境）
   - 推奨: 仮想環境を作成してから実行してください。
   - 例:
     ```
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate
     pip install -e ".[dev]"  # setup.cfg/pyproject に依存関係が定義されている想定
     ```
   - または最低限の依存:
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可能）。
   - 主要な環境変数（必須/任意）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - OPENAI_API_KEY (必須 for NLP) — OpenAI API キー（score_news / score_regime の呼び出しに必要）
     - KABU_API_PASSWORD (必須 for 実行系) — kabuステーション API のパスワード
     - KABU_API_BASE_URL (任意) — kabuステーションの base URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN (任意) / LINE_USER_ID (任意) — LINE 通知用
     - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
     - PID_FILE_PATH, KILL_FLAG_PATH, その他監視設定
     - KABUSYS_ENV — development/paper_trading/live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxx
     OPENAI_API_KEY=sk-xxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. データベース準備
   - DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。必要なディレクトリを作成してください（保存関数側でも自動作成される箇所あり）。
   - 監査用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な API）

以下は代表的な利用例です。関数はいずれも DuckDB 接続（duckdb.connect() の返り値）を第一引数に取ることが多いです。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- 株価差分 ETL（個別実行）:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- 財務データ ETL:
  ```python
  from kabusys.data.pipeline import run_financials_etl
  fetched, saved = run_financials_etl(conn, target_date=date(2026,3,20))
  ```

- 市場カレンダー更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュースの NLP スコア生成:
  - score_news は raw_news / news_symbols / ai_scores を使います。OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡します。
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
  ```

- 市場レジーム判定:
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルに書き込みます。
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- Zスコア正規化ユーティリティ:
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "ma200_dev"])
  ```

- 品質チェック（ETL 後に結果を確認したい場合）:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査テーブルの初期化（既存 DB にスキーマ追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

注意:
- LLM 呼び出し（score_news / score_regime）は OpenAI API の課金が発生します。テスト時は _call_openai_api 関数をモックできます（ドキュメント内にその旨コメントあり）。
- ETL / 研究関数はバックテストでのルックアヘッドバイアスにならないように設計されています（内部で date.today() を直接参照しない等）。

---

## 設定（Settings）一覧（主要項目）

Settings クラス（kabusys.config.settings）から取得可能な主な設定:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuステーション API 用パスワード（必須 for 実行）
- kabu_api_base_url: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id: LINE 通知関連（任意）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite（デフォルト data/monitoring.db）
- pid_file_path / kill_flag_path / kill_flag_clear_on_start: プロセス監視用設定
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct: 監視閾値
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

---

## ディレクトリ構成

以下はこのパッケージの主要なファイル・ディレクトリ構成の抜粋です（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                          — 環境設定読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP スコアリング（score_news）
    - regime_detector.py                — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント・保存処理
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETLResult 再エクスポート
    - calendar_management.py            — 市場カレンダー管理 / calendar_update_job
    - news_collector.py                 — RSS 収集（fetch_rss 等）
    - stats.py                          — Zスコア等統計ユーティリティ
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログスキーマ / init_audit_db
  - research/
    - __init__.py
    - factor_research.py                — モメンタム／バリュー／ボラティリティ等
    - feature_exploration.py            — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ などのモジュール群が公開 API を持ちます

---

## 注意点 / ベストプラクティス

- 機密情報（API キー等）は必ず環境変数または別管理の .env.local に置き、リポジトリにコミットしないでください。
- OpenAI 呼び出し・J-Quants 呼び出しはレート制限と課金に注意してください。テスト時は外部呼び出しをモックしてください。
- ETL / 研究コードはルックアヘッドバイアスに配慮して設計されていますが、バックテストで使用する際はデータのタイムスタンプ・fetched_at を確認して運用してください。
- DuckDB のバージョンによっては executemany の挙動やリストバインドの互換性に差異があるため、大きな括弧付きバインドを避ける実装（個別 DELETE 等）がなされています。DuckDB の互換性に注意してください。

---

この README はコードベース（src/kabusys）から生成した概要です。各モジュール内に詳細なドキュメント（docstring）が含まれているため、より詳細な使い方や引数仕様は該当モジュールの docstring を参照してください。必要であれば、利用する機能ごとのサンプルスクリプトや .env.example を追加で作成します。