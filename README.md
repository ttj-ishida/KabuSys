KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
モジュール化された設計により、取引実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI を用いたニュースセンチメント評価などの機能を提供します。  
（このリポジトリはライブラリ／ランタイムスクリプトを含む開発用コードベースです。）

主な特徴
--------
- ExecutionEngine（発注・注文管理・リスク管理・照合）  
  - KABUSYS_ENV に応じて実際のブローカー or MockBroker を切替（paper_trading モード）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）  
  - system_status / trade_logs / risk_logs / dashboard 等の永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を生成して実行エンジンを停止）
- ポートフォリオ構築ユーティリティ（候補選定、等金額／スコア加重、ポジションサイズ算出）
- リスク調整（セクター上限・レジーム乗数）
- 研究用モジュール（DuckDB を使ったファクター計算・特徴量探索）
- AI モジュール（OpenAI を用いたニュースセンチメント評価・市場レジーム判定）
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）
- 統一されたログ設定（stdout + 日次ローテートファイル）

前提・依存
-----------
- Python 3.10+
- 必要なパッケージ（主要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml のパース検証を行う場合、任意）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（API を利用する機能で必要）

セットアップ手順
----------------
1. リポジトリをチェックアウト／クローンします。
2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. pip をアップデートして依存をインストール：
   - pip install -U pip
   - pip install duckdb psutil openai
   - （オプション）pip install PyYAML
   - もし requirements.txt があれば pip install -r requirements.txt
4. .env の初期作成：
   - python -m kabusys.config_setup
     - 対話式ウィザードで J-Quants / kabuステーション 等の必須値を入力します。
5. 設定検証（起動前に必ず推奨）：
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。
6. DB ディレクトリ／ログディレクトリ等の作成は自動的に行われます（失敗した場合は stdout に警告が出ます）。

重要な環境変数（主なもの）
-------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB・ログ
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（ログ保存先、デフォルト: logs/）
- AI
  - OPENAI_API_KEY（news_nlp / regime_detector などの AI 機能で使用）
- モニタリング関連
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
  - PID_FILE_PATH（実行エンジン PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

使い方（起動・運用）
--------------------
- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor を使った常駐監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番監視 DB）を使用します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録され、本番 DB と隔離されます。
  - 実行中は data/execution.pid が作成されます。
  - 強制停止等は kill.flag を活用します（監視側が判定して作成）。

- 停止手段
  - run_monitoring/run_execution はプロジェクトルート/data/stop_requested.flag の存在をチェックして終了・停止します。停止要求を出すにはこのファイルを作成します（あるいは監視により kill.flag が書き込まれると ExecutionEngine に停止シグナルが送られます）。
  - Kill Switch（監視モジュール）により条件達成時に data/kill.flag を自動生成します。
  - 実行エンジン独自の停止処理は Engine 側の実装に依存しますが、stop フラグ()/PID ファイルを確認して安全停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- 参考コマンド例
  - 開発用（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 監視開始:
    - python -m kabusys.run_monitoring
  - AI スコア作成（ライブラリ API を直接使用）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)

アーキテクチャ要点
-----------------
- 設定管理
  - kabusys.config: .env 自動ロード（.env / .env.local）と Settings クラスで環境変数を集中管理
  - config_setup / validate_config による運用支援

- 永続化
  - 監視系は SQLite（monitoring_db）へ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - データ解析・研究は DuckDB（高速 OLAP）を使用

- ログ
  - kabusys.utils.logging_setup で stdout と日次ローテートファイル（logs/<app_name>.log）を統一管理

- プロセス管理
  - kabusys.utils.process_priority で OS 毎にプロセス優先度を設定
  - PID ファイル / stop flag / kill flag による簡易運用制御

ディレクトリ構成（主要ファイル）
-----------------------------
（リポジトリ内 src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/.env 管理 + Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — 監視プロセス起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite スキーマと DB 操作ラッパー
    - system_monitor.py — システム状態・データ鮮度チェック
    - risk_monitor.py — ドローダウン／ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - (他: trade_monitor, alert_manager 等)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数決定（lot 単位・aggregate cap 等）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）→ ai_scores 書込
    - regime_detector.py — マクロセンチメント＋ETF MA から市場レジーム判定
  - execution/ (実行系コンポーネント; Engine, BrokerFactory, OrderManager 等)
  - data/（ランタイムで生成されることを想定）
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db, paper_trading.db, kabusys.duckdb など

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では必須値・通知先（LINE 等）の設定を慎重に確認してください。validate_config は本番向けガードを含みます。
- AI 機能は OpenAI API キーと通信を必要とし、コスト・レイテンシが発生します。失敗時はフェイルセーフ（スコア 0.0 等）で継続する実装になっていますが、運用ポリシーを定めてください。
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。本番 DB を上書きしないよう .env の設定を確認してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化され stdout のみになります。必要に応じて LOG_DIR を設定してください。

開発・拡張
-----------
- 新しい設定項目は config.py / config_setup.py に追加してください。
- research / ai / portfolio モジュールは純粋関数中心の設計（テストしやすい）です。DuckDB 接続を受け取る形で実行環境に依存しません。
- テストを書く際は、OpenAI 呼び出し部分はモック（patch）して副作用を排除してください（news_nlp._call_openai_api 等を差し替え可能）。

ライセンス・貢献
----------------
（本 README ではライセンス・貢献ポリシーは明記していません。リポジトリの LICENSE / CONTRIBUTING を参照してください。）

以上。開発や運用で必要な情報が他にあれば README に追記します。