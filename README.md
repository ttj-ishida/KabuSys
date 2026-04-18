KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアモジュール群を含みます。  
本 README はローカル開発者・運用担当者向けにプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 必須環境変数
- セットアップ手順
- 使い方（主要コマンド）
- 重要なファイル / フラグの説明
- ディレクトリ構成（主要ファイルの一覧）
- 補足（トラブルシューティング・注意点）

プロジェクト概要
----------------
KabuSys は、J-Quants 等のデータ、kabuステーション（発注API）、OpenAI（NLP）などを組み合わせた日本株自動売買の基盤実装です。  
主な要素は以下の通りです。

- 戦略開発（ファクター計算、特徴量探索、ポートフォリオ構築、ポジションサイズ）
- ExecutionEngine（発注ロジック・リスク制御・Order 管理）
- Monitoring（システムヘルス、取引状態、リスク監視、Kill Switch）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）
- 開発用ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）
- ロギング・プロセス優先度などのユーティリティ

主な機能一覧
-------------
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ペーパートレード時は MockBrokerClient を使用し DB を分離
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag による外部停止（Kill Switch）
  - monitoring DB（SQLite）への永続化
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔を制御）
- ポートフォリオ構築
  - 候補選定 / 重み計算（等金額・スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分）
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI
  - ニュース NLP （OpenAI を使ったセンチメントスコアリング）
  - レジーム判定（MA200 とマクロニュースの合成）
- ツール
  - paper_verification_report: ペーパートレード DB に対する検証レポート生成

前提条件 / 必須環境変数
---------------------
- Python: 3.9+
- 外部ライブラリ（主要）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — validate_config の YAML 検証に使用

重要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（paper_trading 時の上書き）
- OPENAI_API_KEY — OpenAI 呼び出し時に必要（AI モジュール使用時）
- LOG_LEVEL / LOG_DIR — ログ関連
- その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発/検証用）pip install pyyaml

   ※ requirements.txt がある場合はそれを使用してください（本コード断片には同梱されていません）。

4. .env の準備
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
       - 対話に従って .env を生成します（.env は Git にコミットしないでください）
   - もしくは .env.example を参考に .env を作成してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトでは data/ 以下に SQLite / PID / flag ファイルを置きます。必要に応じて作成しておいてください。
   - ログは logs/ に出力されます（LOG_DIR で変更可）。

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file <path>（デフォルト .env）

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
    - 実行中は data/execution.pid に PID が書き出されます（設定で変更可）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60 秒）
  - 挙動:
    - 監視は Settings.sqlite_path（monitoring DB）を使用（環境にかかわらず本番 sqlite_path を参照します）
    - data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 引数:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - レポートは標準出力に出力され、稼働率、注文成功率、レイテンシ等を評価します

重要なファイル・フラグ説明
-------------------------
- data/kill.flag
  - Kill Switch が有効になったときに監視モジュールが書き込むフラグ。ExecutionEngine はこのフラグを検知して安全に停止できます。
  - Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に自動クリアされます（本番では 0 推奨）。

- data/stop_requested.flag
  - run_execution / run_monitoring の制御用。存在すると監視ループや実行を停止または起動をスキップします。

- data/execution.pid
  - ExecutionEngine の PID が書き込まれます（プロセス管理・デバッグ用）。

- logs/
  - 各コンポーネント用ログファイル（例: logs/execution.log, logs/monitoring.log）。日次ローテートされます。

- SQLite / DuckDB
  - monitoring 用 SQLite（デフォルト: data/monitoring.db）
  - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - DuckDB（分析用、デフォルト: data/kabusys.duckdb）

ディレクトリ構成（主要ファイル）
----------------------------
（src/kabusys をルートとした主要ファイル/モジュール）

- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数・設定読み込み・Settings クラス、自動 .env 読み込みロジック
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等（発注ロジック・Order ライフサイクル）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文・約定の監視（存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 監視コンポーネントの統括
  - alert_manager.py — 通知（LINE 等）管理（存在）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・キャップ調整
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py — 各関数をエクスポート

- src/kabusys/research/
  - factor_research.py — momentum / volatility / value の計算（DuckDB 参照）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - __init__.py — 研究用ユーティリティのエクスポート

- src/kabusys/ai/
  - news_nlp.py — OpenAI を使ったニュースのセンチメント集計・ai_scores への書き込み
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュースの合成）

- src/kabusys/utils/
  - logging_setup.py — 統一ログ設定（Stream + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成

補足 / 注意点
-------------
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を含む）を基準に行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution/run_monitoring は設定や環境に応じて本番DBにアクセスするため、本番運用時は .env と設定ファイルを十分に確認してください（validate_config を使用）。
- OpenAI 関連機能を使用する場合は OPENAI_API_KEY が必要です。API 呼び出しにはレートリミットやエラー処理が組み込まれていますが、料金と利用制限に注意してください。
- ペーパートレードと実取引は DB を分離する設計になっています（paper_trading モード）。運用ミスで本番発注が行われないように KABUSYS_ENV の設定に注意してください。
- ログディレクトリ作成に失敗した場合はコンソールのみ出力にフォールバックします。ログディレクトリの権限を確認してください。
- Monitoring / Execution の停止は stop_requested.flag / kill.flag を使って外部から制御できます。運用手順をドキュメント化しておくことをおすすめします。

簡単なワークフロー例
--------------------
1. .env を作成（config_setup を使用）
2. python -m kabusys.validate_config で検証
3. python -m kabusys.run_monitoring を起動（監視）
4. python -m kabusys.run_execution を起動（実行エンジン／発注）
5. 必要に応じて paper_verification_report でペーパー取引の検証

ライセンス / コントリビュート
-----------------------------
- 本 README にはライセンス情報が含まれていません。リポジトリの LICENSE を参照してください。
- コントリビュート手順、issue、PR のポリシーはリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

以上がこのコードベースの概要と基本的な使い方です。必要であれば、各モジュール（ExecutionEngine、Monitoring、AI）や設定項目について詳細なドキュメント（API仕様、シーケンス図、運用手順など）を追記します。どの部分の詳しいドキュメントが欲しいか教えてください。