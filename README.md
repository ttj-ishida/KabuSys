# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリ。  
この README はコードベースの使い方、設定方法、主要機能・ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリは実運用・発注を行うコードを含みます。`KABUSYS_ENV=live` の設定時は特に注意して取り扱ってください。

---

## 概要

KabuSys は次のような機能を持つモジュール群で構成された自動売買・研究プラットフォームです。

- 監視（Monitoring）: システム状態、発注ログ、リスク監視、Kill Switch
- 実行（Execution）: 発注エンジン、ブローカー抽象化、リスク管理
- ポートフォリオ構築: 候補選択、ウェイト計算、ポジションサイズ算出、セクター制限
- 研究（Research）: ファクター計算、特徴量探索、IC 計算
- AI 支援: ニュース NLP による銘柄センチメント、レジーム判定
- ツール: Paper Trading の検証レポート生成など
- 設定ユーティリティ: .env ウィザード、設定検証 CLI

設計方針の例:
- DuckDB / SQLite を利用したローカル DB 中心の処理
- LLM（OpenAI）呼び出しは API キーで制御し、失敗耐性やリトライを実装
- 多くの処理は外部副作用を避ける純粋関数で実装（研究・ポートフォリオ計算等）

---

## 主な機能一覧

- SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存を監視しログ保存
- TradeMonitor / MonitoringDB: 発注イベントやポジション、リスクログを永続化
- RiskMonitor / KillSwitch: ドローダウン・ポジション過多などを検出し Kill Switch を発動
- ExecutionEngine: ブローカークライアントに依存した注文作成・管理（paper_trading モードあり）
- Portfolio module: 候補抽出、等分配・スコア加重、リスクベースのポジション決定、セクター制限
- Research module: momentum/value/volatility ファクター計算、将来リターン・IC 計算
- AI module: ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- CLI ツール:
  - python -m kabusys.config_setup : .env 対話式ウィザード
  - python -m kabusys.validate_config : 環境・設定検証（--strict あり）
  - python -m kabusys.tools.paper_verification_report : Paper Trading の検証レポート

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の `X | Y` 構文を使用）
- pip が利用可能

1. リポジトリをチェックアウト / クローンします。

2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストールします（必要に応じてインストールしてください）。
   代表的な依存:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証の YAML パース用。なくても動作はしますが警告が出ます）
   例:
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は `pip install -r requirements.txt` を実行してください。）

4. .env の初期作成:
   - python -m kabusys.config_setup
   このウィザードは対話式で .env を生成します。生成された .env は絶対に Git にコミットしないでください。

   自動読み込みを無効化する場合:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証を実行:
   - python -m kabusys.validate_config
   - 本番運用前は --strict を付けて警告も FAIL として扱う: python -m kabusys.validate_config --strict

6. DB・ログ用ディレクトリの確認:
   - デフォルトの DB / ファイルパスは .env の値または以下のデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
   - 必要に応じてディレクトリを作成してください（実行スクリプトは自動作成する場合があります）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

詳細は `kabusys.config.Settings` クラスを参照してください。

---

## 使い方（実行例）

- 監視ループを起動（SystemMonitor を定期ポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジンを起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、データは data/paper_trading.db に保存されます

- .env の対話式作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告もエラー扱い）: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

- AI モジュール（コードから呼ぶ）:
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

注意点:
- ExecutionEngine 側は data/kill.flag（Settings.kill_flag_path）を監視し、KillSwitch により停止します。KillSwitch は RiskMonitor 等の条件で作成されます。
- stop フラグ（run_monitoring / run_execution 共通）: data/stop_requested.flag を作成すると外部監視プロセスによりループが終了します。

---

## ログ

- ロギングは共通のユーティリティ `kabusys.utils.logging_setup.setup_logging` を通じて設定されます。
- デフォルト出力: stdout（コンソール）および日次ローテートファイル（logs/<app_name>.log）。
- ログディレクトリは環境変数 LOG_DIR またはデフォルト `logs/`。

---

## ディレクトリ構成

主要ファイル / モジュールの概要:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ（schema 初期化・CRUD）
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — Kill Switch 制御（kill.flag 書込）
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - (その他: trade_monitor, alert_manager など)
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig など）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・スコアソート
    - position_sizing.py     — 発注株数計算・スケールダウン・単元丸め
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — ETF MA + マクロセンチメントでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパー検証レポート生成
  - data/                    — デフォルトで使う DB / pid / flag ファイル等（実行時に作成）
  - logs/                    — ログ出力先（デフォルト）

（上記は主なファイルを抜粋。コードベース内にさらに細分化されたモジュール群があります。）

---

## 開発上の注意事項 / 動作上の留意点

- KABUSYS_ENV が `live` の場合は本番扱いになります。LINE 通知設定や Kill Switch の扱い等、慎重に確認してください。
- AI モジュール（OpenAI）を利用する際は API キーの漏洩に注意してください。トークンは .env に保存する場合でも慎重に管理してください。
- DuckDB / SQLite への書き込みは複数プロセスでの競合に注意が必要です（設計上は役割ごとに DB を分ける想定）。
- 監視・実行スクリプトは stop フラグ（data/stop_requested.flag）・kill.flag（Settings.kill_flag_path）で制御されます。運用手順を整備してください。
- config_setup で生成された .env はデフォルトで OS 環境より下位になります（自動ロード時の優先順位に注意）。

---

## よく使うコマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視ループ起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## 貢献 / 拡張

- 新しいブローカーを追加する場合は `kabusys.execution.broker_factory` と BrokerClient の実装を追加してください。
- 研究用モジュールは DuckDB 接続を受け取る純粋関数として設計されています。データ追加やパイプライン拡張を行う際は影響範囲を確認してください。
- テスト追加・CI を導入する場合は、.env の自動読み込み機構（KABUSYS_DISABLE_AUTO_ENV_LOAD）を利用してテスト環境を分離してください。

---

README に記載のない詳細や運用手順が必要であれば、対象のモジュール名を指定して質問してください。README の改善案（追加したい項目）も歓迎します。