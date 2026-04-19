README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
戦略のファクター計算、ポートフォリオ構築、発注エンジン（実行／ペーパートレード分離）、監視、ニュース系の AI スコアリング等のコンポーネント群を含みます。本リポジトリはモジュール群（pure function や I/O 層）を通じて合理的に設計されています。

主な特徴
--------
- 発注エンジン（ExecutionEngine）と監視ループ（MonitoringEngine）の起動スクリプトを提供
- Paper Trading（ペーパートレード）と Live（本番）を環境で切り替え可能
- DuckDB（分析向け）と SQLite（監視・履歴）を併用するデータレイヤ
- ファクター計算（モメンタム／バリュー／ボラティリティ等）およびリサーチユーティリティ
- ニュースの LLM スコアリング（OpenAI）による銘柄・マクロ評価モジュール
- Kill Switch / リスク監視（ドローダウン・ポジション上限）と通知連携の枠組み
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証ツール）
- Paper Trading の検証レポート生成スクリプト

セットアップ手順
----------------
1. リポジトリをクローン・作業ディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 最低限必要なパッケージ（例）:
     pip install duckdb psutil openai
   - YAML 検証を使う場合:
     pip install pyyaml
   実際の requirements.txt がある場合はそれを使用してください。

4. 初期環境変数（.env）を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成後、設定内容を検証:
     python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ に SQLite や PID・フラグファイルを作成します。実行前に権限を確認してください。

主要な環境変数（主なもの）
-------------------------
（デフォルトは Settings クラスや config_setup に記載されている値）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知（任意）
- OPENAI_API_KEY: OpenAI 呼び出しの API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1、デフォルト: 0)

使い方（主要コンポーネント）
---------------------------

1) 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - 対話式に .env を生成・更新します。

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1)。

3) 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 動作概要:
     - KABUSYS_ENV により挙動が変わります。paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）にトレードログを保存して本番 DB と分離します。
     - 起動時にプロセス優先度を "high" に設定し、pid ファイル（data/execution.pid 等）を管理します。
     - data/stop_requested.flag が存在すると起動を行わない / 実行中はフラグで停止をトリガできます（停止用フラグの位置はスクリプト内の定義に依存します）。

4) 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 動作概要:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング周期を秒単位で上書きできます（デフォルト 60 秒）。
     - 監視は Settings に従い SQLite（monitoring DB）と DuckDB を接続して SystemMonitor / TradeMonitor / RiskMonitor 等をポーリングします。
     - 停止は data/stop_requested.flag を作成するか、KeyboardInterrupt（Ctrl+C）で行います。

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: env または data/paper_trading.db を参照
   - 注文成功率、稼働率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

AI 関連
-------
- kabusys.ai.news_nlp: raw_news から銘柄単位に集約し OpenAI（gpt-4o-mini）でセンチメントを評価、ai_scores テーブルへ保存します。OPENAI_API_KEY が必要です。
- kabusys.ai.regime_detector: ETF（1321）の MA200 とマクロニュース（LLM）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存します。
- API 呼び出しではリトライ・バックオフ・レスポンス検証を行う実装が入っています。

ログ
----
- ログはデフォルトで stdout（console）と logs/<app_name>.log（日次ローテーション 30 日保持）に出力されます。
- setup_logging(app_name="...") でアプリ名を指定します。ログディレクトリは環境変数 LOG_DIR で変更可能。

停止・Kill Switch
-----------------
- KillSwitch は監視結果（リスク等）に応じて data/kill.flag（Settings.kill_flag_path）を書き込み、ExecutionEngine の停止を誘導します。kill.flag は存在確認・クリア機能を持ちます。
- 手動でプロセスを安全に停止したい場合、data/stop_requested.flag（実行・監視スクリプトでチェックされる停止フラグ）を作成してください。存在するとループを終了します。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要なパッケージ・ファイルの一覧（抜粋）です。実ファイルは src/kabusys 以下にあります。

- src/kabusys/
  - __init__.py                       -- パッケージ定義（__version__ 等）
  - config.py                         -- 環境変数 / Settings 管理、自動 .env ロード機能
  - config_setup.py                   -- .env 対話式ウィザード
  - validate_config.py                -- 起動前設定検証 CLI
  - run_execution.py                  -- ExecutionEngine 起動スクリプト
  - run_monitoring.py                 -- SystemMonitor 起動スクリプト（監視用）
  - tools/
    - paper_verification_report.py    -- Paper Trading レポート生成 CLI
  - ai/
    - news_nlp.py                     -- ニュース NLP スコアリング
    - regime_detector.py              -- 市場レジーム判定
  - monitoring/
    - monitoring_db.py                -- SQLite 監視 DB 的 CRUD / 初期化
    - monitoring_engine.py            -- 各 Monitor を束ねるエンジン
    - system_monitor.py               -- システム状態・データ鮮度監視
    - risk_monitor.py                 -- ドローダウン・ポジション監視
    - kill_switch.py                  -- Kill Switch 実装
    - ...（trade_monitor 等）
  - portfolio/
    - portfolio_builder.py            -- 銘柄選定・スコアソート
    - position_sizing.py              -- 株数決定・リスク制限
    - risk_adjustment.py              -- セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              -- モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py          -- IC / 将来リターン / 統計サマリ
  - utils/
    - logging_setup.py                -- 統一ログ設定ユーティリティ
    - process_priority.py             -- プロセス優先度 / CPU affinity 設定
  - execution/                         -- Execution 関連の実装群（OrderManager, BrokerFactory 等）
  - data/                              -- (想定) データ格納ディレクトリ（DB / PID / flags 等）
  - config/                            -- YAML ベースの設定テンプレート（system_config.yaml 等）

補足 / 運用上の注意
-------------------
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 1 にしないことを推奨します。自動クリアが有効だと Kill Switch の保護が無効化される恐れがあります。
- OpenAI を利用するモジュールは API コストが発生します。運用時はバッチサイズ・頻度・エラーハンドリング方針を十分検討してください。
- Paper Trading と Live は DB を分離する設計になっています（PAPER_TRADING_SQLITE_PATH 等）。誤って本番 DB を上書きしないよう環境変数を確認してください。
- Docker 等で運用する場合は環境変数を適切にマウントし、data/ と logs/ の永続化を忘れないでください。

トラブルシュート
-----------------
- 設定検証で YAML の検証がスキップされる場合は PyYAML がインストールされていない可能性があります（pip install pyyaml）。
- SQLite / DuckDB のパスの親ディレクトリが無い場合、validate_config は警告を出します。起動時に自動作成されることもありますが、権限が必要です。
- OpenAI 呼び出しで rate-limit 等が発生するとリトライして最終的に失敗した場合は該当チャンクはスキップされます。ログを確認してください。

最後に
------
この README はソースのドキュメントコメントを基に作成しています。実運用する際は各 config/*.yaml や .env の中身、外部 API の設定、DB バックアップ・権限設定などを十分に確認してください。追加で README に記載したい内容（例: systemd サービス定義、Docker compose、具体的な実行例など）があれば教えてください。