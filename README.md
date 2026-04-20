KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。
主要機能（マーケットデータ集計・ファクター計算・ポートフォリオ構築・ポジションサイジング・発注エンジン・監視・AIニュース解析）をモジュール化して提供します。
本リポジトリ内にある CLI スクリプトや関数群を組み合わせることで、ローカル開発・ペーパートレード・本番運用のワークフローをサポートします。

主な特徴
--------
- 実行環境切替: development / paper_trading / live を環境変数 KABUSYS_ENV で切替
- 発注エンジン (ExecutionEngine): 本番 API とペーパートレード（モック）を切替可能
- 監視サブシステム: System / Trade / Risk の監視、Kill Switch、通知フック
- 研究用モジュール: ファクター計算、将来リターン計算、IC 計測、統計サマリ
- ポートフォリオ構築: 候補選定・配分計算・リスク調整・数量決定（単元丸め対応）
- AI モジュール: OpenAI を用いたニュースセンチメント評価と市場レジーム判定
- ログ: stdout および日次ローテートファイル（logs/<app>.log）
- DB: DuckDB（分析用）と SQLite（監視・発注ログ）を併用

必要な環境変数（主なもの）
-------------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に関係する主なオプション:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能を使う場合に必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- PID_FILE_PATH, KILL_FLAG_PATH — 各種フラグ / PID ファイル位置
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード (instant|partial|never|reject)

セットアップ手順
--------------
1. Python 環境を準備（推奨: venv を利用）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合: 少なくとも duckdb, psutil, openai が必要です。
     例: pip install duckdb psutil openai PyYAML

3. 初期 .env 作成（対話ウィザード）
   - python -m kabusys.config_setup
   これにより .env を対話的に生成できます。生成後は必須環境変数が正しく設定されていることを確認してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

5. ディレクトリ作成（必要に応じて）
   - data/ や logs/ は起動時に自動作成されますが、パーミッション等で失敗する場合は手動で作成してください。

使い方
------

主要なエントリポイント（コマンド例）

- ExecutionEngine を起動（発注エンジン）
  - 本番 / ペーパートレードは KABUSYS_ENV に依存
  - python -m kabusys.run_execution
  - 実行時は data/execution.pid に PID が書かれ、停止は data/stop_requested.flag または kill.flag によって行います（監視側から kill.flag が書かれると停止します）。
  - ペーパートレード: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます（本番 DB と分離）。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（デフォルト 60）。
  - 監視は常に本番用 sqlite_path を参照します（監視 DB は環境に依存しません）。
  - 停止: data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- .env の自動ロード
  - デフォルトでプロジェクトルートの .env（および .env.local）を自動ロードします。
  - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要ライブラリ / API の利用例（コードから呼び出す）
- 研究用ファクター計算:
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
  - 結果は list[dict] で返る（date, code を含む）

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

- AI スコアリング:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=...) — OpenAI API キーが必要

停止と Kill Switch
-----------------
- 実行停止のためのフラグ:
  - data/stop_requested.flag — ローカルプロセスを優雅に停止させるためのファイル（run_* スクリプトで監視）
  - data/kill.flag（デフォルト） — KillSwitch が書き込むことで ExecutionEngine に緊急停止を指示
- KillSwitch は監視条件（ドローダウン超過、ポジション上限超過など）で kill.flag を書き、ExecutionEngine は起動時やループ中にこのフラグを検出して停止します。

ログ
---
- ログは stdout と logs/<app_name>.log（デフォルト logs/）に出力されます。
- ログレベルは LOG_LEVEL 環境変数で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要ファイル／ディレクトリ（簡易ツリー）です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理
  - config_setup.py            — .env 対話ウィザード CLI
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（監視用テーブル）
    - monitoring_engine.py     — Monitor を束ねるエンジン
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文ログ等の監視（ファイル内に実装あり）
    - risk_monitor.py          — ドローダウン・ポジション数監視
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — （通知管理、実装参照）
  - execution/
    - execution_engine.py      — 発注エンジン本体
    - broker_factory.py        — ブローカークライアント生成（Mock/実 API 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度・CPU affinity 設定
  - data/                      — 実行時生成されるデータ/DB/logs 等（プロジェクトルートに存在）

開発上の注意事項 / ポイント
---------------------------
- 環境ごとの DB 分離:
  - 監視用 SQLite（monitoring）は常に sqlite_path（デフォルト data/monitoring.db）を使用します。
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。
- .env の読み込み順:
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
- AI 機能を使う際は OPENAI_API_KEY を設定してください（API 利用料が発生します）。
- 実運用（KABUSYS_ENV=live）の場合は LINE 通知や kill flag の取り扱いに注意してください（validate_config でガードが入ります）。

よくあるコマンドまとめ
--------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス / 貢献
-----------------
README にライセンス表記がない場合はリポジトリのトップレベルにある LICENSE を参照してください。
バグや改善提案は Issue / Pull Request を通じて受け付けてください。

付録: 例 .env スニペット
------------------------
（config_setup で作成することを推奨）

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

以上。README に不足する点や、特定モジュールの詳しい説明（API 使用例・内部設計ドキュメント等）が必要であれば教えてください。