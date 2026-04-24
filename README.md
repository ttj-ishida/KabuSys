README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine（発注エンジン）と監視プロセス（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、サイズ決定、セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI 統合（ニュースのセンチメント評価、レジーム判定） — OpenAI API を利用
- 監視・ログ蓄積用の SQLite 層・ユーティリティ
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主要コンポーネントの目的
- run_execution.py: ExecutionEngine 起動スクリプト（本番 / ペーパー切替対応）
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
- config_setup.py: .env 対話式ウィザード（初期設定）
- validate_config.py: 起動前設定検証 CLI
- tools/paper_verification_report.py: ペーパートレード実行履歴の検証レポート生成
- portfolio/*.py: ポートフォリオ構築の純粋関数群（候補選定・重み・サイズ）
- research/*.py: ファクター計算・特徴量解析
- ai/*.py: OpenAI を使ったニュース NLP / レジーム判定
- monitoring/*: 監視ロジック、Kill Switch、監視 DB（SQLite）
- utils/*: ログ設定、プロセス優先度などのユーティリティ

主な機能一覧
-------------
- Execution:
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - execution.pid に PID を書き、data/stop_requested.flag による外部停止をサポート
- Monitoring:
  - システム状態（CPU/Mem/Disk）、プロセス生存確認、データ鮮度チェック
  - 注文ログ・リスクログ・ポジション・ダッシュボードを SQLite に永続化
  - Kill Switch（ドローダウン等で data/kill.flag を書き、Execution を停止）
  - 通知のための AlertManager 拡張ポイント（LINE 等）
- Portfolio:
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算
  - セクター制限適用、レジーム乗数
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI:
  - ニュース記事を LLM（gpt-4o-mini 想定）で評価し ai_scores に保存
  - ETF（1321）とマクロ記事を組み合わせた市場レジーム判定
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を実装
- 開発ツール:
  - .env ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.9+ を想定（実際の最小バージョンは環境により調整してください）
- システムに sqlite3 は標準で含まれます
- 必要なサードパーティーライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（validate_config の YAML 検証を行う場合、任意）

1) 仮想環境（任意）
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

2) 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

3) データディレクトリ作成
   mkdir -p data logs

4) .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - または .env を手動作成してください。必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - OPENAI_API_KEY（AI 機能を使う場合）

5) 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - 警告も厳密に扱う場合は --strict を付与

6) DB 初期化
   - 起動スクリプト（run_monitoring/run_execution）が内部で必要テーブル作成を行います。
   - ペーパートレード DB を使う場合: data/paper_trading.db が使用されます（Settings.paper_sqlite_path）。

使い方
------
起動スクリプト
- ExecutionEngine（発注エンジン）起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag を立てる（data/stop_requested.flag を作成）か ExecutionEngine 側 API を呼んで停止させます。

- Monitoring 起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを残します。

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB パスは data/paper_trading.db。--db で別指定可。

環境変数・重要な設定
- KABUSYS_ENV: execution のモード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI を使用する AI モジュールで必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログレベル・ログ保存先
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）

運用上の注意
- 本番環境（KABUSYS_ENV=live）の場合は .env 内の設定を十分に確認してください（validate_config は警告を出します）。
- Kill Switch: RiskMonitor がトリガー条件を満たした際に data/kill.flag を書き、Execution に停止シグナルを送る設計です。KILL_FLAG_CLEAR_ON_START=1 に注意（本番では 0 推奨）。
- OpenAI API を利用する機能は料金発生・レート制限の影響を受けます。API キー管理と利用量に注意してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみとなります（ログ設定は kabusys.utils.logging_setup.setup_logging）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースルート src/kabusys 以下の主要ファイル・モジュールの抜粋です（全体構成）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定取得 Utilities
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - execution/               — 発注エンジン関連（OrderManager 等、省略）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite のテーブル管理 / 永続化 API
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留等の監視（省略）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — 各 Monitor の統合ポーリング
    - alert_manager.py        — 通知送信ロジック（拡張ポイント）

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
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（console + 日次ローテート）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

サンプルワークフロー
------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. 監視プロセスを起動（推奨：先に監視を起動してから実行エンジンを起動）
   - python -m kabusys.run_monitoring
4. Execution を起動
   - python -m kabusys.run_execution
5. ペーパートレード検証
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

トラブルシューティング / よくある質問
-------------------------------------
- 「必須環境変数が未設定」と出る:
  .env を正しく配置 / 設定してください。python -m kabusys.config_setup を推奨。
- OpenAI API が動かない:
  OPENAI_API_KEY を設定し、ネットワーク接続・料金枠を確認してください。
- ログファイルが作成されない:
  LOG_DIR の権限やディスク容量を確認してください。失敗時はコンソール出力にフォールバックします。
- Execution が停止する（Kill Switch）:
  data/kill.flag に理由が書かれます。内容を確認後、必要なら KillSwitch.clear()（実装呼び出し）またはファイル削除で解除してください。但し本番では慎重に対応してください。

開発者向け補足
--------------
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト向け）。
- Settings クラスは .env / 環境変数から設定を集約します。Settings.is_paper / is_live の判定を利用してください。
- DuckDB はリサーチ用途での大量データ解析に使う想定です。prices_daily / raw_financials 等のテーブルを参照します。
- テスト時は AI API 呼び出し関数（_call_openai_api 等）をモックして動作確認してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）
- ライセンス表記は本リポジトリのルートに従ってください（README に明示されていない場合は運用方針に従うこと）。

最後に
------
この README はコードを踏まえた要点の抜粋です。詳細な実装や拡張（Broker 実装、Strategy モジュール、AlertManager の実装など）は各モジュールの docstring / 関数説明を参照してください。必要であれば README に含めるサンプル .env テンプレートや起動スクリプトのシステムd/サービス定義例も追加できます — 希望があれば教えてください。