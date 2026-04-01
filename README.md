# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。J-Quants / JPX などからのデータ取得、ETL、ニュース NLP（LLM を用いたセンチメント評価）、ファクター計算、監査ログ（オーダー追跡）など、一連のデータ処理・研究・監視機能を提供します。

主な用途の例:
- 日次 ETL（株価 / 財務 / カレンダー）の自動実行
- ニュース記事の銘柄別センチメント付与（OpenAI）
- 市場レジーム判定（MA200 と マクロニュースセンチメントの組合せ）
- ファクター計算／特徴量探索（研究用途）
- 監査ログ用 DuckDB スキーマ初期化

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須変数チェック）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得 / 保存（DuckDB）
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - レート制御・リトライ・トークンリフレッシュなど堅牢な HTTP 処理
- ETL パイプライン（差分取得 / バックフィル / 品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 汎用統計ユーティリティ（Z スコア正規化等）
- 監査ログスキーマ（signal → order_request → executions の追跡）
- DuckDB ベースの監査 DB 初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | None` を使用）
- Git（.env 自動読み込みでプロジェクトルートを特定するため）

1. リポジトリをクローン（例）
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)

3. 必要なパッケージをインストール
   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従って下さい。

4. 環境変数の設定
   プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます。
   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（代表的なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等を行う場合）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）

   任意（デフォルト値あり）
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

5. データディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 使い方（基本例）

以下はパッケージをインストール済みで、必要な環境変数が設定済みであることを前提とした Python からの呼び出し例です。

- 日次 ETL 実行例
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント付与（1 日分）  
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None なら OPENAI_API_KEY を参照
  print("scored:", count)

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以後 conn を使って監査テーブルにアクセスできます

- テスト／モックについて
  - OpenAI の呼び出し部分はモジュール内の _call_openai_api をモックする設計になっています（unittest.mock.patch などで差し替え可能）。
  - J-Quants クライアントの HTTP 部分も _request を中心として組まれているため、テストでは get_id_token や jq.fetch_xxx をモックして外部依存を排除できます。

---

## 環境変数（主な一覧）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知トークン（通知利用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知利用時）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注利用時）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）

オプション / デフォルトあり:
- KABUSYS_ENV (development / paper_trading / live) — 環境
- LOG_LEVEL (DEBUG/INFO/...) — ログレベル
- KABU_API_BASE_URL — kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

.env の自動読み込みルール:
- プロジェクトルートは .git または pyproject.toml を探索して決定
- 読み込み優先度: OS 環境変数 > .env.local > .env
- .env のパースはシェルスタイル（export KEY=val, quoted values, inline comments を考慮）

---

## 主要モジュールと使いどころ（要約）

- kabusys.config
  - Settings クラス経由で環境設定を取得。自動で .env をロードする仕組みと必須変数チェック。

- kabusys.data
  - jquants_client: J-Quants API 経由のデータ取得・DuckDB への保存（save_* 関数）。
  - pipeline: 日次 ETL （run_daily_etl 等）。
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）。
  - calendar_management: 取引日判定やカレンダー更新ジョブ。
  - news_collector: RSS 収集・前処理・冪等保存（SSRF 対策、XML 安全パース）。
  - audit: 監査ログテーブル定義・初期化ユーティリティ。

- kabusys.ai
  - news_nlp.score_news: 複数銘柄のニュースを LLM に投げて銘柄別スコアを生成し ai_scores に保存。
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とニュースセンチメントを組み合わせて市場レジームを判定・保存。

- kabusys.research
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算。
  - feature_exploration: 将来リターン計算、IC、統計サマリー等。
  - data.stats.zscore_normalize: クロスセクション Z スコア正規化。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - audit 初期化・監査 DB ユーティリティ
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research と data のユーティリティ群

（上記は主要ファイルを抜粋。実ファイル一覧はリポジトリの src/kabusys を参照してください）

---

## 注意事項 / 設計上のポイント

- Look-ahead Bias 防止:
  - AI や ETL の実装は内部で datetime.today() を直接参照せず、呼び出し側が対象日（target_date）を明示的に渡す設計です。バックテスト等で将来情報を使わないように注意されています。

- フェイルセーフ設計:
  - OpenAI や外部 API 呼び出しはリトライやフォールバック（例えばマクロセンチメント失敗時は 0.0）を行い、処理全体が停止しにくい設計になっています。

- テスト容易性:
  - OpenAI 呼び出し関数や一部のネットワーク I/O は内部のヘルパー関数をモック可能に設計されています（ユニットテストで差し替え推奨）。

- セキュリティ/安全対策:
  - RSS 収集で SSRF 対策、defusedxml による XML パース、安全な URL 正規化・トラッキング除去などが組み込まれています。
  - J-Quants の API 呼び出しはレート制御・トークンリフレッシュを備えています。

---

もし README に追加したい、あるいはサンプルスクリプト（systemd タスク、cron、Dockerfile、CI 設定等）のテンプレートが必要であれば、使用用途に合わせて追記します。