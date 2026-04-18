# KabuSys — 日本株自動売買システム

本リポジトリは日本株向けの自動売買フレームワーク「KabuSys」の実装です。  
取引実行（ExecutionEngine）、監視（Monitoring）、リサーチ（Research）、ポートフォリオ構築、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような責務を分離して実装された自動売買システムです。

- Execution: 注文生成・発注・注文管理・リスク管理を行う ExecutionEngine（paper_trading モードあり）
- Monitoring: システム状態・注文/約定ログ・リスク監視・Kill Switch（フラグファイルでエンジン停止）
- Research: DuckDB 上の価格・財務データに基づくファクター計算・特徴量分析
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制限・レジーム調整
- AI: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントおよび市場レジーム判定
- Tools: Paper Trading の検証レポート生成等のユーティリティスクリプト
- Utils: ロギング設定・プロセス優先度設定などの共通ユーティリティ

設計上の特徴:
- 本番とペーパートレードは DB レイヤーで明確に分離（paper_trading 用 SQLite）
- DuckDB を分析用データベースとして利用
- 環境変数 / .env による設定管理と対話式ウィザード、設定検証ツールを提供
- OpenAI API 呼び出しはリトライやレスポンス検証を実装しフェイルセーフ化

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアント（本番）または MockBrokerClient（ペーパートレード）を使用可能
  - リスク管理（max position、utilization、ドローダウン検出等）
  - Order 管理・ログ保存（SQLite）
- Monitoring
  - CPU / メモリ / ディスク監視、プロセス稼働確認
  - trade_logs / risk_logs / dashboard の永続化（SQLite）
  - Kill Switch: 条件により data/kill.flag を書き込んで ExecutionEngine を停止
  - AlertManager 経由でアラート配信（LINE 設定を使用可能）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- Portfolio
  - 候補選定（スコア順）、等金額／スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数（bull/neutral/bear）
- AI
  - ニュース記事を元に銘柄毎センチメントを生成し ai_scores に格納（OpenAI）
  - マクロニュース + ETF MA200 による市場レジーム判定と保存
- Tools
  - Paper Trading 検証レポート生成（稼働率・約定率・レイテンシ評価）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - 必要パッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検査を行う場合）
   - 例: pip install duckdb psutil openai pyyaml

   （本リポジトリに setup.py / pyproject.toml がある場合は `pip install -e .` を利用）

4. 環境変数の設定
   - 推奨手順: 対話式ウィザードを使って .env を生成
     - python -m kabusys.config_setup
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数例:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant | partial | never | reject）
   - .env をプロジェクトルートに配置すると自動読み込み（プロジェクトルートは .git や pyproject.toml により検出）

5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了

6. データディレクトリ
   - デフォルトで DB やログはプロジェクトの data/ や logs/ に配置されます。必要に応じてディレクトリを作成してください。
   - ログは logs/<app_name>.log に日次ローテートで保存されます。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番 or paper_trading）
  - KABUSYS_ENV を設定してから起動
  - python -m kabusys.run_execution
  - 実行時に data/execution.pid に PID を書き込みます。停止は監視プロセス（kill.flag）や stop_requested.flag による制御を利用します。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを永続化します。

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を明示する場合: --db PATH（指定がなければ PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キー（api_key 引数または OPENAI_API_KEY 環境変数）が必要

- 停止制御（手動）
  - 実行ループを停止するにはプロジェクトルートの data/stop_requested.flag を作成（存在を検出して安全に終了）
  - ExecutionEngine に対して強制停止（Kill Switch）を起動するには data/kill.flag を作成（KillSwitch が検出して Execution を停止）
  - KillSwitch は Settings.kill_flag_clear_on_start の設定に基づき起動時に自動クリアされる場合があります（本番では 0 推奨）

---

## 重要な設定項目（抜粋）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading では MockBrokerClient を利用し、データは paper_trading 用の SQLite に記録される（本番 DB と分離）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- DUCKDB_PATH: DuckDB ファイルパス（分析用）
- SQLITE_PATH: 監視 DB（system_status, trade_logs, positions, risk_logs, dashboard）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading モード）
- OPENAI_API_KEY: OpenAI を利用する場合に設定
- LOG_LEVEL, LOG_DIR: ログ出力レベル・保存先

---

## ディレクトリ構成（主要ファイル）

プロジェクトの src/kabusys 以下を中心に説明します（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/                — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ（テーブル作成・アップサート等）
    - system_monitor.py      — CPU/メモリ/プロセス/データ鮮度監視
    - trade_monitor.py       — （trade_monitor 実装ファイル; ここでは抜粋されている想定）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 制御（kill.flag の作成/削除）
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート送信ロジック; LINE 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン, IC, 統計サマリ
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し・バッチ処理・検証）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/                    — デフォルトの DB / フラグファイル / PID ファイル 配置場所（生成される）
  - logs/                    — ログが出力されるディレクトリ（デフォルト）

---

## 運用上の注意 / ベストプラクティス

- 本番環境 (KABUSYS_ENV=live) 設定では LINE チャンネルアクセストークン等の通知設定を必ず確認すること。
- .env ファイルは絶対にリポジトリにコミットしない（config_setup でも注意書きあり）。
- kill.flag の自動クリアは本番では無効（KILL_FLAG_CLEAR_ON_START=0 を推奨）。
- OpenAI API を使用する処理は外部 API 通信に依存するため、API キー管理・コスト管理に注意する。
- データベース（DuckDB / SQLite）はバックアップ・保全を行うこと（特に本番の取引履歴）。
- run_monitoring と run_execution は通常別プロセスで常駐させる（systemd や Supervisor 等のプロセスマネージャーを推奨）。

---

## 参考コマンド一覧（まとめ）

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 必要パッケージインストール（例）
  - pip install duckdb psutil openai pyyaml

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

もし README に追加してほしい具体的な内容（例: systemd ユニットファイルのサンプル、詳しい ExecutionEngine の設定項目一覧、API スキーマや DB スキーマの詳細など）があれば教えてください。必要に応じて追記・整備します。