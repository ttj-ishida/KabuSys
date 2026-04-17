# KabuSys

日本株自動売買システム（簡易ドキュメント）

このリポジトリは、株価データ基盤（DuckDB）を用いたリサーチ・ファクター計算、ポートフォリオ構築、注文実行エンジン、監視・アラート機構、および AI を使ったニュースセンチメント/レジーム判定を含む自動売買システムのコア実装を提供します。

主な設計方針
- 本番データベース（SQLite / DuckDB）は明示的に分離可能（paper_trading モードなど）。
- 時刻参照におけるルックアヘッドバイアスの回避を考慮（多くのモジュールで date/time を引数で渡す設計）。
- 外部 API 呼び出し（OpenAI など）は安全にリトライし、フォールバックを持つ設計。
- 監視・アラート・Kill Switch による自動停止メカニズムを備える。

---

特徴一覧（主な機能）
- 実行エンジン（ExecutionEngine）: Broker クライアントを通じた発注・注文管理（paper_trading モードではモックブローカーを使用）。
- 監視サブシステム:
  - SystemMonitor: プロセス状態・CPU/メモリ/ディスク監視、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション数上限の検出、ダッシュボード更新
  - MonitoringEngine / kill switch / AlertManager: ポーリングループ、LINE通知、Kill Switch（data/kill.flag）
- ポートフォリオ構築モジュール:
  - 候補選定、等配分/スコア配分、セクターキャップ、レジーム乗数、単元丸め・サイズ計算
- リサーチ・ファクター計算:
  - Momentum / Volatility / Value 等を DuckDB 上で計算する関数群
  - 将来リターン、IC 計算、ファクター統計サマリ
- AI モジュール:
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ保存）
  - regime_detector: ETF(ma200) とマクロニュース（LLM）を合成して市場レジーム判定
- 運用ツール:
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

セットアップ手順（開発 / 運用用の最小ガイド）

前提
- Python 3.9+（typing の一部表記に依存）
- SQLite は標準ライブラリに含まれます
- DuckDB, psutil, openai, requests などが必要

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai requests
   - 任意: PyYAML（config YAML 検証を行いたい場合）: pip install pyyaml

   （本リポジトリに requirements.txt は含まれていないため必要パッケージを手動でインストールしてください）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成してルートに置く
   - 必須環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 重要な設定例（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
     - KILL_FLAG_CLEAR_ON_START (0 / 1)

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1)

5. 初回 DB 作成
   - 実行スクリプトは起動時に必要なテーブル（監視テーブルなど）を自動作成します（monitoring_db.init_monitoring_db を通じて）。

---

使い方（代表的なコマンド）

- 実行エンジン（発注実行）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い MockBrokerClient（実際の発注は行わない）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了。
    - 実行中は data/stop_requested.flag を検知するとエンジンを停止する。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- 監視ポーリング
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを SQLite に格納。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（monitoring 用に本番 DB を想定）。
    - デフォルトの停止フラグは data/stop_requested.flag（run_monitoring/run_execution の両方で参照）。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成/更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も FAIL 扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で指定可）

停止 / Kill Switch
- 手動で監視ループ／エンジンを止める:
  - data/stop_requested.flag を作成（例: touch data/stop_requested.flag）
  - 監視プロセス / 実行エンジンは起動ループでこのファイルを見て終了します
- Kill Switch（監視から自動で書かれる）:
  - 監視モジュールが条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止を促します
  - Kill Switch を解除するにはファイルを削除するか（手動で） KillSwitch.clear() を呼ぶ設計

環境変数（抜粋・デフォルト）
- KABUSYS_ENV=development | paper_trading | live  （default: development）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0 | 1
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒、run_monitoring 用）
- PAPER_FILL_MODE (instant | partial | never | reject) — paper trading の約定挙動
- OPENAI_API_KEY（AI モジュールで必要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

---

ディレクトリ構成（主なファイル/モジュール）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - execution/              — 実行エンジン関連（BrokerFactory, Engine, OrderManager 等）
    - (order_manager.py, execution_engine.py, order_repository.py, reconciler.py, risk_manager.py, ...)
  - monitoring/
    - monitoring_db.py      — SQLite に対する永続化ヘルパ（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — OpenAI を用いたニューススコアリング
    - regime_detector.py     — レジーム判定（ma200 + macro sentiment）
    - __init__.py
  - monitoring/monitoring_db.py
  - tools/
    - paper_verification_report.py

注: 実際のブローカー接続や注文ロジックは execution パッケージ内にあり、環境によっては追加の設定（kabuステーション API 等）が必要です。

---

運用上の注意
- .env は絶対に Git に含めないでください（config_setup.py のヘッダにも警告あり）。
- 本番（KABUSYS_ENV=live）での起動前には必ず python -m kabusys.validate_config を実行し設定を確認してください。
- OpenAI API キーやブローカーの資格情報は適切に管理してください（CI/CD シークレット等を使用）。
- 監視・Kill Switch による自動停止を有効にする場合、KILL_FLAG_CLEAR_ON_START の設定には注意してください（本番では 0 が推奨）。

---

トラブルシュート（簡易）
- 監視がデータベースに書き込まれない:
  - 設定された SQLITE_PATH / DUCKDB_PATH の親ディレクトリが存在するか確認してください。validate_config が警告を出します。
- 実行エンジンがすぐ停止する:
  - data/stop_requested.flag が存在していないか確認。または data/kill.flag が書かれていないか確認してください。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY が設定されているか確認。API のレート制限や一時エラーはリトライロジックにより緩和されますが、キーやネットワークを確認してください。

---

貢献 / 開発
- コードの追加や変更は src/kabusys 以下の対応するモジュールに行い、ユニットテストを追加してください（本リポジトリにテストスイートは含まれていませんが、関数分離がされているためテストしやすい設計です）。
- データベーススキーマの変更は monitoring_db.init_monitoring_db にマイグレーションロジックを追加してください（既存コードでは冪等性と簡易マイグレーションが実装されています）。

---

ライセンス・バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（なければ運用前に決めてください）。

---

この README はコードベースの主要点を抜粋した概要です。詳細な仕様や設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を参照できる場合は合わせて確認してください。必要であれば各モジュールの使い方や API サンプルを追記します。