# KabuSys

日本株向け自動売買システムの一部コードベースです。本 README は提供されたソースコードに基づく概観、セットアップ、よく使うコマンド、ディレクトリ構成を日本語でまとめたものです。

注意: このリポジトリは実取引（本番）や OpenAI API 等を利用する機能を含みます。実行前に .env の設定やテスト環境での確認を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な機能は次のとおりです。

- データ処理 / Research: DuckDB 上でファクター計算（モメンタム、ボラティリティ、バリュー等）や特徴量解析を行う。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制限・レジーム調整。
- Execution: 発注エンジン（本番/ペーパートレード切替可）、注文管理、リスク管理、約定ログ保存。
- Monitoring: プロセス・システムリソース・注文流量・ドローダウン等の監視、LINE を用いたアラート通知、Kill Switch（停止フラグ）機能。
- AI モジュール: OpenAI を用いたニュースのセンチメント評価（ニュース NLP）、市場レジーム判定（LLM＋ETF MA）。
- ツール: ペーパートレードの検証レポート生成スクリプト等。

主要な設計方針として、「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避（日時参照の制約）」「フェイルセーフ（API 失敗時のフォールバック）」等が採用されています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト: src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を使用
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report
- AI:
  - kabusys.ai.news_nlp.score_news — ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - kabusys.ai.regime_detector.score_regime — レジーム判定（ETF MA + マクロニュース）
- Portfolio:
  - 選定（select_candidates）、重み（等重・スコア重み）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine、DB 永続化層（monitoring_db.py）
  - AlertManager — LINE Push による通知（クールダウン管理）

---

## セットアップ手順（ローカル）

1. Python 環境作成（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil requests openai
   - optional: PyYAML（config 検証で YAML パースを行いたい場合）: pip install PyYAML

   ※ 実行環境によっては psutil のインストールにビルドツールや管理者権限が必要になる場合があります。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` をプロジェクトルートに作成（.env.example を参照してください）。

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知を有効にする場合）
   - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject）
   - LOG_LEVEL（DEBUG/INFO/...）
   - KILL_FLAG_CLEAR_ON_START（0/1）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合は --strict を付与

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine の起動
  - 通常（設定の env に従う）:
    - python -m kabusys.run_execution
  - ペーパートレードで起動（環境変数を上書き）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、MockBrokerClient が使用され、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

  実行時のポイント:
  - プロセス優先度を "high" に設定する処理を行います（psutil を使用）。
  - data/execution.pid に PID を書き、停止は data/stop_requested.flag または Kill Switch を用いる形です。
  - 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合 kill.flag をクリアする動作を行う運用設定があります（注意して設定してください）。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は実行環境に関わらず（KABUSYS_ENV に関係なく）本番 sqlite_path（SQLITE_PATH）を使用します。

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を利用、あるいは環境変数 PAPER_TRADING_SQLITE_PATH を参照します。

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定する必要があります。
  - 関数単位で使う設計（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）

---

## 運用上のファイル・フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution のループで存在をチェックして終了処理を行うための停止フラグ。
- data/kill.flag
  - KillSwitch によって書き込まれ、ExecutionEngine に停止指示を出すためのフラグ。実運用では慎重に扱うこと（KILL_FLAG_CLEAR_ON_START に注意）。
- data/execution.pid
  - ExecutionEngine の PID を記録するファイル。SystemMonitor はこの PID の存在とプロセスの生存確認を行います。

---

## 主要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（実行モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API 認証（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード約定挙動）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定
- LOG_LEVEL: ログレベル（INFO など）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## 開発・拡張のポイント

- DuckDB を用いた分析系（research）関数群は接続を受け取り SQL + Python で完結する設計です。prices_daily / raw_financials / raw_news 等のテーブルに依存します。
- AI 呼び出しは OpenAI の JSON mode を利用する想定で、レスポンスのバリデーションやリトライロジックが組み込まれています。
- MonitoringDB のスキーマは init_monitoring_db() で冪等に作成・マイグレーションします。
- Process priority / CPU affinity 設定は psutil を用いており、権限不足で失敗した場合はログに記録してスキップします。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイルとモジュール（提供コードに基づく抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / .env の読み込み・Settings
    - config_setup.py               — 対話式 .env ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor 起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py            — SQLite 監視 DB 層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/                     — 発注エンジン周り（参照のみ、実装ファイル群あり）
      - (OrderRepository, ExecutionEngine 等)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
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

（リポジトリ内に data/、config/ 等の補助ディレクトリが存在する想定です）

---

## よくある注意点 / トラブルシューティング

- psutil の一部機能（nice, cpu_affinity）はプラットフォームや権限に依存します。権限不足で警告になることがありますが、システムは継続動作します。
- monitoring は「監視用の DB（SQLITE_PATH）」を直接操作します。監視データは本番 DB を使う設計になっているため、テスト時は SQLite パスを分離してください。
- OpenAI 呼び出しはレート制限や一時的なネットワーク障害を考慮してリトライロジックがありますが、API キーを未設定だと例外になります。テスト時はモック化を推奨します。
- .env は絶対に機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。

---

もし README に追加したい情報（サンプル .env.example の内容、systemd ユニット例、Docker 化手順、CI 設定など）があれば教えてください。それらに合わせて追記・整形します。