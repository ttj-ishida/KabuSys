# KabuSys

日本株向け自動売買システム（プロトタイプ）

このリポジトリは、銘柄選定・ポートフォリオ構築・発注エンジン・監視・リスク制御・研究用ユーティリティを含む自動売買基盤の一部実装です。設計方針として「本番 DB とペーパートレード DB の分離」「外部 API 呼び出しでのフェイルセーフ」「テストしやすい純粋関数群」「ログの統一管理」等が採用されています。

## 主な特徴（機能一覧）
- ExecutionEngine
  - 実際のブローカークライアントまたはペーパートレード用の Mock を使用して発注を実行
  - リスク管理（ポジション上限・ドローダウン等）
  - 発注・約定ログの永続化
- Monitoring
  - システム（CPU/メモリ/ディスク）・プロセス死活・データ鮮度監視
  - トレードログの監視（滞留注文、約定異常など）
  - Kill Switch（条件に応じて停止フラグを書き込み ExecutionEngine を停止）
  - 監視ログを SQLite に永続化
- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定（スコア順）、等重・スコア重み、リスクベースのポジションサイズ算出
  - セクター集中制限、レジーム乗数対応
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 前方リターン計算、IC（Information Coefficient）などの統計ツール
- AI（OpenAI）連携
  - ニュースを LLM でスコアリングして ai_scores に保存（gpt-4o-mini を想定）
  - マクロニュースと ETF の MA を使った市場レジーム判定
  - API エラーに対するリトライやフェイルセーフを備える
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - 統一的なログ設定ユーティリティ、プロセス優先度設定ユーティリティ等

## 必要条件（概略）
実行環境に依存しますが、主要な Python パッケージは以下の通りです（requirements.txt は本リポジトリに含まれている想定でそちらを使用してください）。
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（設定 YAML の検証を行う場合）
- （標準ライブラリ）sqlite3, logging, threading など

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限 duckdb, psutil, openai をインストール）
4. .env の初期作成
   - python -m kabusys.config_setup
   - 対話形式で必要な環境変数を設定できます（J-Quants トークン、kabu API パスワードなど）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って .env を修正

## 主要な環境変数（抜粋）
（config.py のプロパティに基づく主要項目。デフォルト値は `.env.example` を参照してください。）
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）（デフォルト: development）
  - paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject）（デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視（monitoring）用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（開発用。0/1。デフォルト: 0）
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒。run_monitoring で使用。デフォルト: 60）

注意: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等は必須です。`.env` を作成して設定してください。

## 実行方法（代表的なコマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）
- ExecutionEngine（トレード実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に書き込む設計です
  - 起動前に data/stop_requested.flag があると起動をスキップします
- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番 sqlite_path（SQLITE_PATH）を参照します（KABUSYS_ENV に依存しません）
  - 監視スクリプトは data/stop_requested.flag を検知して終了します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY（または api_key 引数）が必要。API 呼び出し失敗時はフェイルセーフが組み込まれています。

## ログ・ファイル・データ
- ログ
  - デフォルトは logs/ に日次ローテーションで出力（例: logs/execution.log, logs/monitoring.log）
  - setup_logging() を共有しているため全コンポーネントで統一されたログフォーマット・ローテーションが利用されます
- データディレクトリ（デフォルト）
  - data/kabusys.duckdb — DuckDB（分析用）
  - data/monitoring.db — 監視用 SQLite（system_status, trade_logs, positions, risk_logs, dashboard）
  - data/paper_trading.db — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時）
  - data/execution.pid — ExecutionEngine の pid ファイル
  - data/kill.flag — Kill Switch（監視が書き込み、ExecutionEngine は存在を検出して停止）
  - data/stop_requested.flag — 開発用の停止指示ファイル（run_* スクリプトが検知して終了）

## ディレクトリ構成（抜粋）
リポジトリ内の主要なディレクトリ / ファイル例:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込みロジック
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在想定: アラート送信ロジック)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（実際のファイル数・構成はリポジトリの内容に依存します。上はこの README 作成時点で提供されたソースを反映しています。）

## 開発・運用上の注意
- 本番運用時は KABUSYS_ENV=live を使用します。validate_config は live 設定時に追加の警告を出します（LINE 通知等）。
- Kill Switch（data/kill.flag）と stop フラグ（data/stop_requested.flag）により外部から安全にプロセス停止できます。KILL_FLAG_CLEAR_ON_START=1 を本番で設定しないでください（危険）。
- Paper Trading は本番 DB と物理的に分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 等外部 API を使う機能は API キーが必須です。API エラー時の挙動はフェイルセーフ（スコア 0 やスキップ）になるよう設計されていますが、API コスト・レート制限に注意してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。ログが出力されているかを必ず確認してください。

## 参考コマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はコードベースの主要な使い方・構成を要約したものです。詳細は各モジュールの docstring（ソース内コメント）および config/*.yaml（存在する場合）を参照してください。問題や追加のドキュメント化が必要なら教えてください。