KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買／研究／監視コンポーネント群をまとめたパッケージです。  
主に以下の役割を持つモジュールを含みます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文管理
- 監視（Monitoring）: システム稼働・注文状況・リスク監視、Kill Switch
- ポートフォリオ構築（Portfolio）: 銘柄選定・配分・ポジションサイズ計算
- 研究（Research）: ファクター計算・特徴量探索
- AI モジュール（AI）: ニュース NLP（OpenAI）によるセンチメント、レジーム判定
- ユーティリティ: 設定管理、ログ設定、プロセス優先度など
- ツール: ペーパートレード検証レポート等

以下は開発者／運用者向けの README（日本語）です。

機能一覧
--------

主な機能（抜粋）:

- Execution
  - 実発注／ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - 注文管理・リスク管理・リコンシリエーション（order_manager, risk_manager, reconciler）
  - paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 発注ログの整合性・滞留注文・約定異常検出（ファイル trade_logs 等）
  - RiskMonitor: ドローダウン監視、ポジション数上限監視、ダッシュボード更新
  - KillSwitch: 条件により data/kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine: 監視コンポーネントを束ねてポーリング実行

- Portfolio
  - 銘柄選定（スコア降順）、等金額／スコア加重配分、リスクベースのポジションサイズ算出
  - セクター集中制限やレジーム乗数の適用

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ

- AI
  - news_nlp: raw_news から銘柄別センチメントを OpenAI で算出し ai_scores に格納
  - regime_detector: ETF（1321）MA200 乖離＋マクロ NLP を使って market_regime を判定

- ツール
  - config_setup: 対話式で .env を生成
  - validate_config: .env / config/*.yaml 等の起動前チェック
  - tools.paper_verification_report: ペーパートレードの検証レポート作成

セットアップ手順
---------------

前提
- Python 3.10+（ソース内の型注釈から推奨）
- SQLite（組み込み）、DuckDB、ネットワークアクセス（OpenAI API 使用時）
- 推奨: 仮想環境 (venv / virtualenv / conda)

1. リポジトリをクローンする
   - git clone ... && cd <repo>

2. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows PowerShell: .\.venv\Scripts\Activate.ps1)

3. 依存パッケージをインストール
   - 必須ライブラリ（例）
     - duckdb
     - psutil
     - openai
     - pyyaml (validate_config で YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （requirements.txt が存在する場合は pip install -r requirements.txt）

4. 初期設定（.env）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これにより .env を生成または更新できます（.env は絶対に Git へコミットしないでください）
   - 手動で環境変数を設定することも可能（.env / 環境変数）

5. 設定検証（起動前）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db に書き込む
  - live: 本番動作（注意して設定してください）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の Fill 動作）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 実行開始時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

使い方
-----

起動スクリプト（モジュール実行形式）:

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings によらず本番 sqlite_path を使用して監視 DB を初期化します
  - 停止: プロジェクトルート/data/stop_requested.flag が作成されるとループは終了します

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と分離）
  - ExecutionEngine は data/execution.pid を PID ファイルとして扱います
  - 停止: data/stop_requested.flag により安全停止をトリガー可能

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を指定すると警告も失敗扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

プログラム的な利用
- パッケージとしてインポートし、各モジュールの関数を呼び出して利用できます。
  - 例: from kabusys.ai.news_nlp import score_news
  - DuckDB 接続（duckdb.connect(...)）を渡して使用する関数が多くあります。

運用上の注意
- Kill Switch:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込みます（ExecutionEngine はこれを検知して停止します）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に自動で kill.flag を消すと危険）。
- ログ:
  - ログは kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。デフォルトは logs/ ディレクトリに日次ローテーションで保存されます。
- プロセス優先度:
  - run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent（冪等）にテーブルと必要な列を作成・追加します。

ディレクトリ構成
----------------

(ルート直下の src/kabusys を基準に抜粋)

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py      — .env を対話式に生成するウィザード
  - validate_config.py   — 起動前チェック CLI
  - run_execution.py     — ExecutionEngine 起動スクリプト
  - run_monitoring.py    — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py        — ニュース NLP（OpenAI）による銘柄別センチメント
    - regime_detector.py — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py   — 監視用 SQLite 永続化層
    - system_monitor.py  — システム状態・データ鮮度監視
    - trade_monitor.py   — (発注ログ監視等)
    - risk_monitor.py    — ドローダウン・ポジション上限監視
    - kill_switch.py     — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py   — （アラート送信の抽象化）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用するデータ / DB / フラグ類を格納する想定のディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid など

追加ドキュメント / 補足
--------------------

- コードには各モジュールごとに詳細な docstring と設計方針が含まれています。個別の実装意図やパラメータの意味は各 .py の docstring を参照してください。
- OpenAI を使用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とし、API 呼び出し失敗時はフェイルセーフ（スコア 0.0 等）で継続する実装になっていますが、本番運用では API コスト・レイテンシ・利用制限に注意してください。
- DuckDB を利用したファクター計算・研究モジュールは SQL を多用しています。prices_daily / raw_financials 等のテーブルが前提です。

よくある運用コマンド例
---------------------

- 設定ウィザード → 検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- モニタリング起動（バックグラウンドで実行する場合はプロセスマネージャを使用）:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパー検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 貢献
----------------
- バグ報告・改善提案は issue を立ててください。Pull Request は歓迎します。
- 重要な設計上の前提や DB スキーマ変更は事前に議論してください（互換性に影響します）。

以上が本リポジトリの概要と基本的な使い方です。個別機能の詳細を知りたい箇所（例えば ExecutionEngine の起動パラメータ、RiskConfig の調整方法など）があれば教えてください。具体例や起動スクリプトの実行オプションを追記します。