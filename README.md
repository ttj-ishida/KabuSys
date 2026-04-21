KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買／研究／監視を想定した Python パッケージです。本リポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュースセンチメント評価などのコンポーネントを含みます。  
設計方針の一例として、以下を重視しています:

- 本番とペーパートレードの DB 分離（paper_trading モード）
- DuckDB を用いた分析・研究処理
- SQLite を用いた監視・ログ永続化
- OpenAI を利用したニュース NLP（任意）
- 実運用を意識したログ、プロセス優先度、Kill Switch 機構

主な機能
--------
- ExecutionEngine 起動／セッション管理（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、別 DB に記録
  - リスク管理、オーダーマネージャ、リコンサイル等を内包
- Monitoring（src/kabusys/run_monitoring.py / monitoring/*）
  - システム状態、取引ログ、リスク指標のポーリング監視
  - Kill Switch（データやドローダウン等の条件で実行エンジン停止フラグを書き込む）
  - アラート発行（AlertManager 経由）
- Portfolio construction（src/kabusys/portfolio/*）
  - 候補選定、重み算出、ポジションサイズ計算、セクター制限等の純粋関数群
- Research（src/kabusys/research/*）
  - ファクター計算（Momentum / Volatility / Value）、前方リターン・IC 計算、特徴量探索
  - DuckDB 経由で prices_daily / raw_financials などのテーブルを利用
- AI モジュール（src/kabusys/ai/*）
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores へ保存
  - 市場レジーム判定（ma200 とマクロニュースの合成）
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ、プロセス優先度設定、DB 初期化など
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意します。仮想環境を作成してください。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストールします（プロジェクトに requirements.txt がない場合は下記を参考に）。
   - pip install psutil duckdb openai
   - 追加で CLI 検証に PyYAML を使う場合: pip install pyyaml

3. .env を用意します（プロジェクトルートに配置）。
   - 手動で作成しても良いですが、対話式ウィザードを使うのが簡単です:
     - python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 便利な変数（よく使うもの）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - OPENAI_API_KEY — AI機能利用時に必要
     - LOG_LEVEL / LOG_DIR / PID_FILE_PATH / KILL_FLAG_CLEAR_ON_START などは Settings クラス参照

4. 設定を検証します:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリ等を作成（必要に応じて）:
   - mkdir -p data logs

基本的な使い方
-------------
- 実行エンジン（ExecutionEngine）を起動する:
  - production / development / paper_trading は KABUSYS_ENV によって切り替え
  - 例: KABUSYS_ENV=development python -m kabusys.run_execution
  - paper_trading のときは専用 SQLite（PAPER_TRADING_SQLITE_PATH）を利用する
  - 実行中にプロセス停止を要求するにはプロジェクトの data/stop_requested.flag を作成（run_execution はこのフラグを検知して停止）

- 監視ループを起動する:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
  - run_monitoring は停止フラグ data/stop_requested.flag を検知して終了します
  - 監視は常に（KABUSYS_ENV に関係なく）本番用の sqlite_path を使用します（監視用 DB は単一）

- 環境設定ウィザード:
  - python -m kabusys.config_setup
  - .env の作成・更新を対話式で行います

- 設定検証:
  - python -m kabusys.validate_config
  - config/*.yaml の存在や .env の必須項目をチェックします（PyYAML があれば YAML のパースも行います）

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定、指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH を参照

重要なファイル・フラグ・挙動
----------------------------
- data/stop_requested.flag
  - run_monitoring / run_execution が監視する「停止要求」フラグ
- data/kill.flag
  - KillSwitch が条件を満たすと作成。ExecutionEngine 停止の最終トリガーとして利用
- data/execution.pid（デフォルト）
  - ExecutionEngine が PID を書き込む場所（Settings.pid_file_path）
- 監視 DB（SQLite）
  - デフォルト: data/monitoring.db（Settings.sqlite_path）
  - init_monitoring_db() により必要テーブルを冪等的に作成します
- DuckDB
  - 分析用 DB。デフォルト: data/kabusys.duckdb（Settings.duckdb_path）

設定（主な環境変数）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（default: data/paper_trading.db）
- OPENAI_API_KEY — AI（news_nlp / regime_detector）利用時
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- LOG_LEVEL / LOG_DIR — ログ出力設定

注意事項 / 運用のヒント
----------------------
- run_monitoring は監視用にプロセス優先度を高く設定します（set_process_priority）
- 実行スクリプトはログ設定ユーティリティ (kabusys.utils.logging_setup.setup_logging) を使って stdout とファイル（logs/*.log）へ出力します
- paper_trading モードは発注を模擬し、本番 DB とは別ファイルに記録します。必ず PAPER_TRADING_SQLITE_PATH を確認してデータ分離を確保してください
- AI 関連機能は OPENAI_API_KEY が必要です。API 呼び出しの失敗はフェイルセーフで無視して継続する設計になっていますが、API 使用料やレート制限に注意してください
- validate_config は本番起動前に必ず実行して不足設定や危険な設定（KILL_FLAG_CLEAR_ON_START=1 等）を検出してください

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings の読み取り・自動ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留や約定異常の監視（存在）
    - risk_monitor.py — ドローダウンやポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 monitor をまとめる
    - alert_manager.py — 通知処理（存在）
  - execution/ (実行関連の実装: broker_factory, execution_engine, order_manager, risk_manager, reconciler, order_repository など)
  - portfolio/ (portfolio_builder, position_sizing, risk_adjustment)
  - research/ (factor_research, feature_exploration)
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロ）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

開発・拡張の指針
----------------
- DuckDB 側のスキーマ（prices_daily, raw_financials, raw_news 等）に依存する処理が多いため、データ整備が前提です
- AI モジュールは外部 API 呼び出しを含むため、テスト時は _call_openai_api をモックして単体テストを行ってください
- monitor / engine は外部副作用（DB 書き込み、ファイルフラグ）を行うため、統合テストでは一時ディレクトリを使うと良いです

ライセンス・その他
------------------
（リポジトリにライセンスファイルがあればここに追記してください）

問い合わせ
----------
実装上の質問やバグレポートはリポジトリの issue をご利用ください。README の補足・改善要望も歓迎します。