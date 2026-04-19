README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォーム用のコードベースです。
以下の主要機能を備え、監視・発注エンジン、ポートフォリオ構築ロジック、ファクター計算、
ニュース NLP（OpenAI 連携）や検証用ツール類を提供します。

主な特徴
--------
- ExecutionEngine（発注エンジン）と Monitoring（監視）を分離して運用可能
- Paper Trading（ペーパートレード）を本番 DB と分離して安全に検証
- DuckDB を用いた分析用データレイク（prices_daily / raw_financials 等）
- SQLite を用いた監視・発注ログ（monitoring.db / paper_trading.db）
- ニュースの LLM ベースセンチメント（OpenAI）による ai_score / regime 判定
- ポートフォリオ構築モジュール（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 各種 CLI：.env ウィザード、設定検証、ペーパートレード検証レポート 等
- ログは共通ユーティリティで stdout と日次ローテートファイルに出力

機能一覧（抜粋）
----------------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV により挙動切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループ起動
- 設定管理
  - kabusys.config : 環境変数/.env 読み込み・Settings 抽象化
  - python -m kabusys.config_setup : 対話式 .env 作成ウィザード
  - python -m kabusys.validate_config : 設定検証 CLI
- 監視
  - kabusys.monitoring.* : SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - monitoring_db.py : SQLite による監視ログの永続化（冪等マイグレーション含む）
- 発注関連（execution）
  - BrokerClientFactory（API クライアント生成）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等
- 研究・データ処理
  - kabusys.research : ファクター計算（momentum/value/volatility）、特徴量解析ユーティリティ
  - kabusys.ai : ニュース NLP（score_news）、regime 判定（score_regime）
  - kabusys.portfolio : 候補選定・重み付け・ポジションサイズ計算・リスク調整
- ツール
  - python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成

前提・推奨環境
--------------
- Python 3.10+（型ヒント／match 等を利用している場合は適宜）
- 主な依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML（config 検証時に YAML 構文チェックを行う場合）
- ログ出力先: デフォルト logs/ ディレクトリ（write 権限が必要）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて）pip install pyyaml

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

4. .env を作成
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants / kabu API / DB パス等を設定してください。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（ニュース NLP / regime 判定で必要）
     - LOG_LEVEL（デフォルト: INFO）
     - その他：LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

使い方（主要なコマンド）
------------------------
- ExecutionEngine を起動する
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）へ記録します
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行時は data/execution.pid に PID が書き出される（PID ファイルのパスは Settings.pid_file_path）

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（monitoring DB）に対して常に「本番」DB パスを使います（環境に依らず）
  - 停止は data/stop_requested.flag を作成すると検出して終了

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - レポートでは稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を判定します

- ニュース NLP / レジーム判定（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーを指定するか、環境変数 OPENAI_API_KEY を設定してください
  - API 呼び出し失敗時はフォールバック動作（スコア 0.0 等）で継続する設計です

停止・Kill Switch 関連
---------------------
- KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止シグナルを送ります
- kill.flag を自動で起動時にクリアするかは KILL_FLAG_CLEAR_ON_START=1 で制御（本番では推奨されない）
- run_monitoring / run_execution は data/stop_requested.flag を見て外部停止要求を検出します

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging で統一的に設定されます
  - stdout（StreamHandler）
  - logs/<app_name>.log（日次ローテーション、30日保持）
- ログレベルは LOG_LEVEL 環境変数または Settings.log_level で制御

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/.env 読み込み・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュースセンチメント得点化（OpenAI 連携）
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ・永続化ユーティリティ
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py       — 注文滞留・約定異常監視（省略ファイル省略）
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みユーティリティ
  - monitoring_engine.py   — 各モニタを束ねるエンジン
  - alert_manager.py       — 通知管理（LINE 等、実装に依存）
- execution/
  - execution_engine.py    — 発注セッション実装
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 発注株数計算
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py — 将来リターン/IC/統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ログの共通設定
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

（補足）実装上の注意点・運用メモ
----------------------------
- .env は絶対に Git 管理下に置かないでください（config_setup のヘッダにも明記）
- validate_config は起動前チェックに有用。PyYAML 未インストール時は YAML チェックをスキップします
- run_execution は KABUSYS_ENV=paper_trading のとき DB を分離するので、本番口座情報を誤って使わないよう注意
- OpenAI 呼び出しはリトライやフォールバックを実装していますが、API 利用料やレート制限に注意してください
- process_priority.set_process_priority("high") を各起動スクリプトで実行します。権限や OS により設定できない場合は警告ログが出ます
- monitoring は環境にかかわらず Settings.sqlite_path を使って監視ログを書きます（run_monitoring の仕様）

トラブルシューティング
----------------------
- 必須環境変数が不足している:
  - python -m kabusys.validate_config を実行してエラー/警告を確認
- .env の自動読み込みが邪魔な場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）
- ログファイルが作成されない:
  - 書き込み権限・ディレクトリのパスを確認（LOG_DIR / logs/）
- OpenAI 関連で例外が発生するが処理継続したい:
  - score_news / score_regime は一部の失敗をフェイルセーフ（デフォルト値）で扱いますが、API キー設定や通信状態を確認してください

ライセンス・貢献
----------------
- 本ドキュメントはソースから抽出した実装コメントに基づき作成されています。ライセンスや貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。README に不足している箇所（例: 実際の requirements.txt、細かい実行フラグ、監視ルールの詳細など）があれば、該当箇所のソースや運用ポリシーに合わせて追補します。