KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム KabuSys のコアモジュール群です。
Execution（発注エンジン）、Monitoring（監視）、Portfolio 構築、Research（ファクター計算）、
AI（ニュース NLP / レジーム判定）などの機能を含んでいます。

以下はこのコードベースの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

プロジェクト概要
----------------
- 自動売買エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネントを備えたシステム。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と完全に分離して検証可能。
- DuckDB を用いたファクター計算 / リサーチ、SQLite を用いた監視ログ・発注ログの永続化。
- OpenAI を利用したニュースセンチメント解析 (news_nlp) と市場レジーム判定 (regime_detector) を提供。
- 設定は .env ファイル / 環境変数で管理。対話式ウィザードと設定検証ツールあり。

主な機能一覧
-------------
- Execution（run_execution.py）
  - Live / Paper Trading 切替
  - BrokerClientFactory を介したブローカークライアント生成
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）を利用した安全停止

- Monitoring（run_monitoring.py, monitoring/*）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 発注ログの監視（滞留注文・異常約定等） ※実装ファイル群あり
  - RiskMonitor: ドローダウン・ポジション上限の検出とリスクログ
  - KillSwitch: 重大リスク時に data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ

- Portfolio（portfolio/*）
  - 候補選定 select_candidates
  - 重み計算（等分・スコア加重）
  - セクターキャップ適用 apply_sector_cap
  - ポジションサイズ計算 calc_position_sizes（lot 単位丸め、集計キャップ調整）

- Research（research/*）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ

- AI（ai/*）
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄ごとにセンチメントを算出し ai_scores に書込
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースを LLM で評価して market_regime に書込
  - API 呼び出しは堅牢化（リトライ／フォールバック）されている

- ユーティリティ
  - 設定ウィザード: kabusys.config_setup で .env を対話式生成
  - 設定検証: kabusys.validate_config で .env / config/*.yaml 等をチェック
  - ログ設定ユーティリティ: kabusys.utils.logging_setup
  - プロセス優先度制御: kabusys.utils.process_priority
  - Monitoring DB 層: kabusys.monitoring.monitoring_db（SQLite スキーマ・永続化）

セットアップ手順
----------------
※以下は最小限の手順例です。環境に応じて適宜調整してください。

1. 必要な Python バージョン
   - Python 3.9+ を推奨（ソース内の型注釈等に基づく）

2. リポジトリをクローン
   - git clone <this-repo>

3. 仮想環境を作成してアクティブ化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージをインストール
   - 以下は主要な依存例（requirements.txt がある場合はそちらを使用）
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML のパースを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

5. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を作成（本リポジトリに .env.example がない場合は config_setup を利用）

6. 設定検証（必須環境変数が揃っているか確認）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合:
     - python -m kabusys.validate_config --strict

7. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。自動作成されることもありますが許可のある場所に配置してください。

主要な環境変数（抜粋）
----------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録する
    - live: 本番

- DB パス（デフォルト）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper trading 用 DB, default: data/paper_trading.db)

- ログ / プロセス / モニタ
  - LOG_LEVEL (INFO / DEBUG / ...)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)

- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)

- OpenAI
  - OPENAI_API_KEY (news_nlp / regime_detector 用)

使い方（コマンド例）
------------------
- ExecutionEngine を起動（通常はプロセス管理ツールで起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すればペーパートレード専用 DB に分離されます。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 でポーリング間隔を上書き（秒）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（オプション）:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムからの呼び出し）
  - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

- ログ
  - logs/<app_name>.log に日次ローテーションで出力（setup_logging を各スクリプトで呼んでいる）
  - コンソール出力は stdout（ストリームハンドラ）

停止 / Kill Switch
------------------
- data/kill.flag に文字列を書き込むことで ExecutionEngine に対して停止シグナルを送ります（KillSwitch）。
- run_execution/run_monitoring は data/stop_requested.flag を見て安全に終了します。
- 設定 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと責務の一覧（抜粋）です。

- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI

  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

  - monitoring/
    - monitoring_db.py         — SQLite スキーマ・DB ラッパー
    - system_monitor.py        — CPU/メモリ/データ鮮度監視
    - trade_monitor.py         — 発注ログ監視（滞留/異常等）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — Monitor を束ねたポーリング実行

  - execution/
    - execution_engine.py      — ExecutionEngine 本体（起動は run_execution）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py               — ニュースセンチメント集計・OpenAI 呼出し
    - regime_detector.py        — レジーム判定（MA + マクロ NLP）

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

データ / デフォルトファイル
---------------------------
- data/kabusys.duckdb         — DuckDB（デフォルト: DUCKDB_PATH）
- data/monitoring.db          — SQLite（監視・ログ用、デフォルト: SQLITE_PATH）
- data/paper_trading.db       — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid          — Execution PID（PID_FILE_PATH）
- data/kill.flag              — Kill スイッチファイル（KILL_FLAG_PATH）
- data/stop_requested.flag    — 手動で監視ループ / 実行ループを停止するためのフラグ

注意事項 / ベストプラクティス
-----------------------------
- .env を絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にし、LINE 通知などの設定を確認してください。
- OpenAI キーを利用する機能は API 呼び出し回数／コストに注意して運用してください。
- Paper Trading は実装で本番 DB と完全分離するよう設計されていますが、環境変数の設定ミスに注意してください。
- DuckDB / SQLite のファイルパスはファイルシステムのアクセス権に依存します。適切な権限を確保してください。

開発者向けメモ
---------------
- モジュールはテスト容易性を考慮して設計されています（外部 API 呼び出しは小さな箇所に集約）。
- AI API 呼び出し部分は簡単にモック可能（例: unittest.mock.patch）になっています。
- monitoring_db.init_monitoring_db は冪等（マイグレーションを一部含む）設計です。

問い合わせ / 貢献
-----------------
- バグ報告や改善提案は issue にお願いします。
- 大きな変更を行う場合は設計方針（安全性・フォールバック）を尊重してください。

以上が README の概要です。必要に応じて README をリポジトリの README.md に追記し、実際の依存関係（requirements.txt）や .env.example を追加すると利用者にとって親切です。必要なら README の英語版や運用手順（systemd / supervisor 用のサンプル unit ファイル等）も作成できます。