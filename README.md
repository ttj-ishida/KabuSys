README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能を持つモジュール群が含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視 / キルスイッチ・アラート基盤（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- ファクター計算・特徴量探索（Research）
- ニュース NLP / レジーム判定（AI）
- ユーティリティ（ログ・プロセス優先度設定など）
- ツール（.env ウィザード、設定検証、Paper Trading レポート等）

主な目的は「戦略の研究」「日次/週次のファクター計算」「バックテスト/ペーパートレード用の安全な実行」「本番を想定した運用監視と自動停止（Kill Switch）」です。

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）による .env の対話生成
- 起動前チェック（kabusys.validate_config）で必須環境変数や設定ファイルを検証
- ExecutionEngine 起動（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading DB に分離
  - 停止フラグ（data/stop_requested.flag）で安全停止
- Monitoring（run_monitoring.py、monitoring_engine モジュール）
  - システム状態・データ鮮度・取引ログ・リスク（ドローダウン・ポジション上限）監視
  - kill.flag による ExecutionEngine 停止指示（KillSwitch）
  - 監視ログは SQLite（monitoring.db）に永続化
- Portfolio モジュール
  - 候補選定、等配分 / スコア配分、リスクベースのポジション決定、セクター上限、レジーム乗数
- Research モジュール
  - momentum / volatility / value ファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）等の探索用関数群
- AI モジュール
  - ニュースを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA を組み合わせた market regime 判定
  - API 失敗時のフェイルセーフやリトライロジックを実装
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを出力
  - config_setup: .env を対話式に作成
  - validate_config: .env と config/*.yaml の検証

セットアップ手順
----------------
1. Python 環境を準備
   - 推奨: Python 3.10+（パッケージの型ヒントや依存関係に依存）
   - 仮想環境を作成して有効化することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - main に使われているライブラリ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証時に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使ってください。）

3. 環境変数 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）
   - 必須項目の例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=... （AI 機能を使う場合）
   - 重要な変数（主なもの）
     - KABUSYS_ENV: 実行環境（development / paper_trading / live）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 時の DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict をつけると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

5. 初期 DB の作成
   - monitoring 用のテーブルは run_monitoring/run_execution が起動時に自動で初期化します。
   - DuckDB ファイルは最初のアクセス時に作成されます。

使い方
------
主要なコマンド例を示します。

- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（本番的な監視プロセス）
  - MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を指定（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 注意: run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- ExecutionEngine 起動（発注エンジン）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使用され、paper_trading DB に記録されます。
  - python -m kabusys.run_execution
  - 実行前に data/stop_requested.flag があると起動せず終了します（停止フラグ）
  - 実行中に stop_requested.flag を作成すると安全に停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging で統一設定されます。
- デフォルトでは stdout と logs/<app_name>.log（日次ローテート、30日保持）に出力します。
- 環境変数 LOG_LEVEL / LOG_DIR で変更可能。

停止 / キルフロー
-----------------
- 停止フラグ:
  - data/stop_requested.flag
    - run_monitoring と run_execution はこのファイルの存在を監視し、存在時に安全停止します。
- Kill Switch:
  - monitoring の監視で重大リスク（ドローダウンやポジション上限）を検出した場合、data/kill.flag を書き込みます。
  - ExecutionEngine はこれを参照して自動停止を受けます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

環境固有の挙動
--------------
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング。0 以下や不正値はデフォルト 60 秒にフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading のとき DB を完全に分離（PAPER_TRADING_SQLITE_PATH）し、MockBrokerClient を使用します。
- AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフが備わっていますが、キーが未設定だと ValueError を送出する関数もあります。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主要ファイル/ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py                      : パッケージ定義（バージョンなど）
  - config.py                        : Settings クラス（環境変数読み込み・自動 .env ロードロジック）
  - config_setup.py                  : .env 対話式ウィザード
  - validate_config.py               : 起動前設定検証 CLI
  - run_monitoring.py                : Monitoring プロセス起動スクリプト
  - run_execution.py                 : ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   : ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py                    : ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py             : 市場レジーム判定（ETF MA + マクロ NLP）
  - research/
    - factor_research.py             : momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py         : 将来リターン、IC、統計サマリー
  - portfolio/
    - portfolio_builder.py           : 候補選定・重み計算
    - position_sizing.py             : 発注株数計算・スケーリング（単元丸め等）
    - risk_adjustment.py             : セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py               : SQLite ベースの永続化層（テーブル定義・CRUD）
    - system_monitor.py              : システム状態・データ鮮度チェック
    - trade_monitor.py               : （取引監視ロジック）
    - risk_monitor.py                : ドローダウン・ポジション上限監視
    - kill_switch.py                 : kill.flag の書き込み（Execution 停止）
    - monitoring_engine.py           : 各 Monitor を束ねる実行ループ
    - alert_manager.py               : （通知管理・LINE 連携など）
  - execution/
    - execution_engine.py            : 実行エンジン（Session 実行ループ）
    - broker_factory.py              : ブローカークライアント生成（Mock/実装切替）
    - order_manager.py               : 注文管理
    - order_repository.py            : 注文永続化/復元
    - reconciler.py                  : 発注整合処理
    - risk_manager.py                : 発注前リスクチェック
  - utils/
    - logging_setup.py               : ログ設定ユーティリティ
    - process_priority.py            : 優先度・CPU affinity 設定ユーティリティ
  - data/ (ランタイムに生成される想定)
    - kill.flag / stop_requested.flag / execution.pid / monitoring.db / paper_trading.db 等

補足・運用上の注意
------------------
- 本番（KABUSYS_ENV=live）では特に kill.flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では推奨されません。
- run_monitoring は監視 DB（SQLite）を使ってリスクイベントやシステム稼働状況を永続化します。テーブルは起動時に自動で初期化・マイグレーションされます。
- AI モジュールは API 呼び出しの失敗に対して保守的にフォールバックする設計ですが、API 利用料やレートリミットに注意してください。
- DuckDB を使った研究モジュールは大規模データ向けの高速集計が可能です。prices_daily / raw_financials / raw_news 等のテーブルを用意して利用してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス表記や貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

お問い合わせ
------------
- 実装や仕様に関する質問があれば、リポジトリの Issue を立てるか、プロジェクト内の担当者にお問い合わせください。

以上が本コードベースの概要と導入・運用ガイドです。必要であれば各モジュールの詳細な使い方（API シグネチャ、例、ユニットテスト例）を追加で作成します。どの部分を詳しく書いてほしいか教えてください。