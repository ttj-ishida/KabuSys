# KabuSys

日本株自動売買システムのコアコンポーネント（ライブラリ + 起動スクリプト群）

このリポジトリは注文実行エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、Paper Trading用検証ツール、AIを用いたニュースセンチメント評価などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要な以下の機能群を持つモジュール化されたシステムです。

- 実際の発注またはペーパートレードを行う ExecutionEngine
- システム稼働状況・注文状況・リスクを監視する Monitoring
- ポートフォリオ構築（候補選定・配分・ポジションサイズ計算・セクター制限など）
- DuckDB を用いたファクター計算・リサーチ（モメンタム、バリュー、ボラティリティ等）
- OpenAI（LLM）を使ったニュースの NLP スコアリングと市場レジーム判定
- Paper Trading 検証レポート生成ツール
- 環境設定ウィザード / 設定検証 CLI

設計方針の一部:
- 本番 DB（monitoring.db）とペーパートレード DB（paper_trading.db）は分離
- ルックアヘッドバイアス回避（日付参照は引数ベース）
- フェイルセーフ（AI呼び出し失敗時はフォールバック動作）
- テストしやすい純粋関数 / 明確な永続化層分離

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / paper_trading 切替（環境変数 KABUSYS_ENV）
  - BrokerClientFactory 経由でブローカー操作（paper_trading は Mock）
  - RiskManager, OrderManager, Reconciler を組み合わせた ExecutionEngine 起動
  - 停止フラグ（data/stop_requested.flag）と PID ファイル管理

- 監視（run_monitoring.py, monitoring モジュール）
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、Executionプロセスの監視
  - TradeMonitor: 注文滞留・約定異常等の検出（trade_logs参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: リスクトリガー時に data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各 Monitor のポーリング統合（MONITOR_POLL_INTERVAL による間隔調整）

- ポートフォリオ（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等分・スコア加重重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）

- リサーチ（kabusys.research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算 / IC 計算 / 統計サマリ（calc_forward_returns, calc_ic, factor_summary 等）
  - DuckDB 接続を受け取り SQL + Python で高速処理

- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を用いた JSON 出力ベースの評価、リトライ・バリデーション実装

- ツール
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 必須要件（推奨）

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（Python 標準ライブラリで扱える）
- ネットワークアクセス（kabu API / OpenAI を使用する場合）

※ 実行環境に応じて追加の依存がある可能性があります。適宜 requirements.txt を作成して pip でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env をプロジェクトルートに作成
     - 主要な環境変数:
       - JQUANTS_REFRESH_TOKEN (必須)
       - KABU_API_PASSWORD (必須)
       - KABUSYS_ENV (development | paper_trading | live)
       - OPENAI_API_KEY（AI 機能を使う場合）
       - DUCKDB_PATH（例: data/kabusys.duckdb）
       - SQLITE_PATH（例: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
       - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START 等
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにするには --strict を付ける

---

## 使い方（起動・操作）

- ExecutionEngine（注文実行）起動
  - python -m kabusys.run_execution
  - 動作モードは環境変数 KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を利用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番ブローカーを使って実際に発注
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中は data/execution.pid に PID を書き込みます

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に Settings.sqlite_path（本番 monitoring DB）を使用
  - 停止: data/stop_requested.flag を作成するとループが終了

- 停止 / Kill Switch
  - KillSwitch はリスク条件（ドローダウン等）に達した場合 data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）で管理
  - ExecutionEngine は起動時または実行中に kill.flag を検出して停止します
  - kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）がありますが本番では注意が必要です

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

---

## 主要 CLI の一覧

- python -m kabusys.config_setup
  - .env の対話式生成・更新ウィザード

- python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml の整合性チェック

- python -m kabusys.run_execution
  - ExecutionEngine の起動スクリプト

- python -m kabusys.run_monitoring
  - SystemMonitor ポーリングループ起動スクリプト
  - 環境変数: MONITOR_POLL_INTERVAL（秒）

- python -m kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート出力

---

## ライブラリ API（簡易）

これらは内部モジュールとして外部スクリプトやテストから利用できます。

- ポートフォリオ
  - from kabusys.portfolio import (
      select_candidates,
      calc_equal_weights,
      calc_score_weights,
      calc_position_sizes,
      apply_sector_cap,
      calc_regime_multiplier,
    )

- リサーチ
  - from kabusys.research import (
      calc_momentum,
      calc_volatility,
      calc_value,
      zscore_normalize,
      calc_forward_returns,
      calc_ic,
      factor_summary,
      rank,
    )

- AI（ニュース）
  - from kabusys.ai import score_news
    - score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str]) -> int

- Monitoring DB 永続化クラス
  - kabusys.monitoring.monitoring_db.MonitoringDB
    - log_system_status / log_trade_event / upsert_position / log_risk_event / upsert_dashboard / get_dashboard

---

## 主要環境変数（要点）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR: ログ設定
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: pid / kill flag のパスを上書き可能

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                     — 環境変数読み込み・Settings定義（自動 .env ロード）
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py            — システム・データ鮮度監視
  - trade_monitor.py             — 注文ログ監視（ファイルにないが監視系の一部）
  - risk_monitor.py              — ドローダウン / ポジション数監視
  - kill_switch.py               — kill.flag 書込みロジック
  - monitoring_engine.py         — 各 Monitor を束ねる実行ループ
  - alert_manager.py             — アラート送信（LINE など、実装は含まれる想定）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py             — 統一的なロギング設定
  - process_priority.py          — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

プロジェクトルート:
- .env (ユーザー作成)
- config/ (各種 YAML 設定ファイルのテンプレート)
- data/ (デフォルトの DB / flag / pid / stop ファイルが置かれる場所)
- logs/ (ログ出力)

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）のときは KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアされると Kill Switch が無効化される恐れがあります。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI API を使用する機能は API 利用料が発生します。キー管理・レート制限に注意してください。
- Monitoring は監視用 DB（monitoring.db）へ常に書き込みます。paper_trading は発注 DB を分離しますが、監視 DB は同じファイルを使う設計になっています（run_monitoring は settings.sqlite_path を常に使用）。
- process priority / CPU affinity の設定はプラットフォーム依存で失敗する場合があります（権限不足等）。その場合は警告ログを出してスキップします。

---

README は以上です。運用や拡張のためのドキュメント（アーキテクチャ図、DB スキーマ詳細、Strategy/Portfolio 設計ドキュメント等）は別途用意することを推奨します。必要があれば各モジュールや CLI の使い方をより詳細にまとめます。