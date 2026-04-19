README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤（プロトタイプ）です。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine（発注エンジン）と Monitoring（監視）用の起動スクリプト
- 発注・ポジションサイズ計算、ポートフォリオ構築の純粋関数群
- DuckDB / SQLite を使ったリサーチ・監視データ処理
- OpenAI を利用したニュース NLP（センチメント評価）および市場レジーム判定ユーティリティ
- ペーパートレード向け分離 DB、検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール

注: このコードは教育/リサーチ用途を想定しており、本番の資金投入前に十分なレビュー・テスト・監査を行ってください。

主要機能
--------
- Execution 起動 (run_execution.py)
  - 実際のブローカークライアントまたはモック（KABUSYS_ENV=paper_trading）で動作
  - paper_trading モードでは data/paper_trading.db（デフォルト）に分離して記録
  - リスク管理（Rate limit / Drawdown / 最大利用率 など）を組込んだ RiskManager

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの検出、データ鮮度チェック
  - TradeMonitor: 約定・滞留注文の監視（trade_logs 参照）
  - RiskMonitor: ハイウォーターマーク・ドローダウン、ポジション上限監視と kill switch 書き込み
  - MonitoringEngine: 各 Monitor をまとめてポーリング、アラート発行

- Portfolio 構成ライブラリ
  - 候補選定、等ウェイト / スコア加重、リスクベース・サイズ計算、セクター制限、レジーム乗数

- Research（DuckDB ベース）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリ等

- AI モジュール（OpenAI）
  - news_nlp.score_news: ニュース記事を集約し LLM で銘柄別センチメントを算出して ai_scores に保存
  - regime_detector.score_regime: MA 乖離 + マクロニュースで日次レジーム（bull/neutral/bear）判定
  - どちらも API キー（OPENAI_API_KEY）を必要とし、失敗時のフォールバックを備えています

- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL を判定

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt があれば:
     - pip install -r requirements.txt
   - 主要依存（例）:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の環境やバージョンはプロジェクトルートのドキュメントや requirements.txt に従ってください。

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 便利な設定（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — OpenAI を使う場合必須

   自動ロード:
   - 起動時にプロジェクトルートの .env, .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

使い方
------

1) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります:
     - python -m kabusys.validate_config --strict

2) 環境セットアップ（対話ウィザード）
   - python -m kabusys.config_setup
   - .env を生成または更新します。

3) ExecutionEngine（発注エンジン）起動
   - 本番/開発モードの切替は KABUSYS_ENV で指定:
     - KABUSYS_ENV=development（発注なし / 開発）
     - KABUSYS_ENV=paper_trading（Mock broker、paper DB を使用）
     - KABUSYS_ENV=live（実ブローカーへ発注）
   - 起動コマンド:
     - python -m kabusys.run_execution
   - 実行中に data/stop_requested.flag を作成すると安全に停止を促せます（起動時もチェック）。
   - Execution は PID ファイル（data/execution.pid）を書きます。

4) Monitoring（監視）起動
   - ポーリングで各監視を定期実行します（デフォルト 60 秒）:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で変更可能:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は Monitoring DB（settings.sqlite_path）へログを残します（環境にかかわらず本番 sqlite_path を使用する設計）。
   - 停止フラグ file: src の run_monitoring で参照している stop_requested.flag（data/stop_requested.flag）を作成して監視ループを終了できます。

5) ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能。

6) AI 関連（プログラム呼び出し）
   - news_nlp.score_news および regime_detector.score_regime はプログラムから呼び出せます（DuckDB 接続を渡す）。
   - 例（簡易）:
     - from datetime import date
       import duckdb
       from kabusys.ai.news_nlp import score_news
       conn = duckdb.connect("data/kabusys.duckdb")
       score_news(conn, date(2026, 4, 11), api_key="sk-...")
   - OPENAI_API_KEY を環境変数に設定すれば api_key を省略できます。
   - API 呼び出しはリトライやフェイルセーフを備えており、部分失敗時の DB 書き込み整合性にも配慮されています。

環境変数一覧（主要）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- PAPER_FILL_MODE — instant | partial | never | reject (paper_trading のマッチ挙動)
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- PID_FILE_PATH — Execution の PID ファイルパス（デフォルト data/execution.pid）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

ログ・ファイル・フラグの動作
----------------------------
- ログ:
  - デフォルトでは logs/<app_name>.log に日次ローテートで出力（TimedRotatingFileHandler）
  - コンソールには stdout に出力します
- Kill / Stop フラグ:
  - KillSwitch は条件が満たされると指定された kill.flag（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine は起動時などでこれを検知して停止します。
  - run_execution/run_monitoring は data/stop_requested.flag の存在を監視して実行ループを終了します。
- DB:
  - monitoring 用のスキーマは monitoring_db.init_monitoring_db で作成（冪等）
  - ペーパートレードは paper_sqlite_path に分離して記録されます

ディレクトリ構成
----------------
（主要ファイル/モジュールを抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装例がある場合)
  - execution/                 — 発注関連（BrokerFactory, Engine, OrderManager, Reconciler 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - （ユーティリティ群）

注意事項・ベストプラクティス
----------------------------
- 本番環境 (KABUSYS_ENV=live) では kill_flag_clear_on_start を 0 に設定することを推奨します（設定ミスで Kill Flag を消すと危険）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI API キーやブローカーの資格情報は安全に管理してください。
- DuckDB / SQLite の DB ファイルはバックアップ・アクセス制御に注意してください。
- 実環境での運用前に validate_config を実行し設定を確認してください。

貢献
----
バグ報告・修正・機能提案は Issue / Pull Request を通じて歓迎します。コードスタイル・テスト追加・ドキュメント改善の貢献も助かります。

ライセンス
---------
（このサンプルにはライセンス表記が含まれていません。実際のプロジェクトでは LICENSE を追加してください。）

問い合わせ
----------
内部での利用や導入支援が必要な場合はリポジトリの管理者へお問い合わせください。