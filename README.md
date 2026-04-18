# KabuSys

日本株自動売買システムのライブラリ兼起動スクリプト群。  
このリポジトリは以下を含みます：データ処理、リサーチ（ファクター計算）、ポートフォリオ構築、発注実行、監視、AI を使ったニュース解析など。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システム向けに設計されたコンポーネント群です。  
主な機能は以下のとおりです：

- データ処理（DuckDB を利用した時系列データアクセス）
- ファクター計算・特徴量生成（momentum, volatility, value など）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- 発注・ExecutionEngine（本番 / ペーパートレード対応、ブローカーファクトリ）
- 監視（System / Trade / Risk の定期チェック、kill flag）
- AI モジュール（OpenAI を使ったニュースセンチメント、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計のポイント:
- 環境変数ベースの設定（.env）を想定
- Paper Trading と Live を DB・動作で分離
- DuckDB はリサーチ用、SQLite は監視/トレードログ用
- OpenAI 呼び出しはフェイルセーフに配慮（リトライ・フォールバック）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定管理
  - config_setup.py: 対話式で .env を生成・更新
  - validate_config.py: .env と config/*.yaml の事前検証（--strict オプションあり）
- 監視
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch 等
  - 監視データ永続化用 SQLite（monitoring_db.py）
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment（等金額／スコア重み／リスクベース）
- リサーチ
  - factor_research（momentum / volatility / value）
  - feature_exploration（forward returns / IC / summary）
- AI
  - news_nlp: ニュース記事を LLM でスコアリング（OpenAI）
  - regime_detector: マクロ + ETF MA200 で市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## システム要件（推奨）

- Python 3.9+
- 必要パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- （任意）ログ出力先ディレクトリ作成権限

インストールはプロジェクトに合わせて requirements.txt を作成し pip で行ってください。最低限は次を入れてください:

pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをチェックアウト／配置する。

2. Python 仮想環境を用意して依存関係をインストール。

3. .env の作成（対話式ウィザード推奨）
   - 対話式ウィザードを実行すると .env を生成できます:
     python -m kabusys.config_setup
   - 生成後、設定が正しいか検証:
     python -m kabusys.validate_config
     （--strict を付けると警告も失敗扱いになります）

4. 必須環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合に必須）
   - その他（LOG_LEVEL, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH など。config_setup で補助されます）

サンプル .env（config_setup が生成する形式の抜粋）:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

注意: .env はセキュアな情報を含むため絶対にリポジトリにコミットしないでください。

---

## 起動・使い方

基本的にはモジュールをモード指定で起動します。プロジェクトルートで実行してください。

- ExecutionEngine を起動
  - 目的: 発注処理を行うエンジンを起動します。
  - コマンド:
    python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - PID ファイル: data/execution.pid（既定。Settings.pid_file_path で変更可能）
    - 停止: kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を監視しているため、監視コンポーネントなどで書き込むことで停止指示できます。

- Monitoring を起動
  - 目的: System/Trade/Risk の定期チェック（監視ログの記録・Kill Switch 評価・アラート通知など）。
  - コマンド:
    python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60
  - 挙動:
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず Settings.sqlite_path）。
    - data/stop_requested.flag を検知するとループを抜けて終了します。

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を指定すると警告も失敗扱い（exit 1）

- .env 設定ウィザード
  - python -m kabusys.config_setup

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト local）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## ログ・永続化

- ログ
  - デフォルトは logs/ ディレクトリにアプリ名ごとの日次ローテーションログを出力（例: logs/execution.log, logs/monitoring.log）。logs ディレクトリは自動作成を試みます（権限がない場合はコンソール出力のみ）。

- DB
  - DuckDB（分析用）: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLite（監視・注文ログ）: SQLITE_PATH（デフォルト data/monitoring.db）
  - Paper trading 用 SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - init_monitoring_db は冪等的にテーブル・インデックス作成および簡単なマイグレーションを実行します。

- フラグ / PID ファイル
  - stop_requested.flag: run_monitoring / run_execution の停止検知用ファイル（data/stop_requested.flag）
  - kill.flag: ExecutionEngine に停止指示を送る KillSwitch 用（Settings.kill_flag_path、デフォルト data/kill.flag）
  - execution.pid: ExecutionEngine の PID ファイル（data/execution.pid）

---

## 開発者向けメモ（コンポーネント概要）

- kabusys.config: 環境変数/ .env 管理。自動ロード機能あり（.env / .env.local）。
- kabusys.utils.logging_setup: ルートロガーの共通設定（Stream + TimedRotatingFileHandler）。
- kabusys.utils.process_priority: psutil を使ってプロセス優先度や CPU affinity を設定。
- kabusys.monitoring: 監視関連（monitoring_db, system_monitor, risk_monitor, monitoring_engine, kill_switch, alert_manager 等）。
- kabusys.execution: 発注エンジン・OrderManager・Reconciler・RiskManager（コードベースに含まれるが詳細は該当ファイルを参照）。
- kabusys.portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数。
- kabusys.research: ファクター計算（momentum/volatility/value）、forward returns、IC、統計サマリー。
- kabusys.ai: news_nlp（OpenAI を使った銘柄毎ニューススコアリング）、regime_detector（マクロ + ETF 指標でレジーム判定）。

---

## ツール（例）

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）など。PASS/FAIL 判定あり。

---

## ディレクトリ構成

プロジェクト内の主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - /* その他監視関連モジュール */
  - execution/
    - /* ExecutionEngine, OrderManager, BrokerFactory 等（詳細は該当ファイル） */
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

（プロジェクトルート）
- data/              # デフォルト DB / PID / flag を配置する想定
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/              # ログファイル（自動作成）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（自動クリアは危険）。
- OpenAI を利用する機能は API キー必須。API 呼び出しはレート制限やサーバエラーを想定した実装（リトライ・フォールバック）になっていますが、コストと失敗時の挙動を事前に理解してください。
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。検証・実験は必ずペーパートレード環境で行ってから本番に移行してください。
- ログや DB のバックアップ、権限設定、ディスク使用量監視などは別途運用フローに組み込んでください。

---

## 参考コマンドまとめ

- .env を作る（対話式）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はここまでです。プロジェクトの追加ファイル（requirements.txt、デプロイ手順、運用 runbook、CI 設定など）は別途用意することを推奨します。必要なら起動フロー図やユースケース別手順（開発 / ステージング / 本番）も作成できます。どの情報を優先して追記しますか？