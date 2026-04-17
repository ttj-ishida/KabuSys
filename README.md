# KabuSys — 日本株自動売買システム

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリ群です。トレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

以下はコードベースから読み取れる使い方・設定方法のまとめ README です。

---

目次
- プロジェクト概要
- 主な機能一覧
- 依存関係（主要）
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数（主要）
- データベース / ファイルの既定パス
- ディレクトリ構成（抜粋）
- 注意事項 / 運用メモ

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのライブラリ群で、発注エンジン（ExecutionEngine）、監視（Monitoring）、リスク管理、ポートフォリオ構築、ファクター／リサーチ、AI によるニューススコアリングや市場レジーム判定などを提供します。
- 設計上、ペーパートレード (paper_trading) と本番 (live) を分離できるようになっており、監視ロジックや DB 初期化などは安全に動くよう冗長性を考慮しています。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパーを切り替え可能。ペーパートレード時は MockBrokerClient を使い専用 SQLite に記録する。
  - プロセス優先度設定、PID ファイル管理、kill flag による停止対応。
- Monitoring（run_monitoring.py, monitoring_engine）
  - SystemMonitor（CPU / メモリ / ディスク / プロセス状態 / データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - KillSwitch / AlertManager を組み合わせて自動停止・通知が可能
- Portfolio（銘柄選定・重み計算・ポジションサイジング）
  - 等配分 / スコア加重 / リスクベースの発注株数計算
  - セクター集中制限やレジーム乗数の適用
- Research（DuckDB を用いたファクター計算・将来リターン / IC / 統計サマリ）
- AI（ニュース NLP / レジーム判定）
  - OpenAI を利用したニュースセンチメント評価（ai_scores へ保存）
  - マクロニュース＋ETF MA 乖離で市場レジーム判定（market_regime へ書込）
- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

依存関係（主要）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 Yaml の検証を行う場合。未インストール時は検証をスキップします）

セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローンして、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（requirements.txt がある場合はそれを利用）。
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 本番で不要なパッケージは必要に応じて除外できます（AI 機能を使わないなら openai は不要）。

3. 初期環境変数設定（.env）
   - 対話式ウィザードで .env を生成・編集できます：
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成してください。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. DB の初期化は各スクリプトが内部で実行します（monitoring 用テーブル等は init_monitoring_db 関数で作成・マイグレーションされます）。

使い方（主要スクリプト）
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数により動作モードを切替:
    - development: 発注なし（開発）
    - paper_trading: MockBrokerClient を使用、データは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）へ
    - live: 本番（実際に発注）
  - 実行中は data/execution.pid（既定）に PID が書かれ、停止は data/stop_requested.flag または data/kill.flag によって制御されます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数指定（既定 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に production 用の sqlite_path（監視 DB）を使用します（環境に関わらず）。

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

環境変数（主要）
- 必須 / ほぼ必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- DB / ログ / 実行
  - DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（既定: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（既定: data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジン PID ファイル（既定: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（既定: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消すか (1 = 消す、0 = 消さない)（本番では 0 推奨）

- ログ / 実行モード
  - KABUSYS_ENV — execution の実行モード（development / paper_trading / live）（既定: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）（既定: INFO）

- AI 関連
  - OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定を使用する場合必須）
  - PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject）（既定: instant）

データベース / ファイルの既定パス
- data/kabusys.duckdb — DuckDB（分析・ファクター・AI 用）
- data/monitoring.db — 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard など）
- data/paper_trading.db — ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading のとき使用）
- data/execution.pid — ExecutionEngine の PID（既定）
- data/kill.flag — Kill Switch のフラグファイル（存在すると ExecutionEngine 停止のトリガ）
- data/stop_requested.flag — run scripts が監視している停止フラグファイル（run_execution / run_monitoring が参照）

ディレクトリ構成（src/kabusys の主なファイル／パッケージ）
- __init__.py
- config.py — 環境変数自動ロード・Settings クラス
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ループ起動スクリプト

サブパッケージ
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py ...
- monitoring/
  - monitoring_db.py, monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py ...
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py, ...
- ai/
  - news_nlp.py, regime_detector.py（OpenAI を利用）
- data/
  - pipeline / stats / raw table utilities（DuckDB と連携するモジュール）
- tools/
  - paper_verification_report.py

（実際のフルツリーは src/kabusys 以下を参照してください）

注意事項 / 運用メモ
- .env は絶対にリポジトリにコミットしないでください（API キー / パスワードを含むため）。
- validate_config.py を起動前に実行して必須変数やパスの問題を事前に検出して下さい。
- run_execution は PID ファイルと stop flag / kill flag によって安全に停止できます。運用時は kill_flag_clear_on_start を慎重に設定してください（本番では 0 推奨）。
- Monitoring は常に監視用 SQLite（SQLITE_PATH）を使用します。環境に依らず同じ監視 DB を使う設計です。
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API 呼び出しはネットワークエラーやレート制限に対するリトライが組まれていますが、API キーがない場合は ValueError を送出する関数もあります。AI 機能を運用する場合は OPENAI_API_KEY を設定してください。
- paper_trading モードでは発注をモックして専用 DB に記録されます。本番 DB と完全分離されます。

トラブルシューティング（よくある項目）
- monitor が即座に停止してしまう / エンジンが起動しない
  - data/stop_requested.flag が存在していないか確認してください。停止フラグは起動前に検査され、存在する場合は起動をスキップします。
- PID ファイルが残っていてプロセスが起動しない
  - PID ファイルが stale（存在するがプロセスが死んでいる）場合、SystemMonitor が検出して削除しますが、手動で確認して削除することも可能です。
- DuckDB / SQLite のファイルが存在しない
  - 多くのスクリプトは親ディレクトリを自動作成しますが、validate_config による警告や、実行時にディレクトリ権限を確認してください。

---

以上がコードベースから作成した README の要約です。必要であれば以下の追加を提供します:
- 実際の requirements.txt の候補一覧
- よく使うコマンド集（systemd / Docker / supervisor 用の起動例）
- 各コンポーネント（ExecutionEngine / Monitoring / AI）についての詳細な実装ドキュメント

どれを追加しましょうか？