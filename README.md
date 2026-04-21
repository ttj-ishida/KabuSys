README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模フレームワークです。
主要機能は戦略（ファクター計算、特徴量探索）、ポートフォリオ構築（候補選定・重量付け・株数算出）、
実行エンジン（ExecutionEngine／ブローカープラグイン対応）、監視（System / Trade / Risk）、
およびニュース NPL / レジーム判定などの補助機能を含みます。

主な設計方針
- DuckDB / SQLite を使ったオンディスクデータ（分析・ログ）
- 実売買（live）・ペーパートレード（paper_trading）・開発（development）を環境切替
- .env ベースで環境変数を管理（対話式ウィザード / 検証ツールあり）
- ログ出力は統一的に設定（コンソール＋日次ローテーションファイル）
- OpenAI を使ったニュース・マクロセンチメント評価をサポート（API キー必須）

機能一覧
--------
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 実行 / 監視プロセス起動スクリプト
  - run_execution: ExecutionEngine を起動（paper_trading 時は MockBroker 使用・DB 分離）
  - run_monitoring: SystemMonitor をポーリングして監視ログを記録
- 監視サブシステム
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス有無をチェック
  - trade_monitor / risk_monitor / monitoring_engine / kill_switch: 注文・ドローダウン・Kill Switch 管理
  - monitoring_db: SQLite スキーマ初期化・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ関連（純粋関数）
  - portfolio_builder: 候補選定・等配分/スコア配分
  - position_sizing: 株数算出・集約上限や単元丸め処理
  - risk_adjustment: セクター上限・レジーム乗数
- リサーチ
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - research.feature_exploration: 将来リターン・IC 等の分析ユーティリティ
- AI
  - ai.news_nlp: ニュースを OpenAI でスコアリングし ai_scores に書き込み
  - ai.regime_detector: ETF MA + マクロセンチメントで市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（SQLite を読みレポート出力）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 演算子を使用）
- SQLite（標準ライブラリ）、DuckDB（外部パッケージ）
- 推奨パッケージ: duckdb, psutil, openai, PyYAML（設定ファイル検証用）

1) 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

2) 必要パッケージインストール（例）
   pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3) .env 作成（対話式ウィザード）
   python -m kabusys.config_setup
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
   - KABUSYS_ENV は development / paper_trading / live のいずれか
   - PAPER_TRADING で動かす場合は分離された PAPER_TRADING_SQLITE_PATH を利用する

4) 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

5) ディレクトリと DB の準備
   - data/ 以下（logs/ と同様）は自動作成されることが多いですが、パーミッション等で失敗する場合は手動作成してください。
   - デフォルト SQLite / DuckDB パス:
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - DUCKDB_PATH: data/kabusys.duckdb

6) ログ出力先
   - デフォルト: logs/
   - 環境変数 LOG_DIR、LOG_LEVEL で調整可能

使い方
------
起動スクリプト
- 監視ループ（SystemMonitor）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト: 60）
  - 監視は常に「本番」sqlite_path を使用（環境にかかわらず monitoring DB は本番パスを参照）
  - 停止: data/stop_requested.flag を作成すると安全にループを抜けます

- 実行エンジン（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、paper DB（PAPER_TRADING_SQLITE_PATH）へ記録されるため本番 DB と完全分離されます
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します
  - 実行中の停止は data/stop_requested.flag を作成することでエンジンに伝播されます
  - 実行時に PID は data/execution.pid（デフォルト）へ記録されます

監視／停止フラグ
- data/stop_requested.flag: run_monitoring / run_execution の外部停止シグナル
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に対する強制停止指示）
- PID ファイル: デフォルト data/execution.pid（Settings.pid_file_path）

ツール
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡単なパス引数や環境変数 PAPER_TRADING_SQLITE_PATH から DB を指定
  - 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定を出力

AI 機能
- OpenAI を使う機能（news_nlp / regime_detector 等）は OPENAI_API_KEY 環境変数が必要
- API 呼び出しはリトライ・失敗時のフェイルセーフ（スコア 0 やスキップ）を備えています

主な環境変数（抜粋）
-------------------
必須
- JQUANTS_REFRESH_TOKEN      (J-Quants API)
- KABU_API_PASSWORD          (kabuステーション API パスワード)

運用設定（デフォルト値）
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 60  (run_monitoring 用のポーリング間隔)
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0|1 （起動時に kill.flag を自動でクリアするか）
- PAPER_FILL_MODE: instant|partial|never|reject （paper_trading の約定振る舞い）

ディレクトリ構成
----------------
（リポジトリ src/kabusys を想定した主要ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理 (.env 自動ロード含む)
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ + CRUD ラッパー
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （注文監視ロジック。今回の抜粋では参照）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート通知ロジック。抜粋では参照）
  - execution/                — ExecutionEngine と関連コンポーネント（OrderManager 等。抜粋参照）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                     — データ処理 / パイプライン（prices_daily 等の前処理を想定）
    - pipeline.py             — get_last_price_date 等ユーティリティ
    - stats.py                — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では Kill Switch / LINE 通知等の設定を必ず確認してください。
- .env は機密情報を含むため絶対に Git 等へコミットしないでください。
- OpenAI API を使用する箇所は API コストが発生します。バッチサイズやトークンサイズに注意してください。
- run_monitoring は monitoring DB に本番 sqlite_path を使用します。運用時の該当 DB のバックアップ方針を検討してください。
- process priority 設定は OS 権限に依存するため、権限不足で警告が出る場合があります（フォールバックあり）。

開発／拡張ポイント（参考）
--------------------------
- StrategyModel.md / PortfolioConstruction.md に従った拡張（ファクター・シグナル生成）
- ブローカークライアントの実装追加（kabuステーション用・他ブローカー）
- order_repository / trade_monitor の詳細ロジック整備
- alert_manager に Slack/LINE/メール通知を実装

ライセンス / 責任
-----------------
この README はソースコードから自動で要約したものであり、実際の運用前には必ずコードを読み、設定を確認してください。

以上。必要であれば各モジュールの詳しい使い方例（コマンド例・環境変数の具体値・テスト手順）を追記します。