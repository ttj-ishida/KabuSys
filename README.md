README
=====

概要
----
KabuSys は日本株向けの自動売買基盤（プロトタイプ）です。  
戦略（ファクター計算・ポートフォリオ構築）、発注実行エンジン、監視・アラート、ペーパートレード検証、AI を用いたニュースセンチメント評価などのコンポーネントを含んでいます。モジュール構成はできるだけ疎結合に設計され、ローカル開発からペーパートレード、本番運用までを想定しています。

主な機能
--------
- ExecutionEngine：発注ロジックと注文管理（paper_trading では MockBroker を使用）
- Monitoring：システム状態、データ鮮度、注文の滞留・約定異常、リスク（ドローダウン・ポジション数）を監視し、kill.flag による停止等の保護機構を提供
- Portfolio construction：候補選定、重み付け、ポジション決定（単元株丸め・集約キャップ調整）
- Research：DuckDB を用いたファクター計算（Momentum/Volatility/Value）・将来リターン計算・IC 等の解析ユーティリティ
- AI モジュール：ニュースを LLM（OpenAI）で評価し銘柄ごとのスコアを生成、レジーム検出のためのマクロセンチメント評価
- CLI ツール：.env ウィザード（config_setup.py）、設定検証（validate_config.py）、ペーパートレード検証レポート生成ツール（paper_verification_report.py）
- ロギング：統一的な logging 設定（コンソール＋日次ローテートファイル）
- 永続化：SQLite（監視ログ・ペーパートレード DB）および DuckDB（分析用）

前提条件
--------
- Python 3.10 以上（型ヒントに | 演算子などを使用）
- 以下の主要ライブラリ（実行する機能に応じて必要）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行う場合に任意）
- SQLite は標準ライブラリで利用可能

インストール
------------
1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   例:
   - pip install duckdb psutil openai pyyaml

   ※ プロジェクトで requirements.txt があればそちらを利用してください。

初期設定 (.env)
---------------
1. 対話式ウィザードで .env を生成 / 更新:
   - python -m kabusys.config_setup

2. 作成後、設定の検証:
   - python -m kabusys.validate_config
   - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や DB パス等のチェックを行うことができます。
   - `--strict` を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（上書き用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効。production では注意）

実行方法
--------
- ExecutionEngine を起動（モードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動前に data ディレクトリや .env を整備してください。
  - paper_trading 環境では本番 DB と分離された paper_trading DB に注文ログが残ります。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL により間隔（秒）を上書き可（デフォルト 60 秒）
  - 監視ループは data/stop_requested.flag の存在で終了します（停止用フラグ）

- ペーパートレード検証レポート（コマンドラインツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

運用に関する注意
----------------
- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch が書き込まれると Execution エンジンは停止処理を開始します。
  - 監視のポーリングループや ExecutionEngine の外部停止には data/stop_requested.flag が使われます。
  - 本番運用（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（自動クリアは危険）。

- ログ
  - ログは標準出力（stdout）と logs/<app_name>.log（タイムローテーション）に出力されます。ログディレクトリは LOG_DIR 環境変数で変更可。

- DB
  - monitoring 用の SQLite（SQLITE_PATH）には監視ログや trade_logs、positions、risk_logs、dashboard 等が作成されます。init_monitoring_db() は冪等的にスキーマを作成・マイグレーションします。
  - DuckDB は分析用に利用します。research や AI モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials / raw_news 等のテーブルを参照します。

開発・デバッグのヒント
--------------------
- Logging を有効にして debug するには LOG_LEVEL=DEBUG を設定して起動してください。
- 開発中に監視ループやエンジンを即停止したい場合は data/stop_requested.flag を作成してください（監視は存在を検知して終了します）。KillSwitch によりデフォルトで kill.flag が書き込まれれば ExecutionEngine 停止を誘発します。
- AI 機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API エラーはリトライやフェイルセーフ（0.0 でフォールバック）実装がありますが、API 制約・コストに注意してください。
- 設定ファイル（config/*.yaml）は存在しない場合に警告が出ます。PyYAML が入っていれば YAML のパース検証を行います。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                      -- 環境変数・Settings の実装（.env 自動ロード機能含む）
- config_setup.py                -- .env 対話式ウィザード
- validate_config.py             -- 起動前設定検証 CLI
- run_execution.py               -- ExecutionEngine 起動スクリプト（メイン）
- run_monitoring.py              -- SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py  -- ペーパートレード検証レポート CLI
- utils/
  - logging_setup.py              -- 統一ログ設定ユーティリティ
  - process_priority.py           -- プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py              -- SQLite スキーマ初期化／永続層
  - system_monitor.py             -- システム状態・データ鮮度監視
  - trade_monitor.py              -- 注文ログ・滞留・約定異常検出（存在）
  - risk_monitor.py               -- ドローダウン・ポジション上限監視
  - kill_switch.py                -- kill.flag 書き込みロジック
  - monitoring_engine.py          -- 各 Monitor を束ねるエンジン
  - alert_manager.py              -- （アラート送信の実装想定）
- execution/                      -- ExecutionEngine や OrderManager, BrokerFactory 等（発注系）
- portfolio/
  - portfolio_builder.py          -- 候補選定・重み計算
  - position_sizing.py            -- 株数計算・集約キャップ
  - risk_adjustment.py            -- セクターキャップ・レジーム乗数
- research/
  - factor_research.py            -- ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py        -- 将来リターン・IC・統計サマリー等
- ai/
  - news_nlp.py                   -- ニュース NLP スコアリング（OpenAI 使用）
  - regime_detector.py            -- レジーム判定（MA200 + マクロセンチメント）
- data/                           -- 実行時に生成されることの多いディレクトリ（DB / flags / pid 等）
- logs/                           -- ログ出力先（デフォルト）

（注）上記はリポジトリに存在するファイル群の抜粋説明です。実際のファイル配置や追加モジュールはプロジェクトの内容によります。

よくある操作例
----------------
- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 実行エンジン起動（バックグラウンド等は OS のサービス管理を利用）
  - python -m kabusys.run_execution

- 監視開始
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （ポーリング間隔30秒）

ライセンス / 貢献
-----------------
本リポジトリにライセンスファイルが含まれている場合はそれに従ってください。貢献やバグ報告は Issue / Pull Request を通じて行ってください。

最後に
-------
本 README はコードベースの主要機能と運用手順をまとめたものです。詳細な設計や各モジュールの仕様（PortfolioConstruction.md, StrategyModel.md 等）がリポジトリに含まれている場合はそちらも参照してください。何か補足が必要であれば、どの部分を詳しく書いて欲しいか教えてください。