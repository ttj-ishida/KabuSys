KabuSys — 日本株自動売買システム（README 日本語版）
================================

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、AI を利用したニュース解析、及び自動売買/監視のための共通ライブラリ群です。主に以下を提供します。

- J-Quants からのデータ取得／ETL（株価・財務・市場カレンダー）
- ニュースの収集と LLM による銘柄センチメント評価（news_nlp）
- 市場レジーム判定（regime_detector）
- ファクター計算・特徴量解析（research）
- データ品質チェック、監査ログ（audit）とトレーサビリティ
- 環境設定管理（settings）

設計上のポイント
- ルックアヘッドバイアス防止（target_date を明示、内部で date.today() を直接参照しない等）
- DuckDB を用いたローカルデータベース中心の処理
- OpenAI（gpt-4o-mini）を利用した JSON mode を使った堅牢な LLM 呼び出し（リトライ、フォールバックあり）
- ETL/保存処理は冪等性を重視（ON CONFLICT / UPDATE など）

主な機能一覧
--------------
- data.jquants_client: J-Quants API クライアント（取得・保存・トークン管理・レート制御）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）
- data.news_collector: RSS からのニュース収集と前処理
- data.quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
- data.calendar_management: 市場カレンダー管理 / 営業日判定
- data.audit: 監査ログ（signal / order_request / executions）スキーマ初期化
- ai.news_nlp: 銘柄ごとのニュースセンチメントスコア生成（score_news）
- ai.regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成する市場レジーム判定（score_regime）
- research.*: ファクター計算（momentum / volatility / value）および特徴量解析ユーティリティ
- config.settings: .env / 環境変数の管理と取得

前提条件
--------
- Python 3.10+
- 必要なパッケージ（概略）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリのみで多くの処理を実装（外部依存最小化の設計）

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 開発中は editable install を推奨:
     pip install -e .

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに .env（および .env.local）を配置すると自動で読み込まれます（デフォルト）。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須 / 推奨の環境変数
--------------------
主なキー（config.Settings により参照）:

必須（未設定時は例外）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード（必要に応じて）

任意（デフォルトあり／空文字許容）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

システム設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

使い方（簡易例）
----------------

以下は最小限の Python 例です。事前に .env 等で必要な環境変数を設定してください。

1) DuckDB に接続して日次 ETL を実行する（run_daily_etl）
- 目的: 株価・財務・カレンダーを J-Quants から差分取得・保存し品質チェックを実行

例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())

2) ニュースセンチメント（銘柄ごとの ai_scores 生成）
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照

例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {count} codes")

3) 市場レジーム判定（ETF 1321 とマクロニュースを合成）
- ai.regime_detector.score_regime(conn, target_date, api_key=None)

例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))

4) 監査ログ DB 初期化
- data.audit.init_audit_db(path) で監査用 DuckDB を初期化（UTC タイムゾーン等を設定）

例:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

5) 市場カレンダー更新ジョブを実行
- data.calendar_management.calendar_update_job(conn, lookahead_days=90)

例:
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")

注意点 / 設計上の挙動（要点）
-------------------------
- LLM 呼び出しは JSON mode を使用し、レスポンスのバリデーションを厳密に行います。
- API エラー時はリトライ（指数バックオフ）し、最終的にフォールバック値を用いることで処理継続を保証します（例: macro_sentiment が API 問題で 0.0 にフォールバック）。
- ETL は差分取得（最終取得日からの差分）とバックフィルをサポートし、ON CONFLICT を用いた冪等保存を行います。
- テスト時に自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみを抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / settings
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP / score_news
  - regime_detector.py             — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（取得 / 保存）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py              — RSS 取得・保存
  - quality.py                     — データ品質チェック
  - calendar_management.py         — 市場カレンダー管理
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - audit.py                       — 監査ログスキーマ / init_audit_db
- research/
  - __init__.py
  - factor_research.py             — momentum/value/volatility
  - feature_exploration.py         — forward_returns, calc_ic, factor_summary, rank
- monitoring/ (存在が想定されるが省略)
- strategy/ (存在が想定されるが省略)
- execution/ (存在が想定されるが省略)

補足: .env パース仕様（重要）
----------------------------
- .env / .env.local はプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みされます（デフォルト有効）。
- export KEY=val 形式にも対応。
- シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を解釈します。
- コメント処理: クォートなしの値内では "#" の直前がスペース／タブの場合に以降をコメントとみなします。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

よくある運用ワークフロー
-----------------------
1. .env を用意して JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等を設定
2. DuckDB のパス（DUCKDB_PATH）を設定
3. run_daily_etl をスケジューラー（cron / Airflow 等）で nightly 実行
4. ETL 後に score_news / score_regime を実行して AI スコア・レジームを更新
5. strategy 層でシグナルを生成、order_requests / executions を監査テーブルに残す

貢献・ライセンス
-----------------
（このリポジトリの CONTRIBUTING、LICENSE は別途参照してください。）

問い合わせ
----------
実装上の質問や利用時の不明点があれば、該当モジュール（例: kabusys.data.jquants_client、kabusys.ai.news_nlp）を参照していただき、必要に応じて issue を作成してください。

以上。必要であれば README に記載する .env.example のテンプレートや、より詳細な運用手順（systemd, supervisor 用の起動スクリプトや具体的な cron 設定例）も作成します。どの情報を追加しますか？