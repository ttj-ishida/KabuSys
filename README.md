# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータ ETL、ニュース NLP、ファクター研究、監査ログ、および市場レジーム判定を含む自動売買／リサーチ基盤です。本リポジトリはバックテストや運用バッチ処理で利用できるコンポーネント群を提供します。

主な設計方針（抜粋）
- Look‑ahead bias を防ぐため、モジュールは可能な限り外部の現在時刻参照（date.today() 等）を避け、呼び出し側から対象日を渡す設計です。
- DuckDB をデータプラットフォームに採用し、SQL＋Python で効率的に集計・保存します。
- J-Quants / OpenAI / RSS 等外部 API に対してはリトライ・レート制御・フェイルセーフを組み込んでいます。
- 監査ログ（signal → order → execution のトレーサビリティ）を重視しています。

---

## 主要機能一覧

- データ取得・ETL
  - J-Quants から株価（日足）、財務、JPX カレンダーを差分取得・保存（jquants_client, pipeline）
  - ETL 実行結果を ETLResult として返却

- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出（data.quality）

- ニュース収集・NLP
  - RSS 収集と前処理（news_collector）
  - OpenAI を用いたニュースの銘柄別センチメントスコアリング（ai.news_nlp）

- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（ai.regime_detector）

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（research.factor_research）
  - 将来リターン、IC、統計サマリー等の特徴量探索（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats）

- 監査ログ（Audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化・管理（data.audit）
  - 監査 DB 初期化ユーティリティ（init_audit_db, init_audit_schema）

- マーケットカレンダー管理
  - JPX カレンダーの差分更新と営業日判定ユーティリティ（data.calendar_management）

---

## 必要な環境変数（主要）

以下は本コードベースが参照する主な環境変数です。実運用前に .env/.env.local 等で設定してください。

必須
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先チャネル ID
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector 実行時）

任意（デフォルトあり）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し .env → .env.local の順で自動読み込みします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

前提: Python 3.10+（型ヒントに union 表記や | を利用しています）、DuckDB、OpenAI の Python SDK 等が必要です。

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成と有効化
   python -m venv .venv
   source .venv/bin/activate  # (Windows) .venv\Scripts\activate

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   ※ 実際の requirements.txt はプロジェクトに応じて用意してください。
   追加で必要になる可能性のあるパッケージ:
   - slack-sdk（Slack 通知を行う箇所がある場合）
   - そのほか依存ライブラリ

4. .env を作成
   プロジェクトルートに .env（または .env.local）を作成して必須の環境変数を設定してください。例:

   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB（データベース）ファイルを準備
   デフォルトでは data/kabusys.duckdb を使用します。初期スキーマ作成はアプリ側ユーティリティ（data.schema.*）を使用してください（本コードリポジトリには schema 初期化のエントリポイントが複数あります。監査ログの場合は data.audit.init_audit_db を利用できます）。

---

## 使い方（代表的な呼び出し例）

以下は主要なユーティリティ関数の簡単な利用例です。実際はロギング、例外処理、ID トークン注入など環境に合わせてラッピングしてください。

- DuckDB に接続して日次 ETL 実行（run_daily_etl）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP（銘柄別スコア付与）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を利用
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB 初期化

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って発注履歴等を保存・参照する

- ユーティリティ（カレンダー判定など）

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

注意点
- OpenAI 呼び出しは API リトライやレスポンスバリデーションを施していますが、API キーが未設定だと ValueError を投げます。
- run_daily_etl などは ETL の各ステップで個別に例外を捕捉して継続する設計になっています。ETLResult に errors / quality_issues が格納されますので呼び出し元で確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化・バージョン定義
- config.py — 環境変数 / 設定管理（.env 自動読み込みロジック含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI 統合）
  - regime_detector.py — ETF + マクロニュース合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得/保存/認証/レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py — RSS 収集と raw_news 保存
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py — 監査ログ（監査テーブル DDL / 初期化）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリーなど
- monitoring, strategy, execution, ...（パッケージ __all__ で公開される名前空間に含める想定）

各モジュールはソース内に詳細な docstring と設計方針を記載しています。実装の挙動やフォールバックについては該当ファイルの docstring を参照してください。

---

## 運用上の注意

- データ品質: ETL 後は必ず quality.run_all_checks を用いて問題を検出・ロギングしてください。critical な問題は ETLResult.has_quality_errors で判定できます。
- API レート・課金: OpenAI / J-Quants の API 呼び出しは適切な課金・利用上限に注意してください（J-Quants はレート制限をコード内で制御）。
- セキュリティ: news_collector は SSRF 対策等を施していますが、外部エンドポイントへアクセスする際は社内ポリシーに従ってください。
- テスト: OpenAI 呼び出しやネットワーク IO 部分はテスト時にモック差し替え可能な設計になっています（例: aik の _call_openai_api を patch する等）。

---

もし README に追加してほしい項目（CI/テスト実行方法、requirements.txt、具体的な起動スクリプト、運用 runbook など）があれば教えてください。必要に応じてサンプル .env.example や簡易起動スクリプトも作成できます。