KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。シグナル生成・ポートフォリオ構築・発注処理（ExecutionEngine）、運用時の監視（Monitoring）および研究用のファクター計算・特徴量解析、AI を使ったニュースセンチメント評価などの機能を含みます。  
設計方針の一部：可能な限りフェイルセーフ（API失敗時はフォールバック）、本番/ペーパーの DB 分離、ルックアヘッドバイアス回避（実行時に日付参照を直接行わない）など。

主な機能
-------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient を用いた paper_trading）
  - リスク管理（RiskManager）、オーダー管理、リコンシリエーション
- Monitoring（監視）
  - システム状態（CPU / メモリ / ディスク）、プロセス生存確認、データ鮮度監視
  - 取引ログ・リスクログの永続化（SQLite）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、Execution を停止）
  - 通知（AlertManager 経由）
- ポートフォリオ構築（純関数実装）
  - 候補選定、等分配・スコア加重、ポジションサイズ算出、セクター上限・レジーム乗数
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算、統計サマリー
- AI モジュール
  - ニュースのセンチメント評価（OpenAI を用いた ai_scores 書き込み）
  - 市場レジーム判定（ETF MA + マクロニュースの LLM 評価）
- ツール
  - 設定ウィザード（.env 生成）: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report
- ユーティリティ
  - 統一ログ設定（logs/*.log、日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
---------------
前提
- Python 3.10 以降（typing の | 記法を利用）
- 必要なパッケージ（主なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - （任意）PyYAML（config/*.yaml のパース検証に使用）

例（仮想環境内で）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発で YAML 検証を使う場合）pip install pyyaml

3. .env を作成
   - 対話的に作る: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（デフォルト INFO）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

使い方
-----
起動スクリプト
- ExecutionEngine を起動（メインの発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすれば MockBrokerClient を使い、ペーパー専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/stop_requested.flag を作成するとエンジンを停止できます。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は常に production（本番）用 sqlite_path を使って監視 DB に記録します。
  - 停止は data/stop_requested.flag を作ることで行えます。

停止 / Kill
- Graceful stop（手動）
  - プロジェクトルートに data/stop_requested.flag ファイルを作成すると、run_execution / run_monitoring のループが終了します。
- Kill Switch（監視からの自動停止）
  - 監視モジュールの条件に合致すると data/kill.flag が書き込まれ、ExecutionEngine がそれを検出して停止する仕組みがあります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

AI 機能
- ニュース NLP / レジーム判定は OpenAI API を使用します。OPENAI_API_KEY を設定してから実行してください。
- API 呼び出しはリトライやフォールバック（失敗時は 0.0 等）を行うため、完全停止ではなく安全に継続する設計です。

ログ
- logs/ ディレクトリに app 単位のログ（例: logs/execution.log、logs/monitoring.log）を日次ローテーションで出力します。
- 環境変数 LOG_DIR で変更可能、LOG_LEVEL でログレベルを制御します。

ツール
- 設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動ロード / Settings クラス
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

サブパッケージ（主要）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
- monitoring/
  - monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_db.py, alert_manager.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- utils/
  - logging_setup.py, process_priority.py
- monitoring scripts / tools
  - tools/paper_verification_report.py

設定ファイル / データ
- .env                   — 環境変数（プロジェクトルート）
- config/*.yaml          — 各種テンプレート（存在しない場合は警告）
- data/
  - monitoring.db (default: data/monitoring.db) — 監視用 SQLite
  - paper_trading.db (default data/paper_trading.db) — paper_trading 用 SQLite
  - kabusys.duckdb (default: data/kabusys.duckdb)
  - execution.pid, stop_requested.flag, kill.flag など制御用ファイル

開発・テストに関する補足
- Settings は .env の自動ロードを行います（プロジェクトルートが .git または pyproject.toml で検出される場合）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring.monitoring_db.init_monitoring_db() は冪等でテーブル作成および簡単なスキーママイグレーションを行います。
- AI への API 呼び出し部分はテスト時に差し替え可能（モジュール内の呼出関数に patch を当てる）。

よくある環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live)
- OPENAI_API_KEY (AI 機能)
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数）

ライセンス / バージョン
---------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）。

最後に
------
この README はコードベースの主要機能・起動手順をまとめたものです。実運用では .env の機密情報管理、ロギング/監視設定、kill switch の取り扱い、本番環境での慎重な設定（KABUSYS_ENV=live の確認）などに十分注意してください。必要であれば各モジュール（ExecutionEngine / Monitoring / AI / Portfolio）の詳細ドキュメントも作成します。