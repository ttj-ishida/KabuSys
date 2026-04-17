# KabuSys

日本株自動売買システムのコア実装リポジトリ（ライブラリ＋実行スクリプト群）。

主に以下を含みます：
- 発注・実行エンジン（ExecutionEngine） — 実口座 / ペーパートレード切替対応
- 監視（Monitoring） — システム状態／注文状態／リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究モジュール（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP / 市場レジーム判定 — OpenAI 使用）
- 管理ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

以下はこのリポジトリの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ（前提・インストール・環境変数）
- 使い方（主要なコマンド例）
- ディレクトリ構成（主要ファイルの説明）
- 補足（DBスキーマ、Kill Switch 等）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。戦略ロジック（ファクター計算・シグナル生成）と発注実行、監視・アラート、リスク管理を組み合わせ、開発用（development）、ペーパートレード（paper_trading）、本番（live）を切り替えて運用できる設計になっています。

設計上の方針の一部：
- 本番／ペーパートレードの DB 分離（ペーパートレード時は別の SQLite を使用）
- 監視・Kill Switch による安全停止
- DuckDB を用いた分析（prices_daily / raw_financials など）
- OpenAI を使ったニュースセンチメント評価・レジーム判定（フォールバック・リトライ実装あり）
- .env ベースの設定管理（対話ウィザードと検証 CLI を提供）

---

## 機能一覧

- Execution
  - ExecutionEngine（発注エンジン）および BrokerClientFactory（実口座・モック切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler（発注・再整合・リスク統制）
  - ペーパートレード専用 DB（data/paper_trading.db がデフォルト）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度を監視
  - TradeMonitor: 滞留注文（stale orders）・約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の更新とリスクログ
  - MonitoringEngine: 各 Monitor を束ねてポーリング、AlertManager 経由で通知
  - KillSwitch: data/kill.flag による ExecutionEngine 強制停止機構
  - 監視ログ永続化（SQLite、monitoring_db）

- Portfolio / Position Sizing
  - 候補選定（スコア降順）
  - 等重み・スコア重み算出
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 各種株数計算（risk_based / equal / score ベース）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定を行う

- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env および config/*.yaml の起動前確認 CLI
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定レポートを生成

---

## セットアップ

前提
- Python 3.9+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証のため）
- OS 権限：プロセス優先度変更や CPU affinity の一部は権限が必要な場合があります。

インストール（例）
1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存をインストール（例: setup.py / pyproject に依存関係があればそちらを利用）
   - 例: pip install -e .  または pip install duckdb psutil openai PyYAML

環境変数 / .env
- 対話式ウィザードで .env を作成:
  - python -m kabusys.config_setup
- .env はプロジェクトルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須環境変数（少なくとも設定しておくべき）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- 主要な環境変数（デフォルトは括弧内）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - LOG_LEVEL: INFO（デフォルト）
  - KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

データディレクトリ
- デフォルトで使用する DB 等は data/ 配下に置かれます。必要に応じてディレクトリを作成してください（スクリプトが自動生成する箇所もあります）。

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も FAIL にする: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - デフォルト（KABUSYS_ENV に応じて動作）
    - python -m kabusys.run_execution
  - ペーパートレード起動例：
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。
  - 実行時の注意：
    - プロセス優先度を "high" に設定（必要に応じて変更）。
    - 起動前に data/kill.flag が立っているとエンジンは起動しません。
    - エンジンは実行中にデータベースへダッシュボード等を書き込みます。PID ファイル（data/execution.pid）も管理されます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒
  - 監視は Settings.sqlite_path（監視 DB）を使用してログを保管します（Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様）。
  - 停止フラグ: data/stop_requested.flag を作成するとループは検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH  または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key が None の場合 OPENAI_API_KEY を参照
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - 両モジュールは API の失敗に対してフォールバック（スコア=0 など）します。OpenAI API キーを環境変数にセットしておく必要があります。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - config.py               — Settings クラス（.env / 環境変数読み込み、設定プロパティ）
  - config_setup.py         — .env 対話ウィザード（対話式設定）
  - validate_config.py      — 設定検証 CLI（.env と config/*.yaml のチェック）

  - ai/
    - news_nlp.py           — ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
    - regime_detector.py    — MA200 + マクロニュースで市場レジーム判定

  - monitoring/
    - monitoring_db.py      — SQLite による監視ログ永続化（テーブル作成・MonitoringDB API）
    - system_monitor.py     — CPU/メモリ/ディスク/データ鮮度 / プロセス生存チェック
    - trade_monitor.py      — 滞留注文・約定異常検出
    - risk_monitor.py       — ドローダウン・ポジション数監視、dashboard 更新
    - monitoring_engine.py  — 各 Monitor を束ねる
    - kill_switch.py        — data/kill.flag を書き込むロジック（ExecutionEngine 停止）
    - alert_manager.py      — （通知送信ラッパー。実装に応じて LINE 等に通知）

  - portfolio/
    - portfolio_builder.py  — 候補選定、等重み/スコア重み
    - position_sizing.py    — 株数計算、上限・aggregate cap、単元丸め
    - risk_adjustment.py    — セクターキャップ、レジーム乗数

  - research/
    - factor_research.py    — momentum / volatility / value 計算（DuckDB）
    - feature_exploration.py— 将来リターン・IC・統計サマリ

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

  - execution/              — 発注関連（OrderManager, OrderRepository, EngineConfig, ExecutionEngine, BrokerClientFactory 等。実運用ロジック）
    - (order_manager.py, order_repository.py, execution_engine.py, broker_factory.py, ...)

（上記は主要モジュールの一覧です。実際のファイルや追加モジュールはリポジトリ内を参照してください。）

---

## DB スキーマ（監視用：monitoring_db の概要）

init_monitoring_db() により作成される主なテーブル（冪等で作成）：
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 固定, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

マイグレーションとして latency_ms（trade_logs）と peak_value（dashboard）列が必要時に追加されます。

---

## Kill Switch / 停止フラグ

- Kill Switch はリスク条件（ドローダウンやポジション上限）に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- run_execution / run_monitoring は data/stop_requested.flag を検知して自プロセスを終了する挙動を持ちます。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0（クリアしない）を推奨します。

---

## 注意点・運用メモ

- OpenAI を利用する機能は OPENAI_API_KEY を必要とし、API レート制限・ネットワーク障害に対するリトライやフォールバックが組み込まれていますが、API キー管理・コストに注意してください。
- 本番運用（KABUSYS_ENV=live）では LINE 通知や kill flag の設定を十分に確認してください（validate_config に live 向けガードあり）。
- ペーパートレード（paper_trading）は本番 DB と分離されます。ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH を使用します。
- process_priority / cpu_affinity の一部操作はプラットフォーム依存かつ権限を要します。必要に応じて調整してください。

---

この README はコードベース（主要モジュール）から要点を抽出してまとめています。詳細な API や内部ロジック（関数引数／戻り値・例外挙動）は各モジュールの docstring を参照してください。必要であれば各モジュール別の詳しいドキュメント（使い方、ユースケース、例）を追記できます。