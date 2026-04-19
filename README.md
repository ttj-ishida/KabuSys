# KabuSys

日本株向け自動売買システムのリポジトリ（簡易 README）

この README は、提供されたコードベースに基づいて作成しています。運用・開発時のセットアップと基本的な使い方、各機能の概要を日本語でまとめています。

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムのコアライブラリ群です。主な目的は以下のとおりです。

- 売買シグナル生成・ポートフォリオ構築（research / portfolio）
- 発注エンジン（ExecutionEngine）とオーダー管理（execution）
- 実行ログ・監視ログの永続化（SQLite / DuckDB）
- システム監視・アラート・Kill Switch（monitoring）
- Paper Trading 用の検証ツール
- ニュース NLP / レジーム判定などの AI 補助モジュール

設計方針として、DB（DuckDB/SQLite）接続を渡して計算する純粋関数群、外部 API 呼び出しは分離、実運用での安全性（Kill Switch、フェイルセーフ、ログ）を重視しています。

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）と対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン関連
  - ExecutionEngine 起動スクリプト（run_execution）
  - Paper Trading 対応（KABUSYS_ENV=paper_trading で mock broker を使用し DB を分離）
- 監視 / 運用
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプト（ポーリング監視ループ）
  - Kill Switch（data/kill.flag）による停止シグナル発行
  - ログ出力ユーティリティ（TimedRotatingFileHandler を含む統一ロギング）
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ決定、セクター制約、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI 補助
  - ニュースを LLM（OpenAI）でスコア化して ai_scores に書き込む（news_nlp）
  - マクロ + ETF 指標を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境
   - Python 3.9+ を推奨（ソースは型注釈に Python 3.9 以上を想定）

2. 必須パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML を検証する場合）
   - （SQLite は標準ライブラリに含まれます）

   例（pip）:
   ```
   pip install duckdb psutil openai pyyaml
   ```

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

3. .env の作成
   - 対話型ウィザードで .env を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - オプション・デフォルト:
     - KABUSYS_ENV=development|paper_trading|live（デフォルト: development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO

   - .env は自動的にプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ作成
   - デフォルトでは `data/` と `logs/` を使用します。必要に応じて作成してください（スクリプトは自動生成も行いますが権限等に注意）。

---

## 使い方

### 基本コマンド

- 実行エンジンを起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` を使用します。
  - 起動前に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中は pid ファイル（デフォルト data/execution.pid）を生成します。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず）。
  - 停止は `data/stop_requested.flag` を作成することでループを抜けます。

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

### ロギング
- 共通の logging セットアップ関数があり、各スクリプトは以下を呼び出しています:
  - setup_logging(app_name="execution" / "monitoring")
- ログディレクトリは `LOG_DIR` 環境変数または `logs/`（デフォルト）を使用し、日次ローテーション（30日保持）。

### Kill Switch / 停止操作
- Kill Switch のトリガーで `data/kill.flag` に理由を書き込むと、ExecutionEngine に停止シグナルを送る設計です。
- 手動停止用フラグ: `data/stop_requested.flag` を作ると run_monitoring/run_execution のループが検知して終了します。
- ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に kill.flag をクリアする挙動になります（本番では 0 を推奨）。

### OpenAI（AI モジュール）
- news_nlp と regime_detector は OpenAI API を使用します。環境変数 `OPENAI_API_KEY` を設定するか、関数に api_key を渡してください。
- LLM 呼び出し失敗時はフォールバック（ゼロスコア等）して継続するよう設計されています。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring）ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（default: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default: 60）

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス（デフォルト値・検証ロジック）
- config_setup.py
  - .env を対話式で生成/更新するウィザード
- validate_config.py
  - 起動前設定チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（pid 管理・stop flag 検知・paper_trading 分離）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- utils/
  - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
  - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil ベース）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス存在チェック
  - trade_monitor.py — （存在）取引ログ監視（ファイルに同梱の全体像から推測）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各モニタの統合ポーリング
  - alert_manager.py — （参照）通知管理（LINE 等）
- execution/
  - execution_engine.py — ExecutionEngine 本体（起動・セッション管理）
  - broker_factory.py — Broker クライアント生成（実口座 / mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周りのコンポーネント群
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数決定 / キャップ / 単元丸め
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- research/
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / サマリ
- ai/
  - news_nlp.py — ニュースを LLM でスコア化し ai_scores に書き込む
  - regime_detector.py — ETF MA + マクロスコアでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- その他:
  - data/ — データ・DB・フラグファイルが配置される（デフォルト）
  - logs/ — ログ（デフォルト）

---

## データベース（監視用）スキーマ（簡易）
monitoring_db.init_monitoring_db が作成する主なテーブル:
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (単一行 id=1 で集計保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定とシークレット管理に十分注意してください。validate_config は live の場合に追加警告を出します。
- Kill Switch / stop flag を誤って設定すると ExecutionEngine が停止します。特に `KILL_FLAG_CLEAR_ON_START` の取り扱いに注意（本番は 0 推奨）。
- OpenAI を利用する機能は API コストとレイテンシを伴います。API キーの管理と呼び出し回数の制御を行ってください。
- ログディレクトリ作成や DB ファイル作成時の権限に注意してください。ログディレクトリ作成に失敗した場合はコンソールログのみになります。

---

必要に応じて README に追記します。例えば:
- requirements.txt / pyproject.toml の推奨内容
- systemd / supervisor 用のサービス定義例
- 詳細な ExecutionEngine の挙動・API ドキュメント
があればそれに基づく具体的な運用手順を追加できます。必要であれば教えてください。