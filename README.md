# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）・ニュース収集・AIベースのニュースセンチメント・市場レジーム判定・ファクター計算・データ品質チェック・監査ログなど、バックテスト／運用に必要な基盤機能を提供します。

主に DuckDB をデータレイクに、J-Quants API と OpenAI（gpt-4o-mini）を外部データソース／解析エンジンとして利用します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（OS 環境変数が優先）。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`。

- データ ETL（kabusys.data.pipeline）
  - J-Quants から株価（daily quotes）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存。
  - 品質チェック（欠損、重複、スパイク、日付不整合）を実行。
  - 日次 ETL の統合エントリ `run_daily_etl`。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制御・リトライ・トークン自動リフレッシュを実装。
  - fetch / save の各ユーティリティ（raw_prices / raw_financials / market_calendar / listed info）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存を想定。

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、将来日付・非営業日データ検出。

- 監査ログ（kabusys.data.audit）
  - signal → order_request → executions のトレーサビリティを保持する監査スキーマ定義と初期化ユーティリティ。

- 研究モジュール（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）。
  - 将来リターン、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ。

- AI（kabusys.ai）
  - ニュースの銘柄別センチメント付与（news_nlp.score_news）
  - マクロニュース + ETF(1321) MA200 を合成した市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しは JSON Mode を使い、堅牢なリトライ/フォールバック実装あり。

---

## 必要な環境変数

主要な環境変数（必須は README に明示）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合、関数呼び出し時に引数で指定可能）
- KABUSYS_ENV — 環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）

設定は OS 環境変数、またはプロジェクトルートの `.env` / `.env.local` に記述して読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（基本）

1. リポジトリをクローンします。

   git clone <repository-url>
   cd <repository>

2. 仮想環境を作成・有効化（例: venv）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストールします。

   - requirements.txt がある想定で:
     pip install -r requirements.txt

   - もしくはローカル編集版としてインストール:
     pip install -e .

   （このコードベースでは openai, duckdb, defusedxml などが利用されます）

4. 環境変数を設定する:
   - プロジェクトルートに `.env` を作成するか、OS 環境変数で設定します。
   - `.env` の例は `.env.example` を参照してください（プロジェクトにある場合）。

5. DuckDB 等の初期化（監査 DB など）:
   - Python REPL で以下を実行して監査スキーマを初期化できます。

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - または既存の DuckDB 接続に対して:

     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（主要ユーティリティの例）

以下は最小限のサンプルコード例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を作る（設定値からパスを取得）:

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（市場カレンダー・株価・財務を差分取得、品質チェック）:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースセンチメント（銘柄別）をスコアして ai_scores を書き込む:

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY は環境変数に設定するか api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジームを判定して market_regime テーブルへ書き込む:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化して使用する:

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対して監査用の INSERT/SELECT を行う

- 研究用ファクター計算例:

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  # z-score など
  from kabusys.data.stats import zscore_normalize
  recs_z = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])

注意:
- AI 呼び出し関数（score_news, score_regime）は OpenAI API キーを必要とします。関数引数で `api_key` を渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants API はレート制限・認証が必要です。`JQUANTS_REFRESH_TOKEN` を設定しておくことで自動で id_token を取得します。

---

## 環境変数読み込みの挙動

- 自動ロード順序: OS 環境変数 > .env.local > .env
- 自動ロードはパッケージ読み込み時に行われます（kabusys.config）。テスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の変数が参照されるとき（Settings のプロパティ経由）未設定の場合は ValueError が発生します。

---

## 注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止: 多くの関数は内部で現在日時を参照せず、明示的な target_date を受け取ります。バックテスト用途で過去のみを参照することを想定。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE 等で冪等に設計。
- フェイルセーフ: OpenAI API 失敗時や一部の品質チェックで致命的でない場合は処理を継続し、ログを残してフォールバックします。
- セキュリティ: RSS 収集は SSRF 対策や XML の安全パーシング（defusedxml）を実装。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント付与（OpenAI 経由）
    - regime_detector.py — マクロ + ETF を合成した市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 営業日判定 / カレンダー更新ジョブ
    - etl.py — ETL インターフェース（ETLResult）
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py — Zスコア等の統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py — RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / サマリー等

各モジュールは docstring に仕様・設計意図・リトライ・フェイルセーフ挙動が詳細に記載されています。実装に沿った利用を推奨します。

---

## 参考 / トラブルシューティング

- OpenAI の呼び出しがエラーになる場合は API キー確認、ネットワーク、リクエスト頻度を確認してください。ライブラリ側でリトライやフォールバック処理が入りますが、キー未設定時は例外になります。
- J-Quants API の 401 発生時は自動的にリフレッシュを試みます。`JQUANTS_REFRESH_TOKEN` の有効性を確認してください。
- DuckDB のバージョン依存（executemany の挙動など）がコード内に考慮されている箇所があります。問題が出る場合は DuckDB のバージョンを合わせてください。

---

この README はコードベースの要点をまとめたものです。詳細は各モジュールの docstring を参照してください。必要であれば、使い方サンプルや運用手順（ETL スケジューリング、Slack 通知設定、モニタリング）について追加で記載できます。必要なら指示してください。