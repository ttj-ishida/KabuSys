KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・調査・監視を目的とした Python コードベースです。  
主な機能は以下の通りです。

- 戦略に基づく銘柄選定・配分・株数決定（portfolio）
- ファクター計算・特徴量探索（research）
- 実際の発注処理・注文管理・リコンシリエーション（execution）
- 監視・アラート・Kill Switch（monitoring）
- ニュース NLP によるセンチメント評価・レジーム判定（AI）
- Paper Trading 検証レポート / Streamlit ダッシュボード などのツール

機能一覧
--------
主なモジュールと役割（抜粋）：

- kabusys.config
  - .env 自動読み込み機構。環境ごとの設定（KABUSYS_ENV=development|paper_trading|live）を管理。
- kabusys.portfolio
  - 銘柄選定（select_candidates）、重み計算（等金額／スコア重み）、ポジションサイズ計算（単元丸め・リスク制限）、セクター上限・レジーム乗数。
- kabusys.research
  - ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン計算、IC（Spearman）や統計サマリ。
- kabusys.ai
  - news_nlp.score_news: OpenAI を使ってニュース記事を銘柄別にセンチメント評価して ai_scores に書き込む。
  - regime_detector.score_regime: ETF の MA とマクロニュースを統合して市場レジーム（bull/neutral/bear）を判定して DB に書き込む。
- kabusys.execution
  - OrderManager, Reconciler: 注文の作成・送信・同期、再起動時の自動リコンシリエーション。
  - ExecutionEngine 起動スクリプト（run_execution.py）。
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine：定期ポーリングによるログ記録とアラート送信。
  - AlertManager：LINE Push による通知（オプション）。
  - KillSwitch：フラグファイルによる ExecutionEngine 停止シグナル。
  - Streamlit ダッシュボード（streamlit_dashboard.py）。
- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ。

セットアップ手順
--------------
1. Python バージョン
   - Python 3.10 以上を推奨（コードは型合併演算子などを使用しています）。

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - その他（標準ライブラリ: sqlite3 等）
   例: pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに requirements.txt がある場合はそれを使用してください。

3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。  
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE: paper_trading 時の模擬約定モード ("instant"|"partial"|"never"|"reject")
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用）

4. データディレクトリ
   - デフォルトで data/ 以下に DB や flag ファイルを置きます。実行前にディレクトリを作成してください:
     mkdir -p data

使い方
------

基本的な実行例

- ExecutionEngine（本番・ペーパートレード）
  - run_execution.py をモジュール実行:
    python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に書き込む（本番 DB と分離）。
    - プロセスの優先度を "high" に設定します（psutil による試行、失敗時は警告）。

- Monitoring（SystemMonitor の単体起動）
  - run_monitoring.py をモジュール実行:
    python -m kabusys.run_monitoring
  - オプション / 環境変数:
    - MONITOR_POLL_INTERVAL: ループのポーリング間隔（秒）。デフォルト 60。0 以下や不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視ログの一元化）。

- Streamlit ダッシュボード（監視）
  - 実行例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - 実行例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 使用 DB:
    --db オプション、環境変数 PAPER_TRADING_SQLITE_PATH、またはデフォルト data/paper_trading.db の優先順で解決されます。
  - レポートでは稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL を判定します。

- AI モジュール
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キー（引数または OPENAI_API_KEY 環境変数）が必須。
    - raw_news / news_symbols / ai_scores テーブルを参照・更新します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - OpenAI を使ったマクロセンチメントと ETF MA によるレジーム判定を market_regime テーブルへ書き込みます。
  - 実行には OpenAI の利用料が発生します。API レート制限・エラーはリトライロジックで扱われ、最終的にフォールバックする実装が施されています。

注意点 / 補足
- .env のパーシングはシェル風の簡易ルールに準拠（export あり、クォート処理、末尾コメント扱い等）。
- MonitoringDB は init_monitoring_db() で必要なテーブル・インデックスを冪等に作成・マイグレーションします（例: peak_value, latency_ms カラム追加）。
- process priority の設定はプラットフォーム依存（Windows / POSIX 対応）で、権限不足時には警告を出してスキップします。
- Paper Trading と本番の DB は明示的に分離されます（paper_trading モードは data/paper_trading.db を使用）。

ディレクトリ構成（抜粋）
--------------------
以下は src/kabusys 配下の主要ファイル/パッケージ概要（省略あり）:

- src/
  - kabusys/
    - __init__.py             — パッケージ定義（__version__ 等）
    - config.py               — 環境変数 / .env ロード / Settings
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor 単体起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py   — プロセス優先度・CPU affinity ユーティリティ
    - portfolio/
      - __init__.py
      - portfolio_builder.py  — 候補選定・重み計算
      - position_sizing.py    — 株数決定・配分・スケールダウン
      - risk_adjustment.py    — セクターキャップ・レジーム乗数
    - research/
      - __init__.py
      - factor_research.py    — momentum / volatility / value
      - feature_exploration.py— forward returns / IC / summary
    - ai/
      - __init__.py
      - news_nlp.py           — ニュース NLP（OpenAI）によるスコアリング
      - regime_detector.py    — レジーム判定（ETF MA + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py      — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py     — システム状態・データ鮮度
      - trade_monitor.py      — 注文滞留・約定異常
      - risk_monitor.py       — ドローダウン・ポジション上限監視
      - kill_switch.py        — フラグファイルによる停止シグナル
      - alert_manager.py      — LINE Push 通知
      - monitoring_engine.py  — 各 Monitor を束ねる Engine
      - streamlit_dashboard.py— Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, risk_manager など)
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成

貢献 / 開発メモ
----------------
- .env.example を用意して最低限必要な環境変数を示すことを推奨します（本コードベースでは .env.example は示していませんが、Settings._require() の指示に従って作成してください）。
- AI 呼び出し部分はネットワーク不安定や 429 に対するリトライ実装があるものの、API キー/課金/レートには注意してください。
- DB スキーマは init_monitoring_db() で管理されます。将来のスキーマ変更はマイグレーションロジックを追加してください。

ライセンス / 著作権
------------------
（ここにライセンス情報を追記してください。コードベースに既にライセンスファイルがある場合はそれを参照してください。）

以上。必要に応じて .env のサンプルや requirements.txt、実行例スクリプトを追加できます。追加を希望する場合は具体的な内容（例: .env サンプル、推奨 Python バージョン、requirements.txt の内容など）を教えてください。