KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。本リポジトリは、戦略の研究用ユーティリティ、ポートフォリオ構築、発注実行エンジン（本番 / ペーパートレード切替可）、監視・アラート、及び AI (OpenAI) を使ったニュース分析やレジーム検出などを含みます。

バージョン: 0.1.0（src/kabusys/__init__.py）

主な機能
-------
- 環境設定管理 (.env 読込/ウィザード)
  - 自動 .env ロード（.env / .env.local, OS 環境変数優先）
  - 対話式ウィザードで .env を生成 (kabusys.config_setup)
- 設定検証 CLI（環境変数・config/*.yaml の簡易チェック） (kabusys.validate_config)
- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading 時は MockBroker を使用し、専用 SQLite に記録
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視ループ
  - Kill Switch（条件達成時に data/kill.flag を書き込み、ExecutionEngine を停止）
- Portfolio モジュール（銘柄選定・配分・ポジションサイジング）
- Research モジュール（ファクター計算・将来リターン・IC 計算）
- AI モジュール
  - news_nlp: OpenAI を使ったニュースのセンチメントスコアリング
  - regime_detector: マクロ + ETF MA を組合せた市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレードの検証レポート生成
- 共通ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

前提条件
-------
- Python 3.10+
- 推奨パッケージ（プロジェクトに requirements.txt がない場合の例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に任意）
- システムでのファイル書き込み（data/, logs/）権限

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで要求される値を入力し、.env を生成します。
   - 重要: .env を絶対に Git にコミットしないでください。

5. 設定を検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

環境変数（主なもの）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード

運用に関係する主要設定（デフォルトを併記）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db) — 監視 DB。monitoring は常に sqlite_path を参照します
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 専用 DB
- LOG_LEVEL (INFO)
- LOG_DIR (logs/)
- OPENAI_API_KEY — OpenAI 呼び出し用（AI 機能を使う場合に必須）
- PAPER_FILL_MODE ("instant", "partial", "never", "reject") — paper_trading の約定モード
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 監視 / Kill Switch 関連

注意: monitoring サービスは KABUSYS_ENV に関わらず settings.sqlite_path を使用して永続化します（監視ログは本番 DB として扱われる点に注意）。

使い方（主なコマンド）
-------------------
- 環境ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（メイン発注エンジン）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で切替（paper_trading の場合は専用 DB を使用）
  - 停止: data/stop_requested.flag を作成すると安全に停止します
  - Kill Switch により data/kill.flag が書き込まれると ExecutionEngine 側で検知して停止します

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db オプションで別 DB を指定できます（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI 関連（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果を DB に書き込みます。OPENAI_API_KEY の設定が必要です。

停止・Kill フラグの仕組み
------------------------
- stop_requested.flag (data/stop_requested.flag)
  - run_execution / run_monitoring のループを優雅に停止させるための外部フラグ
  - 作成するとループが検知して処理を終了します

- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch が危険条件（ドローダウンやポジション上限超過等）を検出した際に書き込むファイル
  - ExecutionEngine は起動時や稼働中にこれを検出して停止します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされます（本番では推奨されません）

ログ
---
- ログはデフォルトで logs/ 以下に出力されます（アプリ名ごとにファイルが分かれる: execution.log, monitoring.log など）
- 同時に stdout にも出力されます
- ログレベルは LOG_LEVEL 環境変数で調整可能

ディレクトリ構成
----------------
以下は主要ファイルの一覧（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity の設定

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — Momentum / Value / Volatility ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - ai/
    - news_nlp.py            — OpenAI を用いたニュースのセンチメントスコアリング
    - regime_detector.py     — 市場レジーム検出

  - monitoring/
    - monitoring_db.py       — SQLite 監視用 DB 操作クラス
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（このコードベースで主旨は同様）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信を担う想定のマネージャ）

  - execution/
    - execution_engine.py    — ExecutionEngine 本体（発注ループ）
    - broker_factory.py      — ブローカークライアント生成（Mock/Real 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/tools/
    - paper_verification_report.py — ペーパートレード検証レポート

補足 / 注意事項
--------------
- DB マイグレーションやテーブル作成は init_monitoring_db() により冪等に行われます。
- AI (OpenAI) 機能を利用するには OPENAI_API_KEY が必要です。API 呼び出しはネットワーク/コスト/レート制限の考慮が必要です。
- KABUSYS_ENV=live を設定する場合は特に注意してください。validate_config は live 時に追加の警告を出します（LINE トークン未設定など）。
- プロセス優先度設定はプラットフォーム依存（psutil を使用）。権限不足で失敗することがありますが、安全にフォールバックします。
- 本リポジトリのコードは運用を想定したサンプル設計が含まれますが、本番運用前には十分なテスト・監査を行ってください。

ライセンス / コントリビューション
---------------------------------
（リポジトリに合わせて適宜追記してください）

問い合わせ
---------
- 実装上の質問や不明点があれば、該当するモジュールの docstring を参照してください。特に AI・Execution・Monitoring 関連は使用上の前提（DB スキーマ・時刻の扱い・フェイルセーフ設計）をコメントに明記しています。

以上。必要があれば README を英語版にしたり、起動スクリプトごとの詳細なオプション説明（ログローテーション・デバッグ方法等）を追加できます。どの情報を重点的に追記しましょうか？