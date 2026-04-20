# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。

本 README はソースツリー (src/kabusys 以下) の主要コンポーネントと使い方をまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株の自動売買を想定した以下の主要機能を持つシステムです。

- Execution Engine: ブローカークライアント経由で発注・注文管理を行う実行エンジン（paper_trading モードあり）。
- Monitoring: システム稼働状況／データ鮮度／注文状況／リスクをポーリングしてログ記録・アラート・Kill Switch を評価。
- Portfolio Construction: 候補選定、ウェイト計算、ポジションサイズ計算、セクター上限・レジーム補正などの純粋関数群。
- Research: DuckDB 経由でファクター計算や特徴量探索を行うモジュール群（モメンタム、ボラティリティ、バリュー等）。
- AI ユーティリティ: ニュースの NLP スコアリングや市場レジーム判定（OpenAI を利用、オプション）。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード・検証ツールなど。

設計の要点：
- 設定は .env と環境変数で管理（config モジュール）。
- DuckDB は分析・リサーチ用、SQLite は監視・発注ログ用（paper_trading 用に専用 DB を分離可能）。
- 起動スクリプトはパッケージ内のモジュールとして提供（python -m kabusys.<module>）。

---

## 機能一覧

- 実行関連
  - ExecutionEngine の起動スクリプト（run_execution.py）。
  - ブローカークライアントを環境に応じて切替（本番 / ペーパートレード）。
  - 発注履歴 / trade_logs / positions の永続化（SQLite）。

- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）。
  - system_status / trade_logs / risk_logs / dashboard テーブルを持つ監視 DB（SQLite）。
  - Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine の停止を誘発。
  - stop フラグ（data/stop_requested.flag）によるループ停止。

- ポートフォリオ構築
  - 候補選定（スコア降順）、等重・スコア重み付け。
  - セクター分散制限、レジームに応じた乗数。
  - 単元（lot）丸め・最大ポジション比率・利用可能資金に基づく株数算出。

- リサーチ
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー。

- AI（オプション）
  - OpenAI を使ったニュースセンチメントスコア（news_nlp）。
  - マクロニュース + ETF MA を用いた market_regime の算出（regime_detector）。

- 開発支援
  - .env 作成ウィザード（config_setup.py）。
  - 起動前チェック（validate_config.py）。
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report.py）。

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+ が推奨（コードに 3.10 の構文を使用）。
- git でプロジェクトルートをサポート（.env 自動読み込みに使用）。

1. レポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 最低依存（例）:
     - duckdb
     - psutil
     - openai (AI機能を使う場合)
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使ってください）

3. .env ファイルを作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY （AI 機能を使う場合）
   - 重要: .env は Git にコミットしないでください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルト DB 等は `data/` に作成されます。必要に応じて手動で作成してください（logging や PID/flag 用にも使用）。
   - デフォルト：
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

6. ログディレクトリ
   - デフォルト: logs/
   - 環境変数 LOG_DIR で変更可能。

---

## 実行・使い方

以下は主要な起動手順です。パッケージとして起動可能（python -m kabusys.<module>）。

1. Execution Engine（注文実行）
   - 起動:
     python -m kabusys.run_execution
   - 挙動:
     - Settings.KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、ペーパー専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録。
     - 実行中は data/execution.pid に PID を書く（設定による）。
     - data/stop_requested.flag が存在すると起動を中止または実行中に停止します。

2. Monitoring（監視ループ）
   - 起動:
     python -m kabusys.run_monitoring
   - 挙動:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV に依らず production の sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
     - 停止フラグ data/stop_requested.flag が検出されるとループを終了します。

3. 設定ウィザード・検証
   - .env 作成ウィザード:
     python -m kabusys.config_setup
   - 構成検証:
     python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート
   - レポート生成:
     python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH。

5. Kill Switch / 停止フラグ
   - KillSwitch は監視ロジックにより条件が満たされると `data/kill.flag` を書き込みます（ExecutionEngine はこれを検知して安全停止する設計）。
   - 手動停止用のフラグ:
     - data/stop_requested.flag：run_monitoring / run_execution のポーリングループ（および起動判定）を止めるために用いる。
   - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアする挙動になるので、本番では `0` を推奨。

---

## 環境変数（主要）

- 決定的なもの:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - OPENAI_API_KEY（AI 機能使用時）
- DB / ファイルパス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- ロギング / 実行:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の MockBroker の挙動: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアする: "1" で有効）

各変数は .env または環境に設定可能。config_setup ウィザードで初期 .env を作成できます。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前の設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py          — OpenAI を用いたニュースセンチメント
    - regime_detector.py   — レジーム判定（ma200 + LLM）
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ + DB 操作ラッパー
    - system_monitor.py
    - trade_monitor.py      — （ソース省略: 監視ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py      — （アラート送信ラッパー: LINE など）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py     — 統一ロギング設定
    - process_priority.py   — プロセス優先度 / CPU affinity

- データディレクトリ（実行時に利用）
  - data/
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper_trading 用)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/
    - execution.log
    - monitoring.log
    - ... 日次ローテート

※上記はソース内のコメントやデフォルト値を基に抜粋しています。完全なファイル一覧はリポジトリツリーを参照してください。

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では env の設定を入念に確認してください。validate_config で警告が出ます。
- Kill Switch 機能は本番保護用の重要な仕組みです。KILL_FLAG_CLEAR_ON_START を 1 にすることは本番では危険です（デフォルトは 0 推奨）。
- Monitoring モジュールは監視 DB（sqlite）に書き込むため、Monitoring は常に production の sqlite_path を参照する点に注意してください（run_monitoring の実装ポリシー）。
- OpenAI を利用する際は API キーの管理に注意し、使用料とレイテンシを考慮してください。AI 機能は障害時にフェイルセーフ（0.0 相当）にフォールバックする実装になっていますが、鍵の漏洩は重大です。
- ロギングは統一的に設定され、デフォルトで日次ローテート・30 日保存が設定されています。LOG_DIR を適切に設定し、ディスク容量に注意してください。
- process_priority の設定は psutil に依存し、権限不足により設定できない場合は警告が出力されます。

---

## 開発・拡張のヒント

- DuckDB 接続を注入して research / ai モジュールをオフラインでテストできます（DB に prices_daily / raw_news 等のテーブルを用意）。
- MonitoringEngine.run_once() はテスト用に個別モニタを 1 回だけ実行するための便利な API です（ユニットテストでの利用を想定）。
- news_nlp と regime_detector は OpenAI 呼び出しロジックを内部で分離しており、ユニットテストでは _call_openai_api をモックしてテストできます。

---

以上が本パッケージの概要と基本的な使い方です。具体的なコードや追加の運用手順は各モジュールの docstring / コメントを参照してください。必要であれば README の補足（デプロイ手順、systemd ユニット例、Dockerfile 例など）も作成しますのでリクエストしてください。