KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／実行スクリプト群です。  
本リポジトリは以下の機能群を含みます: 注文実行エンジン、監視モジュール（プロセス・データ鮮度・リスク監視）、ポートフォリオ構築ユーティリティ、研究用ファクター計算、OpenAI を用いたニュース NLP / レジーム判定、各種 CLI ユーティリティ（.env ウィザード / 設定検証 / ペーパートレード検証レポート生成）など。

主な設計方針
- 実行（Execution）と監視（Monitoring）、ペーパートレード用 DB を明確に分離
- DuckDB を用いた分析／履歴データ保存、SQLite を監視・ログ保存に使用
- OpenAI API を使った NLP 機能はフェイルセーフ設計（API 失敗時は処理を続行）
- ルックアヘッドバイアス対策（日時の直接参照を抑制した設計）

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレード（KABUSYS_ENV）を切り替え可能
  - Broker クライアントの抽象化（Mock を含む）
  - リスク管理 / 注文管理 / 再整合（reconciler） を組み合わせてセッション実行
- 監視ポーリング（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - Kill Switch（条件により data/kill.flag を書き込み、Execution を停止）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 設定関連 CLI
  - config_setup: 対話式 .env ウィザード（.env を生成/更新）
  - validate_config: .env と config/*.yaml の事前検証ツール（--strict オプションあり）
- 研究／ファクター計算（research）
  - momentum / volatility / value 等のファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分・スコア加重、ポジションサイズ計算（リスクベース）、セクターキャップ適用、レジーム乗数
- AI 機能（ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores への書き込み
  - regime_detector: ETF（1321）MA とマクロニュースの合成によるレジーム判定
- モニタリング DB（monitoring/monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
- ユーティリティ
  - ログ設定（utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（utils.process_priority）
- ツール
  - paper_verification_report: ペーパートレード DB をもとに検証レポートを生成

前提・依存関係
--------------
- Python 3.10 以上（注: 型ヒントで X | Y を使用）
- 必要な主な Python パッケージ（用途別）
  - duckdb
  - psutil
  - openai
  - pyyaml（config ファイル検証のため任意）
- 標準ライブラリ: sqlite3, threading, logging など

インストール例（開発環境）
------------------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - git clone ... && cd <project_root>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   -（任意）PyYAML を使う場合: pip install pyyaml

セットアップ手順（運用開始まで）
------------------------------
1. ディレクトリ作成
   - data/ と logs/ を作成しておくと良い（スクリプトが自動生成することもある）
     - mkdir -p data logs

2. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development/paper_trading/live）等を設定

3. 設定検証
   - python -m kabusys.validate_config
   - 本番前に --strict モードで警告も失敗扱いにする: python -m kabusys.validate_config --strict

4. （任意）ペーパートレード DB の初期化
   - PAPER_TRADING_SQLITE_PATH を .env で指定するかデフォルト data/paper_trading.db を使用
   - 実行エンジンは KABUSYS_ENV=paper_trading の場合に MockBroker を使用して paper_trading 用 DB に書き込む

実行方法（主要コマンド）
-----------------------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数により挙動が変わる:
    - paper_trading: MockBroker 使用、DB は data/paper_trading.db（分離）
    - live: 実際のブローカーに発注（注意）
  - 起動時に data/stop_requested.flag が存在すると起動を中止
  - 実行中に data/stop_requested.flag を作成するとエンジン停止をトリガー

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用する点に注意

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知（任意）
- OPENAI_API_KEY — AI 機能利用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（整数、デフォルト 60）
- PAPER_FILL_MODE — paper_trading 時の MockBroker の fill モード（instant/partial/never/reject）

ログ
----
- ログの初期化は kabusys.utils.logging_setup.setup_logging で行われ、全起動スクリプトで共通の設定を使用します。
- 出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log を日次ローテーションで出力（デフォルト 30 日保持）
- LOG_DIR 環境変数でログ保存先を指定可能

停止 / Kill Switch
------------------
- 監視モジュールや運用者は data/kill.flag を作成（KillSwitch）して ExecutionEngine に停止シグナルを送ることができます。  
- run_execution / run_monitoring は data/stop_requested.flag を監視して安全にシャットダウンできます。  
- .env の KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に kill.flag を自動クリアします（本番では推奨しません）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — Settings クラス、.env 自動読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM センチメント処理（ai_scores 書込み）
  - regime_detector.py — マクロ + ETF MA によるレジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・読み書きラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - kill_switch.py — Kill Switch ロジック
  - monitoring_engine.py — 複数モニタのポーリング統合
  - alert_manager.py —（アラート送信、実装参照）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行関連（詳細は各ファイル参照）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・統計解析
- monitoring/（上に同）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート CLI
- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度設定

開発メモ / 注意点
----------------
- Settings クラスは .env の自動読み込みを行います（プロジェクトルートが見つからない場合はスキップ）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB と完全に分離されます（paper_sqlite_path を使用）。
- OpenAI/API 呼び出しまわりはリトライやバックオフ、レスポンス検証を実装していますが、API キー設定や利用料などの運用面の配慮が必要です。
- ローカルでの検証・単体テストを行う際は、KABUSYS_ENV=development を使用してください（実発注は行われません）。
- Python の型ヒントやコード中の記述から Python 3.10 以上を想定しています。

問い合わせ / 貢献
-----------------
バグ報告や機能追加は Issue を立ててください。Pull Request は歓迎します。  

以上が本リポジトリの概要とセットアップ・使用方法の簡易 README です。必要であれば各モジュール（ExecutionEngine、monitoring の詳細な起動オプションや設定ファイル例、CI / デプロイ手順など）について追補版を作成します。どの部分を詳細化したいか教えてください。