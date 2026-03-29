# KabuSys — 日本株自動売買システム（README）

KabuSys は日本株向けの自動売買 / データプラットフォーム用のライブラリ群です。  
データ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレーサビリティ）などのコンポーネントを提供します。

バージョン: 0.1.0

目次
- プロジェクト概要
- 主な機能
- 前提条件・依存関係
- セットアップ手順
- 環境変数（設定項目）
- 使い方（主要な利用例）
- ディレクトリ構成
- トラブルシューティング / 注意点

プロジェクト概要
- DuckDB をローカル DB として用い、J-Quants API から株価・財務・カレンダー等を取得して ETL を実行します。
- RSS ニュースを収集して raw_news テーブルに格納し、OpenAI（gpt-4o-mini）でニュースセンチメントを評価して ai_scores に書き込みます。
- ETF（1321）とマクロニュースの合成により市場レジーム（bull / neutral / bear）を日次でスコアリングします。
- 研究用途（ファクター計算、将来リターン、IC 計算、統計サマリー等）をサポートする関数群を提供します。
- 発注・約定の監査ログ用スキーマを提供し、完全なトレーサビリティを確保します。

主な機能
- データ ETL
  - run_daily_etl: 市場カレンダー・株価日足・財務データの差分取得と保存、品質チェック
  - 個別の ETL ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（自動トークンリフレッシュ、レート制御、リトライ）
- ニュース収集 & NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定（score_regime）
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアを合成
- 研究（research）
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
  - 汎用統計: zscore_normalize
- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合チェック
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- 設定管理（config）
  - .env/.env.local 自動読み込み（プロジェクトルート検出）と必須環境変数チェック

前提条件・依存関係（主要）
- Python 3.10+
- パッケージ（代表）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など

※ 実際のプロジェクトでは requirements.txt / Poetry 等で依存関係を管理してください。

セットアップ手順（開発環境での例）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - またはプロジェクトの requirements.txt / pyproject.toml があればそれを使用
4. パッケージをインストール（編集可能モード）
   - pip install -e .
5. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を置くと自動ロードされます。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

環境変数（主な設定項目）
- 認証・API
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注連携用）
- Slack 通知
  - SLACK_BOT_TOKEN: Slack Bot Token（必須）
  - SLACK_CHANNEL_ID: 通知対象チャネル ID（必須）
- データベースパス（デフォルト値）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 実行モード・ログ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: パッケージ起動時の .env 自動読み込みを無効化

使い方（主要 API と実行例）
- DuckDB 接続の準備
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- ETL（1日分の ETL を実行）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())
  - run_daily_etl は ETLResult を返し、品質問題やエラー情報を含みます。

- ニューススコアリング（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を省略すると環境変数 OPENAI_API_KEY を使用
  - print(f"scored {n} codes")

- 市場レジーム判定（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - r = score_regime(conn, target_date=date(2026,3,20), api_key=None)
  - # 戻り値は成功時 1、結果は market_regime テーブルに記録される

- 研究用関数（例: モメンタム算出）
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - records = calc_momentum(conn, target_date=date(2026,3,20))
  - # records は dict のリスト（各要素に date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # テーブルとインデックスが作成されます

- 設定（config）利用例
  - from kabusys.config import settings
  - settings.jquants_refresh_token
  - settings.duckdb_path

自動 .env ロードの動作
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順に読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします（ただし OS 環境変数は保護されます）。
- テストなどで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py: パッケージ定義（バージョン等）
  - config.py: 環境変数・設定管理（.env 自動読み込み、バリデーション）
  - ai/
    - __init__.py
    - news_nlp.py: ニュース NLP（score_news）
    - regime_detector.py: 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - etl.py: ETLResult のエクスポート
    - news_collector.py: RSS 収集・前処理（fetch_rss 等）
    - calendar_management.py: マーケットカレンダー管理（is_trading_day 等）
    - quality.py: データ品質チェック
    - stats.py: 統計ユーティリティ（zscore_normalize）
    - audit.py: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py: ファクター算出（momentum/value/volatility）
    - feature_exploration.py: 将来リターン / IC / summary / rank
- .env(.local) のサンプルはプロジェクトに .env.example を置く想定（config._require のメッセージ参照）

トラブルシューティング / 注意点
- OpenAI / J-Quants の API キーは必ず設定してください。未設定だと score_* 関数は ValueError を送出します。
- DuckDB の executemany に関する注意: 一部関数は空リストで executemany を呼ばないようにガードしています（DuckDB 互換性）。
- ニュース収集では SSRF 対策や受信サイズ制限が入っています。独自の RSS を追加する際は URL のスキームやホストに注意してください。
- ETL / API 呼び出しにはリトライ・レート制御が組み込まれていますが、レート上限を守るための追加制御が必要なケースがあります（多量の並列実行など）。
- 本ライブラリは「データ取得・研究用」「シミュレーション」に向けて設計されています。実際のフル自動売買で発注連携を行う場合は、追加の安全対策・監査・手動検証を行ってください（特に live 環境）。

ライセンスや貢献など
- この README にはライセンス情報は含まれていません。実際のリポジトリでは LICENSE ファイルを確認してください。

補足
- 実行例は Python API 呼び出しの形で示しています。将来的に CLI ツールやワークフロースケジューラ（cron / Airflow 等）から run_daily_etl を呼ぶ形で運用することが想定されています。

以上が本コードベースの概要と利用方法です。必要であればサンプルスクリプト（ETL 起動、ニューススコアリング、レジーム判定、監査 DB 初期化）を用意します。どの用途のサンプルが欲しいか教えてください。