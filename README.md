KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・調査・監視を目的とした Python コードベースです。  
主に次の用途を持ちます：

- ExecutionEngine：発注・注文管理・リスク管理（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文状況・リスク指標の定期監視とアラート / Kill Switch
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：ニュースセンチメント（OpenAI）を用いたスコア・レジーム判定
- ツール群：ペーパートレード検証レポート生成など

主な特徴
--------
- 環境分離
  - KABUSYS_ENV による実行モード（development, paper_trading, live）
  - paper_trading 時は MockBroker を使用し、専用 SQLite に記録（本番 DB と分離）
- モジュール化
  - 実行、監視、ポートフォリオ構築、リサーチ、AI の機能が分離
- 永続化
  - DuckDB（分析用）と SQLite（監視・取引ログ）を併用
- 安全機構
  - Kill Switch（data/kill.flag）による安全停止
  - リスクモニタ（ドローダウン・ポジション上限）
- OpenAI 統合
  - ニュースのセンチメント集約（gpt-4o-mini 等）とレジーム検出（market_regime）

前提条件
--------
- Python 3.10 以上（型ヒントに | を使用しているため）
- 推奨パッケージ（主要な依存）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時に任意）
- OS: Windows / Linux / macOS に対応（ただし process priority / affinity はプラットフォーム依存）

セットアップ手順
----------------
1. リポジトリをクローンし、ソースルートに移動
   - 想定プロジェクト構成: src/kabusys/*

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. 環境変数の設定
   - .env を作成するか環境変数を直接設定します。対話式ウィザードを用意しています:
     - python -m kabusys.config_setup
   - 重要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
   - 自動 .env ロードはデフォルトで有効（プロジェクトルートの .env/.env.local を読み込み）
     - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

使い方
------
基本的な実行方法（モジュールとして起動）：

- ExecutionEngine を起動（本番 / ペーパートレードの切り替えは KABUSYS_ENV）
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag があれば起動しない
    - data/execution.pid に PID を書き、停止フラグにより終了可能

- Monitoring を起動（定期ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視モジュールは本番の sqlite_path を参照（環境にかかわらず）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 戻り値: 0 = OK, 1 = FAIL

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ関数（ライブラリとして呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - duckdb 接続を渡して日次の処理を行います（API キーが必要）

運用に関する注意
----------------
- Kill Switch / Stop Flag
  - data/kill.flag: Kill Switch が書き込まれると ExecutionEngine 停止を試みます
  - data/stop_requested.flag: run_monitoring / run_execution の外部停止フラグとして監視されています
- ログ
  - デフォルトは logs/ に日次ローテートで保存されます（kabusys.utils.logging_setup）
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルと一部カラムの追加（マイグレーション）を行います
- Paper Trading
  - paper_trading モードでは、本番 DB を使わないように設計されています。PAPER_TRADING_SQLITE_PATH を確認してください
- OpenAI
  - API 呼び出しはリトライ・エラーハンドリング実装済み。環境変数 OPENAI_API_KEY を設定してください
  - モデルと出力フォーマットに依存している点に注意

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です（完全な一覧ではありません）。

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数/設定管理（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- kabusys/execution/  — 発注関連（Engine, OrderManager, RiskManager 等）
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文/約定の監視（滞留注文等）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の生成・管理
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - alert_manager.py —（アラート通知管理: LINE 等のラッパーが想定される）

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（リスクベース等）
  - risk_adjustment.py — セクター制限・レジーム乗数

- kabusys/research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC 計算・統計サマリ

- kabusys/ai/
  - news_nlp.py — ニュースセンチメント集計（OpenAI 呼び出し、ai_scores 書き込み）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

- kabusys/utils/
  - logging_setup.py — 統一的なログ設定（コンソール + 日次ファイルローテーション）
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

データ・ログ配置（デフォルト）
-----------------------------
- data/kabusys.duckdb — DuckDB（分析データ）
- data/monitoring.db — SQLite（監視ログ）
- data/paper_trading.db — SQLite（ペーパートレード用、paper_trading モード）
- data/kill.flag — Kill Switch フラグファイル
- data/stop_requested.flag — 外部停止要求フラグ
- logs/ — ログファイル出力ディレクトリ（デフォルト）

開発・拡張のヒント
------------------
- DuckDB を使った分析処理はテストしやすく、prices_daily / raw_financials 等のテーブルを前提に設計されています
- OpenAI API 呼び出しはテスト時に _call_openai_api をモックして差し替え可能
- .env の自動ロードはプロジェクトルート検出ロジックを用いるため、パッケージ配布後も動作するよう設計されています
- ログ設定は全スクリプト共通の setup_logging を使うことで運用時に一貫したログ管理が可能です

ライセンス・コントリビュート
---------------------------
（ここにライセンス情報やコントリビュート方法を記載してください。リポジトリに合わせて追記を推奨します）

補足 / よくある質問
-------------------
Q: どの Python バージョンで動きますか？  
A: Python 3.10 以上を推奨します（型注釈に | を使用）。

Q: 本番での停止はどう行いますか？  
A: Kill Switch（data/kill.flag）を書き込めば ExecutionEngine は停止を受けます。Monitoring は kill.flag を評価して通知も行います。

Q: OpenAI の料金対策は？  
A: batch サイズ制御、記事数/文字数のトリム、リトライ制御が実装されています。API キーのローテーション・呼び出し頻度制御は運用で管理してください。

以上が主要な README 相当の概要です。必要であれば「インストール用 requirements.txt の推奨内容」「systemd / Supervisor の起動ユニット例」「config/*.yaml の説明」などを追加で作成します。どれを優先しますか？