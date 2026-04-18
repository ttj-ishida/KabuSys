README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注、オーダー管理、リスク管理を行う。
- 監視（Monitoring）: システム状態、オーダー状況、リスク指標を定期ポーリングしてログ・アラート・Kill Switch を管理。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限などの純粋関数群。
- 研究（Research）: DuckDB を用いたファクター計算・特徴量探索・IC計算。
- AI モジュール: ニュースのセンチメント評価（OpenAI）や市場レジーム判定を行う。
- ツール: ペーパートレード検証レポート生成などの補助スクリプト。
- 設定支援: .env の対話式生成（config_setup）と起動前検証（validate_config）。

主な設計方針
- DB（監視用 SQLite / 分析用 DuckDB）を区別して扱う。
- Paper Trading は本番 DB から完全分離（デフォルトで data/paper_trading.db を使用）。
- ルックアヘッドバイアスを避ける設計（AI / リサーチ関連関数は date 引数を明示的に受け取る）。
- フェイルセーフ：外部 API（OpenAI 等）に依存する処理は失敗時に安全側のフォールバックを持つ。

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading 用モードへ切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定 / 検証
  - config_setup.py: .env を対話的に生成・更新
  - validate_config.py: 環境・設定ファイルを事前検証（--strict で警告も FAIL）
- 監視関連
  - monitoring_engine.py: 各モニタを束ねるエンジン
  - system_monitor.py / trade_monitor.py / risk_monitor.py: それぞれの監視処理
  - kill_switch.py: kill.flag による停止シグナル生成
  - monitoring_db.py: 監視ログの永続化（SQLite）
- 実行関連（execution/*）
  - BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等（発注フロー）
- ポートフォリオ（portfolio/*）
  - 候補選定・重み算出・単元株丸め・セクター制約・レジーム乗数など
- 研究（research/*）
  - ファクター計算（momentum/volatility/value）、将来リターン、IC、統計サマリ等（DuckDB 前提）
- AI（ai/*）
  - news_nlp: OpenAI を用いたニュース集約→センチメントスコアリング
  - regime_detector: マクロ＋ETF MA200 から市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポートの生成

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 可能であれば requirements.txt を用意している想定:
     - pip install -r requirements.txt
   - 主要なパッケージ（例）:
     - pip install duckdb psutil openai
   - 注: 実際の requirements.txt がない場合は上記を個別にインストールしてください。

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env をプロジェクトルートに作成
   - 必須環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の重要変数
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題がある場合はエラー/警告が出力されます。--strict を付けると警告も失敗扱いになります。

使い方（起動 / 実行例）
---------------------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は monitoring 用の SQLite（Settings.sqlite_path）を使用します（環境に関わらず本番 sqlite_path を参照）。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 実行中は data/execution.pid が作成されます。停止フラグ data/stop_requested.flag を作成するとループが終了します（スクリプトが検出して Graceful に停止）。

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でも DB を指定できます。

- AI / レジーム判定の呼び出し（ライブラリとして）
  - import して関数を呼ぶ例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - どちらも OpenAI API キー（引数 or 環境変数 OPENAI_API_KEY）が必要です。

停止・Kill スイッチについて
--------------------------
- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring.py / run_execution.py は stop_requested.flag を監視し、存在するとループを終了します（外部的に停止要求を出す用途）。
- kill.flag (Settings.kill_flag_path / default: data/kill.flag)
  - KillSwitch（監視側）がリスクトリガーを検出した場合に書き込まれる flag で、ExecutionEngine に対する停止シグナル用途に使われます。
  - 手動で削除する場合: rm data/kill.flag
  - Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に自動でクリアされます（本番では 0 推奨）。

ログ・データ
------------
- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（setup_logging による）。
  - コンソール出力は stdout に出力されます。
- データベース
  - DuckDB: デフォルト data/kabusys.duckdb（分析用）
  - SQLite (監視): デフォルト data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（paper_trading モード時に使用）

主要な環境変数一覧
------------------
必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（推奨）
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: AI 機能使用時
- DUCKDB_PATH
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）を上書き

ディレクトリ構成（主なファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールと概要です。

- __init__.py
  - パッケージ定義、バージョン情報

- config.py
  - Settings クラス: 環境変数読み取り・検証・デフォルト提供
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等
  - （発注ロジック・リスク制御を含む）

- monitoring/
  - monitoring_db.py: SQLite テーブル定義・読み書き
  - monitoring_engine.py: 各 Monitor を束ねる
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: 注文・約定監視（略記）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書き込みユーティリティ
  - alert_manager.py: アラート送信管理（LINE 連携など、実装箇所を参照）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・資金スケール調整
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: momentum/value/volatility 等の計算（DuckDB 参照）
  - feature_exploration.py: 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py: ニュースセンチメント（OpenAI） → ai_scores 書き込み
  - regime_detector.py: マクロ+ETF MA200 を用いたレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート出力

- utils/
  - logging_setup.py: 統一的なログ設定
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

トラブルシューティング・注意事項
--------------------------------
- DB ファイルやログディレクトリの親ディレクトリが存在しないと警告が出る場合があります（validate_config が警告を出します）。必要なら手動で作成してください（例: mkdir -p data logs）。
- 開発環境では KABUSYS_ENV=development を使用してください。live は注意して使用（validate_config は live の場合に追加警告を出します）。
- OpenAI 関連は API 呼び出しに失敗してもシステムが継続するよう設計されていますが、AI 機能を有効にするには OPENAI_API_KEY の設定が必要です。
- run_monitoring は監視用 DB（Settings.sqlite_path）を使用します。paper_trading モードでも同じ監視 DB を参照しますのでご注意ください。
- stop/kill フラグファイル（data/stop_requested.flag / data/kill.flag）の管理は運用上重要です。自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番では 0 を推奨します。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報やコントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在しない場合は管理者へ問い合わせてください）。

最後に
------
README は最低限のガイドです。実運用にあたっては config/*.yaml の設定・strategy の実装・ブローカークライアントの安全性（注文ロジックの二重チェック）を十分に確認してください。質問や拡張のご要望があれば具体的な箇所を示していただければドキュメントや使用例を追補します。