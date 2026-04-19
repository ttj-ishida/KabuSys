# KabuSys — 日本株自動売買システム

簡易 README（日本語）

このリポジトリは日本株向けの自動売買・リサーチ・監視ユーティリティ群をまとめたライブラリ/サービス群です。実行エンジン、監視モジュール、ポートフォリオ構築、ファクター計算、AIベースのニュース解析などを含みます。

※ 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

- 目的: 日本株の自動売買を支援するための実行エンジン、監視・リスク管理、研究（ファクター計算）および AI によるニュースセンチメント評価のためのモジュール群を提供します。
- 実行モード:
  - development: ローカル開発・テスト（発注なし）
  - paper_trading: ペーパートレード（発注はモック、専用 DB に記録）
  - live: 本番（実際に発注）
- 設計方針:
  - DuckDB を分析用 DB として使用
  - SQLite を監視・トレードログ用に使用
  - OpenAI（gpt-4o-mini 等）をニュースセンチメントやレジーム判定に利用可能
  - .env により環境変数で設定を管理（interactive ウィザードあり）

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使い DB を分離。
- 監視プロセス
  - run_monitoring.py: SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL で間隔変更可。
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期実行・アラート発行・Kill Switch 評価を行う。
- 監視 DB 層
  - monitoring_db.py: SQLite に対するテーブル作成・読み書きユーティリティ（system_status, trade_logs, positions, risk_logs, dashboard等）。
- リスク監視
  - risk_monitor.py: ドローダウン・ポジション上限の監視とダッシュボード更新、リスクログ出力。
  - kill_switch.py: 条件を満たしたら data/kill.flag を書き込み ExecutionEngine に停止命令を出す。
- ポートフォリオ構築
  - portfolio/ : 候補選定、重み計算、セクターキャップ、レジーム乗数、ポジションサイズ計算（lot 単位の丸め・aggregate cap 等）。
- リサーチ
  - research/ : ファクター（Momentum/Value/Volatility 等）・将来リターン計算・IC（Information Coefficient）や統計サマリ機能。
- AI モジュール
  - ai/news_nlp.py: raw_news から銘柄ごとのニュースを集約し OpenAI でセンチメント（ai_scores）を作成して書き込む。
  - ai/regime_detector.py: ETF（1321）MA とマクロニュースを組み合わせて市場レジーム判定を行い market_regime に書き込み。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定（stdout + 日次ローテートファイル）。
  - utils/process_priority.py: プロセス優先度や CPU affinity の設定（Windows/Linux の差分吸収）。
- CLI ヘルパー
  - config_setup.py: .env を対話式で作成・更新するウィザード。
  - validate_config.py: 環境変数・config/*.yaml の事前検証ツール（--strict オプションあり）。
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成するスクリプト。

---

## 前提 / 必要環境

- Python 3.9+（ソース内で型注釈等を利用）
- 推奨パッケージ（機能に応じて必要）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- その他: ネットワーク接続（OpenAI / ブローカ API）や SQLite/DuckDB ファイル書き込み権限

インストール例（仮）:
- 仮想環境作成後:
  - pip install duckdb psutil openai pyyaml

（実際の requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリを取得して作業ディレクトリをプロジェクトルートにする。
2. Python 仮想環境を作成・有効化。
3. 依存パッケージをインストール（上記参照）。
4. .env の作成（推奨）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、必要な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定します。
5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict
6. データディレクトリ等の確認:
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/
7. （paper_trading を使う場合）KABUSYS_ENV を `paper_trading` に設定すると Execution はモックブローカーを使用し data/paper_trading.db に記録され、本番 DB と分離されます。

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（分析用）
  - SQLITE_PATH: data/monitoring.db（監視ログ）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（run_monitoring 用、デフォルト 60）
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定挙動）

---

## 使い方（主なスクリプト/コマンド）

- .env 作成（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時に process priority を "high" に設定します（utils/process_priority）。
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path に接続します。
    - 実行中に data/stop_requested.flag を作成すると安全に停止できます。
    - 実行中は pid ファイル（data/execution.pid）を生成します。

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（デフォルト: 60）。
    - 監視プロセスは本番 sqlite_path を環境に関係なく使用します（監視ログ共通）。
    - data/stop_requested.flag が存在するとループを終了します。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼び出す）
  - ニューススコア付け:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

- ログ:
  - ログは stdout に出力され、かつ logs/<app_name>.log に日次ローテートで保存されます（utils/logging_setup.setup_logging）。

---

## 停止・Kill Switch について

- Kill Switch:
  - kabusys.monitoring.kill_switch がリスク条件を評価して必要なら data/kill.flag を出力します。
  - ExecutionEngine 起動時に Settings.kill_flag_clear_on_start を 1 にしていると起動時に自動クリアします（本番では推奨しません）。
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は検知して安全に停止します。
  - 実行プロセスは該当フラグを監視するループ設計です。

---

## ディレクトリ構成（主要ファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（自動 .env ロード・Settings クラス）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）処理
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・読み書き（system_status 等）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - trade_monitor.py       — （存在ファイルに基づくトレード監視ロジック）
    - monitoring_engine.py   — 監視エンジン（まとめ）
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （アラート送信の抽象化）
  - execution/               — ExecutionEngine, OrderManager, BrokerFactory 等（起動ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要モジュールの抜粋です。実際のファイルを参照してください）

---

## 開発・デバッグのヒント

- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を検出して .env/.env.local を自動読み込みします。テスト時に自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング:
  - setup_logging(app_name="execution") のようにアプリ名を指定すると logs/<app_name>.log に出力されます。
- テスト時の API 呼び出し差し替え:
  - news_nlp._call_openai_api / regime_detector._call_openai_api 等の内部呼び出しはユニットテストで patch 可能です。
- DuckDB / SQLite スキーマ:
  - monitoring_db.init_monitoring_db は冪等にテーブル・インデックス作成を行います。既存 DB のマイグレーション（カラム追加）も一部実装されています。

---

## よくある操作例

- .env を作成して設定検証まで行う一連の流れ:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config --strict

- 監視をローカルで 30 秒間隔にして起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート（2026-04-01 〜 2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / 注意事項

- この README はソースコード内のドキュメントや docstring に基づいて作成されています。
- .env（機密情報）は決してバージョン管理に含めないでください（config_setup でも明記）。
- 本番運用時は KABUSYS_ENV=live にし、Kill Switch・LINE 通知等の設定を十分に確認してください。
- OpenAI / ブローカ API の利用は追加コストとリスクがあります。APIキーは安全に管理してください。

---

必要であれば、各モジュール（ExecutionEngine、OrderManager、TradeMonitor など）の API 使用例・設計ドキュメント（フロー図・シーケンス）や、より詳細なデプロイ手順（systemd / supervisor / Docker / コンテナ化）を追記できます。どの箇所を詳細化したいか教えてください。