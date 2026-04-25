README
======

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine（発注実行） — ブローカークライアントを介した発注制御（本番 / ペーパートレード対応）
- Monitoring（監視） — システム稼働状況、注文ログ、リスク（ドローダウン・ポジション数）を定期監視して永続化・アラート出力
- Portfolio（ポートフォリオ構築） — 候補選定、重み付け、ポジションサイズ算出、セクター制御等の純粋関数群
- Research（リサーチ） — DuckDB を用いたファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- AI（ニュースNLP / レジーム判定） — OpenAI を利用したニュースのセンチメント解析や市場レジーム判定機能
- Tools（検証 / レポート） — ペーパートレード検証レポート生成などのユーティリティ
- 設定管理 / ヘルパー — .env ウィザード、設定検証、ログ設定、プロセス優先度設定等

主なファイル・スクリプト
- src/kabusys/run_execution.py — ExecutionEngine を起動するエントリポイント
- src/kabusys/run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- src/kabusys/config_setup.py — .env を対話式で作成・更新するウィザード
- src/kabusys/validate_config.py — 環境変数・設定ファイルの前検証 CLI
- src/kabusys/tools/paper_verification_report.py — ペーパートレード検証レポート生成

特徴一覧
--------
- 環境分離
  - KABUSYS_ENV により development / paper_trading / live を切り替え（paper_trading は専用 SQLite を使用）
- フェイルセーフ設計
  - AI 呼び出し失敗や DB パースエラーは基本的にフォールバック／スキップして継続
- モジュール分離
  - 発注ロジック、ポートフォリオ構築、監視、リサーチ、AI が分離された設計
- DuckDB + SQLite
  - 分析側は DuckDB、監視／発注系は SQLite（monitoring.db / paper_trading.db）を使用
- ログ管理
  - 統一的な logging 設定（コンソール + 日次ローテートファイル）
- Kill Switch
  - data/kill.flag による外部停止シグナル、停止フラグや stop_requested.flag による安全停止

セットアップ手順
----------------
以下は開発／ローカル実行向けの一般的な手順です。実際の依存関係（requirements.txt 等）がある場合はそれに従ってください。

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 依存パッケージのインストール
   - duckdb、psutil、openai などが利用されます。例:
     - pip install duckdb psutil openai
   - validate_config の YAML 検証を使う場合は PyYAML をインストール:
     - pip install pyyaml

3. プロジェクトルートに移動（.git または pyproject.toml を基準に自動検出）
   - パッケージは src/kabusys 以下に配置されています。CWD に依存しない実装ですが、ルートに .env を置く想定です。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）  
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - strict モードで警告もエラー扱い:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 配下に DB やフラグファイルが置かれます。
   - ディレクトリを手動で作るか、初回実行時に自動作成されます。

使い方
------
主要な起動・ツールの使用例を示します。

- ExecutionEngine を起動（ローカル / 本番）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、デフォルトで data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書き込みます（設定で変更可能）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は KABUSYS_ENV にかかわらず production（settings.sqlite_path）を使用して監視データを記録します。
  - 停止は data/stop_requested.flag の作成で検知します（ファイルを作るとループが終了）。

- .env の対話式設定
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - PyYAML が無ければ config/*.yaml の内容検証はスキップされますがファイル存在チェックは行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を参照

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live） — 動作モードの切替
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（分析用 DuckDB、デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY（AI モジュールを利用する場合）
- LOG_LEVEL, LOG_DIR 等（ログ関連）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔／秒）

停止・制御フラグ
- data/stop_requested.flag — run_execution / run_monitoring の外部停止フラグ（存在するとループが終了）
- data/kill.flag — KillSwitch が評価して書き込む実行停止フラグ（ExecutionEngine はこれを検出して停止）
- KILL_FLAG_CLEAR_ON_START（設定） — 起動時に kill.flag を自動クリアするか（1 でクリア、デフォルト 0）

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30 日分保持）。
- すべての起動スクリプトで共通の logging 設定関数を使用しています（kabusys.utils.logging_setup.setup_logging）。

簡単な運用ワークフロー例
- 開発者が .env を作成（python -m kabusys.config_setup）
- 設定を検証（python -m kabusys.validate_config）
- 分析用 DuckDB に価格データをロード（外部スクリプト）
- Execution を paper_trading モードで起動して挙動確認
- Monitoring を起動してシステム監視と KillSwitch を有効にする
- PaperTrading 実行後に検証レポートを生成

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
- config_setup.py          — .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py            — ニュースのセンチメント解析（OpenAI 連携）
  - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化・永続化 API
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン/ポジション上限監視
  - trade_monitor.py       — （注文監視ロジック）
  - monitoring_engine.py   — 各 Monitor を束ねたポーリングエンジン
  - kill_switch.py         — kill.flag の作成・判定
  - alert_manager.py       — （通知管理。LINE 等の実装想定）
- portfolio/
  - portfolio_builder.py   — 候補選定、重み付け
  - position_sizing.py     — 発注株数計算、集約キャップ処理
  - risk_adjustment.py     — セクターキャップ、レジーム乗数
- research/
  - factor_research.py     — momentum / volatility / value 等の算出
  - feature_exploration.py — forward returns、IC、統計要約
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ロギング共通設定
  - process_priority.py    — プロセス優先度設定ユーティリティ

注意事項・トラブルシューティング
--------------------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は設計上「監視」専用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。paper_trading では Execution 側の DB を分離しますが、監視は production の DB を用いる点に注意してください。
- OpenAI を利用する機能は API の呼び出し制限やエラーを考慮して実装されていますが、API キーが未設定だと例外が上がります（score_news / score_regime は OPENAI_API_KEY が必要）。
- validate_config は config/*.yaml の存在と簡易パースをチェックしますが、PyYAML がない場合はパースチェックをスキップします。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります（警告が出ます）。

ライセンスや貢献ルール、詳細な設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がある場合は別途参照してください。

以上。必要であれば README に含めるサンプル .env のテンプレートや起動スクリプトの systemd/cron 設定例なども追加します。どの情報を追加しますか？