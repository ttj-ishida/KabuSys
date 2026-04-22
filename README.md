KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python コードベースです。本リポジトリは以下の主要機能を含みます：

- 発注エンジン（ExecutionEngine）とペーパートレード分離
- 監視（Monitoring）: システム状態、注文ログ、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP（OpenAI を使ったセンチメントスコアリング）
- CI 用の設定ウィザード / 設定検証ツール / 検証レポート生成ツール
- 統一的なログ設定、プロセス優先度設定ユーティリティ

アーキテクチャは「実行」「監視」「リサーチ／AI」「ポートフォリオロジック」などの責務を明確に分離しています。データは主に SQLite（監視・ペーパートレード用）と DuckDB（分析用）に永続化します。

主な機能
--------
- ExecutionEngine（run_execution.py）  
  - 本番 / ペーパートレードモードを切り替え可能（KABUSYS_ENV）
  - BrokerClientFactory により実口座／モックを分離
  - RiskManager / OrderManager / Reconciler 等を組み合わせて注文実行を行う
  - 停止フラグ（data/stop_requested.flag）や kill.flag による停止制御、PID 管理

- Monitoring（run_monitoring.py / monitoring/*）  
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 注文の滞留や約定異常などの検出（trade_logs テーブル参照）
  - RiskMonitor: ドローダウンやポジション上限の監視とアラートログ
  - KillSwitch: 一定条件で data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB: SQLite にテーブルを作成・書き込みする永続化層

- Portfolio（portfolio/*）  
  - 候補選定、等重／スコア加重の計算、セクター上限適用、ポジションサイズ計算（単元株丸め含む）

- Research（research/*）  
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（情報係数）、特徴量サマリー

- AI（ai/*）  
  - news_nlp: raw_news テーブルを集約して OpenAI に送り銘柄別センチメントを計算し ai_scores に永続化
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を算出

- ツール  
  - config_setup.py: .env を対話式に作成・更新
  - validate_config.py: 起動前に環境変数 / config/*.yaml を検証
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

セットアップ手順
----------------

前提
- Python 3.10 以上（型アノテーションの新構文を使用）
- SQLite は標準ライブラリで利用可能
- DuckDB, psutil, openai 等の外部パッケージが必要

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: PyYAML（config ファイル検証用）: pip install pyyaml

   （リポジトリに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を元に手動編集してプロジェクトルートに .env を配置

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正し、--strict を付けると警告もエラー扱いにできます:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成（必要に応じて）
   - data/ （デフォルト DB やフラグファイル）
   - logs/ （ログ出力先）
   これらは多くのユーティリティが自動で作成しますが、権限などで失敗する場合は手動作成してください。

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
  - paper_trading: MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、default: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、default: instant）
- KILL_FLAG_CLEAR_ON_START: 本番起動時の kill.flag 自動クリア（0/1、default: 0）

使い方（主要コマンド）
--------------------

- 環境セットアップ（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（監視 DB）を使用します（環境に依存せず本番 DB を参照する仕様）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定するとペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使い MockBrokerClient が選択されます
  - 起動時に data/stop_requested.flag があれば起動を中止します
  - 停止は data/stop_requested.flag の作成や kill.flag によって行う仕組みです

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / レジーム判定（プログラム呼び出し）
  - news NLP のスコアリング関数を呼ぶ例（スクリプト内 / REPL）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか環境変数を使用
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

ログとローテーション
-------------------
- ログは kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
- デフォルトログディレクトリ: logs/（日次ローテーション、30日保持）
- app_name 引数により logs/<app_name>.log が生成されます（例: "execution" / "monitoring"）

停止・Kill Switch の挙動
-----------------------
- data/stop_requested.flag: run_monitoring / run_execution スクリプトが監視し、存在するとループを終了します
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止を促す（監視側ロジックで評価）
- Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要ファイル／ディレクトリと簡単な説明です：

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を指定可能。

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じてペーパー/本番切替。

- config.py
  - 環境変数の読み込み・Settings クラス。.env 自動読み込み機構を持つ。

- config_setup.py
  - .env を対話式に生成・編集するウィザード。

- validate_config.py
  - 起動前に環境変数や config/*.yaml の存在／整合性を検証する CLI。

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定、リスク制限、単元丸め
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリー

- ai/
  - news_nlp.py: ニュースセンチメントの LLM スコアリング
  - regime_detector.py: 市場レジーム判定（MA200 + マクロ NLP）

- monitoring/
  - monitoring_db.py: SQLite テーブル作成・読み書きラッパー
  - system_monitor.py: システム状態・データ鮮度の監視
  - trade_monitor.py: 注文ログの監視（存在）
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag の書き込みロジック
  - monitoring_engine.py: 各 Monitor を束ね日次周期で実行
  - alert_manager.py: （アラート送信の抽象化: LINE など）

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

開発・運用上の注意
------------------
- 環境変数の管理: .env は機密情報を含むため決して Git にコミットしないでください
- 本番モード（KABUSYS_ENV=live）では LINE 等のアラート設定を必ず確認してください（validate_config で警告が出ます）
- OpenAI を使う機能は API コスト・レイテンシに注意。API キーは OPENAI_API_KEY に設定してください
- DuckDB / SQLite ファイルはデフォルトで data/ 下に作成されます（PAPER_TRADING 用 DB は分離）
- process_priority や CPU affinity の設定は OS 権限に依存します。権限不足時は警告が出てスキップされます

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス表記はリポジトリに含めてください（このサンプルでは未記載）

問い合わせ・貢献
----------------
- バグ報告や機能追加は Issue を立ててください。
- 大規模な変更は PR を作成し、ユニットテスト・静的解析・設定検証を追加してください。

以上がこのコードベースの README 相当の説明です。必要であれば、サンプル .env テンプレート、起動時のログ出力例、よくあるトラブルシュート（権限や DB パス関連）などの追加情報も作成します。どの情報を追加しますか？