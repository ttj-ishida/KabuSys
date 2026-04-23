# KabuSys

日本株向け自動売買システム（ライブラリ + 実行スクリプト群）の README。  
このプロジェクトは戦略・ポートフォリオ構築、実行エンジン、監視、Research/AI 補助処理を含むモジュール群で構成されています。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- 株式のファクター算出・特徴量探索（research）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- 発注・発注管理・リスク管理を含む Execution Engine（本番 / ペーパートレード対応）
- システム稼働・注文・リスクの監視と Kill Switch（監視モジュール）
- ニュースを LLM でスコアリングする AI 補助（OpenAI を利用）
- Paper Trading の検証レポート生成ツール

設計方針の一部：
- 本番 DB / ペーパートレード DB を分離（KABUSYS_ENV により切替）
- DuckDB を分析用途に使用、SQLite を監視・ログ用途に使用
- OpenAI 呼び出しはフェイルセーフ（失敗時はフォールバックする実装）
- 自動化運用を意識したプロセス優先度設定、ログローテーション、フラグファイルによる停止制御

---

## 主な機能一覧

- 実行（Execution）
  - Engine 起動スクリプト: run_execution.py
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - RiskManager, OrderManager, Reconciler 等の組み立て
- 監視（Monitoring）
  - run_monitoring.py によるポーリング監視ループ（SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine）
  - kill.flag による ExecutionEngine の安全停止
  - 監視ログ永続化（SQLite）: system_status, trade_logs, risk_logs, positions, dashboard
- ポートフォリオ構築（portfolio）
  - 銘柄選定（スコア降順）、等重・スコア重み付け
  - セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元株丸め）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を用いた SQL 実装）
  - 将来リターン、IC 計算、ファクター統計サマリー
- AI
  - ニュース記事のセンチメントを OpenAI でスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector）
- ツール
  - 環境設定ウィザード: config_setup.py（.env の対話的作成）
  - 設定検証 CLI: validate_config.py（.env / config/*.yaml の検証）
  - Paper Trading 検証レポート生成: tools/paper_verification_report.py

---

## セットアップ手順（簡易）

1. リポジトリをクローン（あるいはソースを配置）
   - 例: git clone <repo>

2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 追加で必要に応じて: pip install PyYAML
   - ※実プロジェクトでは requirements.txt を用意してください（本コード抜粋には含まれていません）

4. .env を作成
   - 対話ウィザード: python -m kabusys.config_setup
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用データベース、デフォルト data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE 等

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

6. 必要なディレクトリを作成（自動生成される場合もあるが手動で準備しておく）
   - mkdir -p data logs

---

## 使い方（起動コマンド・主要スクリプト）

- 監視ループを起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path（monitoring.db）を使用（KABUSYS_ENV に依らず本番 sqlite_path を参照）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - 実行開始前に data/stop_requested.flag が存在すると起動を抑止します

- 環境の対話的設定
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（SQLite を読み取り）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI / Research 機能（ライブラリ関数として使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, target_date) 等

ログ設定は共通ユーティリティで行われ、logs/<app_name>.log に日次ローテートで出力されます（デフォルト 30 日保持）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ保存先ディレクトリ、デフォルト logs）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒）
- PAPER_FILL_MODE（instant|partial|never|reject、paper_trading 動作）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

※ 詳細は `kabusys.config.Settings` を参照してください。

---

## ディレクトリ構成（抜粋）

（ソースツリーは src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py        — 対話式 .env ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py     — 共通ログ設定
    - process_priority.py  — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層 + MonitoringDB クラス
    - system_monitor.py    — システム状態 / データ鮮度監視
    - trade_monitor.py     — （注文監視ロジック）※抜粋には一部のみ
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 制御
    - monitoring_engine.py — 監視エンジン（複数モニタ連携）
    - alert_manager.py     — アラート送信管理（参照あり）
  - execution/
    - execution_engine.py  — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py          — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py   — 市場レジーム判定（ETF MA + マクロ）
  - tools/
    - paper_verification_report.py

データ・ログ格納先（デフォルト）
- data/monitoring.db       — 監視ログ（SQLite）
- data/paper_trading.db   — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading）
- data/kabusys.duckdb     — DuckDB（分析用）
- logs/<app_name>.log     — ログファイル

---

## 運用上の注意 / 補足

- ペーパートレードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を使う処理（news_nlp, regime_detector）は API キーが必要です。失敗時は安全側のフォールバックを行いますが、適切なキーとコール制御（レート制限）を設定してください。
- kill.flag / stop_requested.flag / execution.pid などのフラグファイルでプロセス制御を行います。運用時はこれらの存在／権限に注意してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。
- SQLite / DuckDB のパスは Settings を通じて環境変数で上書き可能です。運用環境に合わせて .env を準備してください。
- config/*.yaml のテンプレート生成や詳細設定はリポジトリ付属のスクリプト / ドキュメントに従ってください（抜粋では省略されています）。

---

必要であれば、README に以下を追記できます：
- 具体的な .env のテンプレート（.env.example）
- サービス化（systemd / supervisor）のサンプルユニット
- 実行フロー図（Engine と Monitor の相互作用）
- 主要な設定項目の細かな説明（risk manager の閾値や execution の制約等）

追記希望があれば対象項目を教えてください。