KabuSys
======

日本株自動売買システム（KabuSys）のコードベース向け README。  
このリポジトリは、売買実行エンジン、監視（Monitoring）、リサーチ／ファクター計算、ポートフォリオ構築、AI（ニュースセンチメント／レジーム判定）、および運用支援ツール群を含みます。

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買システムを想定したモジュール群です。主要な責務は次の通りです。

- ExecutionEngine: ブローカークライアント経由で注文を管理・発注（paper_trading と live を切替）。
- Monitoring: システム稼働、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch を発動可能。
- Research: DuckDB 上の時系列データからファクター（モメンタム、ボラティリティ、バリュー等）や統計指標を計算。
- Portfolio: 候補選定、重み算出、リスク調整、ポジションサイズ計算。
- AI: OpenAI を用いたニュースセンチメント評価（news_nlp）や市場レジーム判定（regime_detector）。
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- ユーティリティ群: ロギング設定、プロセス優先度設定、設定読み込みウィザード・検証ツール等。

主な機能一覧
--------------
- 環境設定ウィザード（.env 生成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（環境変数・config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB に分離して記録
- Monitoring ポーリングループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
  - 検証基準（稼働率、注文成功率、送信率、P95 レイテンシ等）に基づく PASS/FAIL 判定
- AI ベースのニュースセンチメントおよび市場レジーム判定（OpenAI API 必要）
- DuckDB を用いたリサーチ／ファクター計算モジュール
- SQLite を用いた監視ログ永続化（monitoring_db）

セットアップ手順（ローカル開発）
-----------------------------
以下は基本的なセットアップ手順です（環境に合わせて適宜調整してください）。

前提
- Python 3.9+（※実際の要件はプロジェクトポリシーに合わせてください）
- 必要な外部ライブラリ（例）:
  - duckdb
  - openai
  - psutil
  - （オプション）PyYAML（validate_config の YAML 検証に使用）
- SQLite は標準ライブラリで利用可能

1. リポジトリをチェックアウト
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai psutil
   - 必要なら pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

4. ディレクトリ作成
   - data/ と logs/ ディレクトリを作成しておくと便利:
     - mkdir -p data logs

5. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成。主な環境変数は次節参照。

6. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine を起動（デーモン / フォアグラウンド）
  - python -m kabusys.run_execution
  - 注意: data/stop_requested.flag が存在すると起動しないか停止処理が動作します
  - paper_trading 環境では専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL 環境変数（秒）
    - 例: export MONITOR_POLL_INTERVAL=30

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可能）

設定（主な環境変数）
-------------------
（.env で管理。config_setup.py がウィザードを提供します）

必須（実運用で必要）
- JQUANTS_REFRESH_TOKEN : J-Quants API リフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード

運用・挙動関連
- KABUSYS_ENV            : 実行環境（development | paper_trading | live）デフォルト: development
  - paper_trading: MockBroker を使用し paper_trading 用 DB に保存
  - live: 実際に発注されるため注意が必要
- LOG_LEVEL              : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR                : ログ出力ディレクトリ（デフォルト logs/）

DB 関連
- DUCKDB_PATH            : DuckDB ファイル（分析用）デフォルト data/kabusys.duckdb
- SQLITE_PATH            : 監視 DB（monitoring）デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（paper_trading 環境時の分離先）デフォルト data/paper_trading.db
- PAPER_FILL_MODE        : paper_trading の約定モード（instant|partial|never|reject）

AI / OpenAI
- OPENAI_API_KEY         : OpenAI API キー（news_nlp, regime_detector 等で使用）

監視 / Kill Switch
- KILL_FLAG_PATH         : data/kill.flag（KillSwitch のパス、デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PID_FILE_PATH          : ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- MONITOR_POLL_INTERVAL  : run_monitoring のポーリング間隔（秒、デフォルト 60）

停止フラグ
- data/stop_requested.flag : run_monitoring/run_execution が監視する停止フラグ
- data/kill.flag           : KillSwitch が書き込む停止シグナル（ExecutionEngine を停止させるため）

注意事項 / 運用メモ
------------------
- Monitoring 側は「環境にかかわらず」本番 sqlite_path を使用する設計の部分があります（run_monitoring の実装参照）。paper_trading のログを完全に分離したい場合は設定と運用ポリシーを確認してください。
- ExecutionEngine は paper_trading 環境時に paper_trading 用 DB を使う設計です（run_execution）。
- OpenAI を使う機能は API キーが必要です。API 呼び出しはリトライやフォールバックが設けられていますが、API コストとレート制限に注意してください。
- ログは stdout とログファイル（日次ローテーション）に出力されます。logs/ ディレクトリの権限・ディスク容量に注意してください。
- validate_config は config/*.yaml の存在や YAML パース（PyYAML があれば）もチェックします。config/ 以下のテンプレートは scripts/generate_config.py 等から生成する想定です（該当スクリプトがある場合）。

ディレクトリ構成（抜粋）
-----------------------
ルート（プロジェクト）:
- data/                  : DB ファイル・フラグファイル・PID などの永続領域（運用で作成）
- logs/                  : ログファイル（デフォルト）
- pyproject.toml / .git  : プロジェクトルート検出に使用

ソース:
- src/kabusys/
  - __init__.py          : パッケージ初期化（__version__ = "0.1.0" 等）
  - config.py            : 環境変数 / Settings 管理、.env 自動読み込みロジック
  - config_setup.py      : .env 対話式ウィザード
  - validate_config.py   : 起動前設定検証 CLI
  - run_execution.py     : ExecutionEngine 起動スクリプト
  - run_monitoring.py    : Monitoring ポーリングループ起動スクリプト

  サブパッケージ:
  - ai/
    - news_nlp.py        : ニュースセンチメント（OpenAI）バッチ処理
    - regime_detector.py : 市場レジーム判定（MA + マクロセンチメント合成）
  - monitoring/
    - monitoring_db.py   : SQLite ベースの監視ログ永続化層
    - system_monitor.py  : システム状態・データ鮮度監視
    - trade_monitor.py   : (存在) 注文関連監視（実装参照）
    - risk_monitor.py    : ドローダウン・ポジション上限監視
    - kill_switch.py     : Kill Switch 実装（flag 書き込み）
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - alert_manager.py   : (存在) 通知送信（LINE 等）の管理
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py    : 統一的なログ設定ユーティリティ
    - process_priority.py : プロセス優先度・CPU affinity 設定

開発 / テスト向けメモ
--------------------
- 自動 .env ロードは Settings モジュールで行われる（プロジェクトルートに .env があれば自動読み込み）。テスト中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- validate_config は --strict オプションで警告をエラー扱いにできます（CI に組み込みやすい）。
- OpenAI 呼び出しや外部 API 呼び出し箇所はユニットテスト時にモック可能なように設計されています（内部の API 呼び出しラッパー関数を patch して置換）。

ライセンス / 貢献
-----------------
プロジェクトのライセンスや貢献方法はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
------
この README はコードベースから抽出した情報を元に作成しています。運用前には必ず python -m kabusys.config_setup および python -m kabusys.validate_config で設定を作成・検証し、config/*.yaml（戦略・リスク・実行設定）や .env の内容を確認してください。問題点や改善案があれば Issue を作成してください。