# KabuSys

日本株向け自動売買システムの軽量フレームワーク（パーツ群）。  
このリポジトリはシグナル生成・ポートフォリオ構築・発注実行・監視・リサーチ・AI 補助などの機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような機能を備えた自動売買システムの基盤ライブラリです:

- シグナル → ポートフォリオ構築 → 発注の Execution Engine（本番 / ペーパー切替）
- 実行状況・システム状態を記録する監視コンポーネントと Kill Switch
- DuckDB を使ったリサーチ／ファクター計算モジュール
- OpenAI を使ったニュースセンチメント（AI モジュール）
- 設定ウィザード・設定検証用の CLI ツール
- Paper Trading の検証レポート生成ツール
- 汎用ユーティリティ（ログ設定・プロセス優先度設定 等）

設計方針として、外部 API（発注APIなど）への直接依存を分離し、テスト容易性・フェイルセーフを重視しています。

---

## 主な特徴 (機能一覧)

- Execution
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - Broker クライアントの抽象化（実ブローカ or Mock）
  - RiskManager、OrderManager、Reconciler を備えた実行フロー
- Monitoring
  - SystemMonitor: CPU・メモリ・ディスク・プロセス・データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留やドローダウン監視
  - KillSwitch: 条件により停止フラグを書き込み Execution を停止
  - MonitoringEngine: 複数モニタのポーリングとアラート連携
  - SQLite ベースの monitoring DB（初期化・マイグレーション対応）
- Portfolio
  - 候補選定 / 等配分・スコア配分 / ポジションサイズ計算
  - セクターキャップ・レジーム乗数適用
- Research
  - DuckDB を使ったファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI
  - ニュースを OpenAI（gpt-4o-mini）でスコアリング（ai_scores テーブルへ格納）
  - マクロニュース + ETF MA200 による市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バリデーション・フェイルセーフ実装
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ログ設定（ログローテート含む）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提 / 必要環境

- Python 3.9+
- 推奨パッケージ（主な依存）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - pyyaml（config 検証で YAML の検証をする場合）
- SQLite（標準で組み込み済み）
- ネットワークアクセス（kabuステーション API / OpenAI を使う場合）

（requirements.txt は本リポジトリに含まれていないため、必要なパッケージを個別にインストールしてください）

例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

---

## 環境変数 / 主要設定

自動的にプロジェクトルートの `.env` / `.env.local` が読み込まれます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（デフォルト値や意味）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意、アラート送信)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- LOG_DIR (デフォルト: logs/)
- KILL_FLAG_CLEAR_ON_START (0/1) — Execution 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔を秒で上書き可能)

注意:
- `.env` は機密情報を含むため絶対に Git 等にコミットしないでください。
- 本番（KABUSYS_ENV=live）では各種設定（LINE など）を十分に確認してください。

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. 環境変数を用意
   - 対話式で .env を作る（推奨）
     - python -m kabusys.config_setup
   - 手動で `.env` を作る場合は `.env.example` を参考に必要キーを設定

4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

5. DB 初期化は各起動スクリプトで必要に応じて行われます（monitoring / execution の起動時に SQLite / DuckDB を接続して初期化されます）。

---

## 起動・使い方

基本的に以下のモジュールをエントリポイントとして起動します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ（SystemMonitor 単体起動）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト: 60）
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  動作概要:
  - SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）へ接続して SystemMonitor を初期化
  - data/stop_requested.flag が作成されるとループを終了

- Execution Engine（発注エンジン）
  - KABUSYS_ENV により本番 / ペーパーを切り替え
    - paper_trading: MockBrokerClient を使用し paper DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 実ブローカークライアントを使用
  - python -m kabusys.run_execution
  - 例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  動作概要:
  - 設定・DB 接続後、Broker の生成、OrderManager / RiskManager / Engine を組み立て、別スレッドで engine.run_session を実行
  - data/stop_requested.flag を検知すると engine.stop() を呼び停止

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必須（OPENAI_API_KEY）
  - 関数はプログラムからインポートして使用:
    - from kabusys.ai import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続と target_date を受け取り、DB に書き込む

停止シグナル:
- run_monitoring / run_execution はプロジェクトルート配下の data/stop_requested.flag を参照し、存在すると起動中ループを終えてシャットダウンします。
- KillSwitch は data/kill.flag を書き込み Execution の停止を誘導します（設定により起動時に自動クリア可能）。

ログ:
- デフォルトで logs/<app_name>.log に日次ローテーションで出力（ログディレクトリは LOG_DIR で上書き可）。
- コンソール出力は stdout に出力されます。

---

## ディレクトリ構成（代表）

（src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — （データアクセス関連モジュールは別ディレクトリにある想定）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

その他トップレベル（プロジェクトルート）:
- .env, .env.local       — 環境変数ファイル（機密情報のためコミット禁止）
- data/                  — SQLite / PID / flag 等のデータファイル置き場
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                  — ログ出力（デフォルト）

---

## 実運用上の注意点

- .env に API キーやパスワードを保存する場合はアクセス制御・バックアップ等を注意してください。
- 本番で KABUSYS_ENV=live を設定する前に必ず validate_config を実行して設定を確認してください。
- Kill Switch（kill.flag）の自動クリア設定は本番では無効（0）にすることを推奨します。
- OpenAI 利用に伴うコストとレート制限に注意してください。ニュース NLP ではバッチ化・リトライ・スコア検証を実装していますが、運用時はモニタリングを行ってください。
- DuckDB / SQLite のファイルは定期的にバックアップすることを推奨します。

---

## 開発・テストのヒント

- モジュールを単体でテスト可能なように設計されています（DB 接続や OpenAI クライアントは引数で渡す）。
- ai.news_nlp の OpenAI 呼び出し関数はテストで差し替え可能（unit test で patch する設計）。
- monitoring_db.init_monitoring_db は冪等で実行でき、既存 DB へマイグレーション（カラム追加）を行います。

---

必要であれば、README にサンプル .env のテンプレート、より詳しい起動手順（systemd / supervisor 用のサービスユニット例）や、各モジュールの API 仕様（関数シグネチャ）などを追加できます。どの情報を優先して展開しますか？