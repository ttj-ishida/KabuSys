KabuSys — 日本株向け自動売買・データ基盤ライブラリ
================================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI）によるセンチメント評価、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含む統合ライブラリです。DuckDB をデータレイク／分析 DB として用い、J-Quants API と OpenAI（gpt-4o-mini）を利用する設計になっています。

設計上のポイント
- Look-ahead バイアスを避けるため、内部実装は datetime.today()/date.today() の直接参照を避け、呼び出し側から対象日を渡す設計になっています。
- ETL / 保存処理は冪等（ON CONFLICT / UPSERT）を意識しています。
- API 呼び出しはリトライ・バックオフ、レート制御、401 のトークン自動リフレッシュなど堅牢性を考慮。
- ニュース収集は SSRF 対策・XML 病対策（defusedxml）・サイズ制限など安全面に配慮。

主な機能一覧
- データ ETL（J-Quants 経由）
  - 株価日足（raw_prices / prices_daily）
  - 財務データ（raw_financials）
  - JPX 市場カレンダー（market_calendar）
  - 差分更新、バックフィル対応、品質チェック（quality モジュール）
- ニュース収集・前処理（news_collector）
  - RSS フィード取得、正規化、raw_news への冪等保存
- ニュース NLP（ai.news_nlp）
  - OpenAI を用いた銘柄別センチメント算出（ai_scores への保存）
- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の MA とマクロニュースの LLM スコアを組合せて日次レジーム判定（market_regime テーブル）
- 研究用ユーティリティ（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）算出、ファクター統計
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
- 設定管理（config）
  - .env/.env.local 自動ロード、環境変数経由の設定取得（settings オブジェクト）

セットアップ手順
----------------

前提
- Python 3.10+（ソースは型注釈に union operator 等を利用）
- ネットワーク接続（J-Quants / OpenAI）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - など（実行環境に合わせて requirements.txt を用意してください）

手順（ローカル開発の一例）
1. リポジトリ取得
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt があれば: pip install -r requirements.txt
   - 開発インストール（パッケージ化済みであれば）:
     - pip install -e .

4. 環境変数（.env）設定
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD: kabuステーション等のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/...

使い方（簡単なコード例）
---------------------

設定参照
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path などでアクセス可能

DuckDB 接続を作る
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行（株価・財務・カレンダー + 品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニューススコアリング（LLM）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照

市場レジーム判定（LLM + MA）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

監査スキーマ初期化
- from kabusys.data.audit import init_audit_db, init_audit_schema
- conn_audit = init_audit_db(settings.duckdb_path)  # :memory: も指定可能
- あるいは既存 conn に対して init_audit_schema(conn, transactional=True)

設定読み込み自動化の注意点
- .env.local は .env より後に読み込まれ、上書きされます。
- OS 環境変数はデフォルトで保護され、.env/*.local による上書きから除外されます。

ディレクトリ構成
----------------

（主要モジュールと役割）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング（ai_scores へ書き込み）
    - regime_detector.py     — マクロ + MA を使った市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント＋DuckDB 保存ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理ユーティリティ
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック（各種 QualityIssue を返す）
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログ用 DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

追加情報・運用上の注意
--------------------
- OpenAI 呼び出し
  - API エラー・レート制限へのリトライとフォールバック（失敗時は 0.0 を採用して処理継続）を実装していますが、コストとレート制限を考慮してください。
- J-Quants API
  - レート制限（120 req/min）をモジュール内で制御しています。リトライ時は指数バックオフを行います。
  - get_id_token によるトークン更新やキャッシュ処理を内部で行います。
- Look-ahead バイアス
  - 分析／バックテスト用途では、必ず過去時点のデータのみを DB にロードしてから評価してください（fetch_listed_info 等の関数は注意書きあり）。
- 自動 .env ロード
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env を自動ロードします。テスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

トラブルシューティング（よくある問題）
----------------------------------
- ValueError: OpenAI API キーが未設定
  - score_news / score_regime を実行する前に OPENAI_API_KEY を設定するか、api_key を関数に渡してください。
- ValueError: 環境変数が設定されていない
  - settings のプロパティは必須キーについて未設定だと ValueError を投げます。.env.example を参考に .env を作成してください。
- DuckDB のテーブルがない・DDL エラー
  - audit.init_audit_db / schema 初期化関数を使って必要テーブルを作成してください。

ライセンス・貢献
----------------
- この README はコードベースの説明を目的としています。実プロジェクトでの利用や配布に際してはライセンス表記や運用ルールに従ってください。貢献する場合は PR と issue を送ってください。

以上。動作確認や具体的な利用例（CI / cron ジョブでの ETL 定期実行、監視設定、Slack 通知フロー等）について必要であれば、さらに実運用向けの手順（systemd / cron / Dockerfile / Compose サンプルなど）を追記します。どの情報が欲しいか教えてください。