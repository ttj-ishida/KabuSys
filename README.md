# KabuSys

KabuSys は日本株の自動売買システム向けライブラリ／実行基盤です。  
戦略・ポートフォリオ構築、注文発行・リスク管理、監視・アラート、AI を使ったニュース解析などの機能を持ち、ローカル開発 / ペーパートレード / 本番（live）の実行モードをサポートします。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）の独立実行
  - run_execution.py：注文発行・リスク管理・注文調整を行う実行エンジン起動スクリプト
  - run_monitoring.py：SystemMonitor をポーリングして監視ログを記録する起動スクリプト
- Paper Trading（ペーパートレード）モード
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し本番 DB と分離（デフォルト: data/paper_trading.db）
  - ペーパートレード用検証レポート生成スクリプト（tools/paper_verification_report.py）
- 監視機能
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセスチェック
  - TradeMonitor: 滞留注文／約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、kill flag 発動
  - MonitoringDB: SQLite に監視ログ・トレードログ・リスクログを永続化
  - KillSwitch: data/kill.flag により ExecutionEngine を安全停止
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重、セクター上限、レジーム乗数、ポジションサイズ算出（lot 単位丸め）
- リサーチ / ファクター
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携
  - ニュース NLP（news_nlp）で銘柄別センチメントを算出し ai_scores に保存
  - 市場レジーム判定（regime_detector）で ma200 とマクロニュースを合成
  - API 呼び出しは堅牢化（リトライ、バリデーション等）
- 開発支援ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前チェック（必須環境変数・config/*.yaml・パス等）
  - 自動 .env 読み込み（プロジェクトルートの .env/.env.local。ただし無効化可能）

---

## セットアップ手順

1. リポジトリをチェックアウト／コピーして作業ディレクトリへ移動

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 以下は最低限必要となるパッケージの例（requirements.txt がある場合はそちらを使用）
     - duckdb
     - psutil
     - openai
     - PyYAML (validate_config の YAML 検証で使用)
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（.env は Git にコミットしないこと）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトの DB／フラグファイル等は `data/` 配下を使用します。プロジェクト実行時に自動作成されることもありますが、必要に応じて作成してください。

注意: 環境変数の自動読み込みはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 主要な環境変数（抜粋）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行モード
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
    - paper_trading: MockBroker を使用し、発注はペーパートレード DB に記録

- データベース / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill flag（デフォルト: data/kill.flag）

- ペーパートレード設定
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- ロギング / その他
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1/0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（実行例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV により Broker クライアントが切り替わる（paper_trading では MockBroker）
    - 停止は data/stop_requested.flag ファイル（または Kill Switch）により行える
    - 実行中は PID を data/execution.pid に書き込む

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（秒）
  - 監視は常に本番の sqlite_path を使ってログを記録（環境に依らず）

- ペーパー検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- kill flag / 停止
  - KillSwitch は data/kill.flag を書き込む仕組みです。ExecutionEngine はこのファイルを検知すると安全停止します。
  - run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）／kill.flag の存在をチェックしています。

---

## ディレクトリ構成（主要ファイル）

ここでは `src/kabusys` 配下の主要モジュールを抜粋して示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動読み込み / Settings クラス
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 起動前の設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングスクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — ペーパートレード検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP（OpenAI 連携）
      - regime_detector.py     — 市場レジーム判定（OpenAI 連携）
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py      — システム・データ鮮度監視
      - trade_monitor.py       — 注文滞留・約定異常監視
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 書込ユーティリティ
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - alert_manager.py       — （アラート送信用の抽象層 / 実装は未表示）
    - execution/                — Execution 関連（OrderManager, Engine, BrokerFactory 等）
      - ... (実行ロジック関連)
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 株数決定・スケール調整・単元丸め
      - risk_adjustment.py     — セクター上限・レジーム乗数
    - research/
      - __init__.py
      - factor_research.py     — Momentum, Volatility, Value 計算
      - feature_exploration.py — 将来リターン・IC・統計サマリ
    - utils/
      - __init__.py
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

（実際のファイル一覧はリポジトリを参照してください）

---

## 注意事項 / トラブルシューティング

- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- OpenAI API キーが未設定だと news_nlp / regime_detector の機能は動作しません。これらの機能は失敗時にフェイルセーフ（0.0 等）で継続する設計ですが、API を使う場合は OPENAI_API_KEY を設定してください。
- run_monitoring は Monitoring 用 SQLite（Settings.sqlite_path）に常に接続します。テスト時に本番 DB を誤って操作しないよう注意してください。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して DB を分離します。
- プロセス優先度設定（psutil による nice / Windows priority）は OS の権限に依存します。権限不足で警告が出ることがありますが、致命的ではありません。
- PID ファイル（data/execution.pid）が不正な内容だった場合、SystemMonitor が削除してアラートを出します（stale PID 検出）。
- Docker などで実行する場合はファイルベースのフラグ（data/kill.flag, data/stop_requested.flag）やパスのマウントに注意してください。

---

## 参考コマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- ペーパー検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README はコードベースの主要機能と運用手順を簡潔にまとめたものです。詳細な設計仕様や API 利用方法（kabuステーション / J-Quants / OpenAI の各種仕様）は別途ドキュメント（Design / API README 等）を参照してください。