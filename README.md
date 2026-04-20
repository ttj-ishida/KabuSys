# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコードベースです。  
この README はコード内にあるモジュールや起動スクリプトを基に、導入・運用に必要な情報を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件
- セットアップ手順
- 環境変数と .env（推奨）
- 起動 / 使い方（主要スクリプト）
- 停止・Kill スイッチについて
- 開発者向けノート
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買フレームワークです。  
主要な機能はシグナル生成・ポートフォリオ構築・発注管理・実行エンジン・監視（Monitoring）・ペーパートレード検証・AI（ニュース NLP）による補助情報などを含みます。  
設計上、本番環境（live）とペーパートレード環境（paper_trading）を明確に分離し、安全性と検証性を重視しています。

---

## 主な機能一覧

- Execution Engine（発注エンジン）
  - ブローカークライアント抽象化（本番/モック切替）
  - OrderManager / RiskManager / Reconciler を組み合わせた発注ワークフロー
- Monitoring（監視）
  - SystemMonitor（プロセス状態・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（注文滞留・約定異常 等）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件を満たすと停止フラグを書き込み、Execution を停止）
  - Monitoring DB（SQLite）へのログ永続化
- Portfolio Construction
  - 候補選定、等重/スコア重みの計算、ポジションサイズ決定、セクター上限など
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計要約
- AI 支援
  - ニュース記事の LLM によるセンチメントスコア（OpenAI）集約
  - 市場レジーム判定（ma200 + マクロセンチメント）
- ツール
  - 設定ウィザード（.env 作成）: config_setup.py
  - 設定検証 CLI: validate_config.py
  - Paper Trading 検証レポート生成: tools/paper_verification_report.py
- ロギングとプロセス優先度ユーティリティ
  - 統一的なログ設定（console + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）

---

## 動作要件（推奨）

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証を行う場合に推奨）
- SQLite（標準ライブラリで利用）
- Unix/Windows の両対応を意識した実装あり（psutil を使用）

※ 実際の requirements.txt はこの README に含まれていません。導入時はローカルで使用している環境に合わせて依存をインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（クイックスタート）

1. リポジトリをチェックアウト
   - git clone ... && cd <repo>

2. 仮想環境作成（任意推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がない場合は手動で主要パッケージをインストール）

4. 環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（下を参照）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化・データ準備
   - DuckDB / SQLite のパスは .env の DUCKDB_PATH / SQLITE_PATH 等で指定
   - monitoring DB は起動スクリプトが必要に応じて自動でテーブル作成します

---

## 環境変数（主なもの）

このプロジェクトは .env ファイルを利用して環境変数を管理します（.env/.env.local 自動ロード）。重要なキー:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API パスワード

運用・DB 関連
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
  - paper_trading: 発注はモック、専用 paper_trading DB を使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant, partial, never, reject）

ロギング・制御
- LOG_LEVEL — DEBUG/INFO/...
- LOG_DIR — ログの保存先（デフォルト: logs/）
- PID_FILE_PATH — Execution 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill スイッチのフラグパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に Kill フラグを自動クリアするか（0/1）

AI（任意）
- OPENAI_API_KEY — OpenAI API キー（ai 機能を使う場合）

その他
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）

.env の例（テンプレート）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

注意: .env は機密情報を含むためリポジトリにコミットしないでください。

---

## 使い方（主要スクリプト）

各スクリプトはモジュールとして実行できます（パッケージルートから）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Execution Engine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して paper_trading.db に記録（本番 DB と分離）
    - PID ファイルを data/execution.pid に書く（設定可能）
    - data/stop_requested.flag の検出で Engine に停止命令を出す

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト: 60 秒）
    - settings.sqlite_path（本番の monitoring.db）へログを残す（監視は環境にかかわらず本番 sqlite_path を使用）
    - data/stop_requested.flag の検出で監視ループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ機能
  - ai.score_news 等はライブラリ API として利用（プログラム内部から呼ぶ）
  - OpenAI の利用には OPENAI_API_KEY を設定

ローグ出力:
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテート）に出力されます。

---

## 停止・Kill スイッチ

運用中に安全に実行を停止するための仕組みが複数あります。

- 停止フラグ（run_* スクリプト共通）
  - data/stop_requested.flag が存在すると run_* のループは終了します（管理用）。
- Kill Switch（監視側が判定して書き込む）
  - data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを与える仕組み
  - KillSwitch はドローダウンやポジション上限超過等で発動するよう設計
- PID ファイル
  - Execution 用 PID を data/execution.pid に保存し、外部運用ツールからプロセス管理可能

注意: KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（起動時に自動クリアされます）。

---

## 開発者向けノート

- 設定の自動ロード
  - .env と .env.local はプロジェクトルート（.git または pyproject.toml を基準）から自動ロードされます。テスト時に自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。
- ロギング
  - setup_logging(app_name=...) を全スクリプトの起動直後に呼び出して統一的にログを処理しています。
- プロセス優先度
  - set_process_priority("high") を起動直後に呼び出して、監視/エンジンプロセスの優先度を上げる設計です（psutil を使用）。
- Paper trading 分離
  - paper_trading 環境では発注ロジックはモックに切り替わり、paper_trading 用の SQLite に記録されます。本番 DB と完全に分離されます。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"

  - run_monitoring.py     — Monitoring ポーリングループ起動スクリプト
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - config.py             — 環境変数 / 設定管理
  - config_setup.py       — .env 対話式ウィザード
  - validate_config.py    — 設定検証 CLI

  - utils/
    - logging_setup.py    — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

  - monitoring/
    - monitoring_db.py    — SQLite による監視ログ永続化
    - system_monitor.py   — システム状態・データ鮮度監視
    - trade_monitor.py    — 注文関連監視（存在）
    - risk_monitor.py     — ドローダウン / ポジション上限監視
    - kill_switch.py      — Kill スイッチ処理
    - monitoring_engine.py — 監視モジュール束ね（ポーリング）処理
    - alert_manager.py    — アラート送信管理（存在）

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py         — ニュース NLP（OpenAI）
    - regime_detector.py  — 市場レジーム判定

  - tools/
    - paper_verification_report.py

- data/                  — データファイル（logs/ や DB ファイルのデフォルト位置）
  - monitoring.db (default)
  - paper_trading.db (paper_trading 用)
  - execution.pid
  - kill.flag / stop_requested.flag

- logs/                  — ログ出力ディレクトリ（デフォルト）

---

## よくある運用手順（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. monitoring をデーモンで起動（python -m kabusys.run_monitoring）
4. execution を起動（python -m kabusys.run_execution）
5. 運用中は logs/ を監視し、必要に応じて data/kill.flag を作成（手動または監視が自動で作成）
6. ペーパートレード結果の検証（python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11）

---

何か README の追記や、各モジュールの詳細なドキュメント（API リファレンス、設定例、運用手順）を追加したい場合は、対象範囲を指定していただければ詳細なドキュメントを作成します。