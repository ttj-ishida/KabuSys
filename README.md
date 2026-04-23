# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（モジュール群）。  
このリポジトリは発注実行エンジン、監視、ポートフォリオ構築、ファクター計算、AI を使ったニュースセンチメント評価などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な設計方針は以下のとおりです。

- 実行（ExecutionEngine）と監視（Monitoring）を明確に分離
- Paper Trading（ペーパートレード）向けに実本番 DB と分離された挙動をサポート
- DuckDB を用いた時系列・財務データ解析（研究用途）
- OpenAI を使ったニュース NLP（センチメント評価）・レジーム判定（オプション）
- ローカル .env ワークフローを前提とした設定管理、対話ウィザード、検証 CLI

---

## 機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV による paper_trading モードのサポート（MockBroker 使用）
  - paper_trading 時は専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離
  - PID ファイル管理 / 停止フラグ検知（data/stop_requested.flag）

- Monitoring 起動スクリプト（run_monitoring.py）
  - System / Trade / Risk の定期チェックを行うポーリングループ
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化（init_monitoring_db）

- 設定管理
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前チェック・検証 CLI（kabusys.validate_config）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分 / スコア配分、セクター上限適用、レジーム乗数、ポジションサイズ計算

- 研究（kabusys.research）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計

- AI（kabusys.ai）
  - ニュースから銘柄ごとのセンチメントスコアを生成（news_nlp.score_news）
  - ETFベースの MA200 とマクロニュースを用いた市場レジーム判定（regime_detector.score_regime）

- ユーティリティ
  - ロギングセットアップ（logs/ 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（PEP604 の | 型注釈などを使用）
- Git リポジトリルートをプロジェクトルートとして扱う（.env 自動ロードに使用）

1. リポジトリを取得
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な必須パッケージ（手動インストール例）:
     - pip install duckdb psutil openai
   - 任意（YAML 検証や分析で必要）:
     - pip install PyYAML

4. 環境変数の設定
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または手動でルートに `.env` を作成。必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 機能利用時）
   - 起動時に .env が自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリの作成（必要に応じて）
   - data/ （SQLite / PID / フラグ等）
   - logs/ （ログ出力）

---

## 使い方

基本的なコマンド例を示します。いずれもプロジェクトルートから実行してください。

- .env 作成（対話ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/stop_requested.flag の存在で停止処理をトリガー

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は監視用 SQLite（Settings.sqlite_path、デフォルト data/monitoring.db）へログを保存
  - 監視プロセスは常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH を使って既定 DB を上書き可

- AI 機能（ニューススコア / レジーム判定）
  - これらは関数として提供され、DuckDB 接続と API キーを渡して使用します。
  - 例（簡易）:
    - Python REPL で:
      - from datetime import date
      - import duckdb
      - conn = duckdb.connect("data/kabusys.duckdb")
      - from kabusys.ai.news_nlp import score_news
      - score_news(conn, date(2026,4,1), api_key="sk-...")

  - 注意: OpenAI API キーは env または引数で指定してください。ネットワークエラー時にリトライロジックあり。

- ロギング
  - setup_logging が各起動スクリプトで呼ばれます。デフォルトログディレクトリは `logs/`、日次ローテートで 30 日保持。

- 停止 / Kill Switch
  - KillSwitch モジュールは監視結果により data/kill.flag を書き込み、ExecutionEngine の異常停止等をトリガーします。
  - 実際の起動・停止フローは stop フラグ（data/stop_requested.flag）や kill.flag を利用しています。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリア（本番では 0 を推奨）。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY — AI 機能利用時に必要
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

例 (.env の抜粋)
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成

以下は主要なファイル／ディレクトリと簡単な説明です（src/kabusys をルートとした構成）。

- src/
  - kabusys/
    - __init__.py
    - config.py
      - .env 自動ロード、Settings クラス
    - config_setup.py
      - 対話式 .env ウィザード
    - validate_config.py
      - 起動前チェック CLI
    - run_execution.py
      - ExecutionEngine 起動スクリプト
    - run_monitoring.py
      - Monitoring ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py
      - __init__.py
    - ai/
      - news_nlp.py
        - ニュース記事を OpenAI で評価して ai_scores に書き込み
      - regime_detector.py
        - ETF MA200 とマクロニュースでレジーム判定、market_regime へ書込
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照: trade_monitor を含む想定)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (アラート管理、実装を想定)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/ (エンジン関連モジュール群、OrderManager 等)
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - data/（実データ・DB ファイルは .gitignore 推奨）
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
    - logs/
      - execution.log, monitoring.log ... (日次ローテート)

注: 上記はソース内にあるファイルを元にした代表的構成です。実際のリポジトリでは多少の差分がある可能性があります。

---

## 開発者向けメモ（要点）

- Settings クラスは runtime に環境変数を参照します。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと自動 .env ロードを無効化できます。
- Monitoring の DB 初期化は init_monitoring_db() にて冪等的に行われます（マイグレーションも一部実装済み）。
- run_execution は paper_trading の場合、MockBrokerClient を使いデータを分離します。Production（live）の場合は実ブローカーを使用する想定。
- AI モジュールは OpenAI API への依存があるため、キー管理・コスト管理に注意してください。API エラー時は基本的にフェイルセーフ（スコア 0 やスキップ）で続行する実装です。
- ログはルートロガーに統一的に設定されます。logs/ ディレクトリが作れない環境ではコンソール出力のみになります。

---

もし README に追加したい具体的なコマンド例、CI 設定、Docker イメージ化、または個別モジュール（ExecutionEngine の起動フローや OrderRepository の利用方法など）について詳細が必要であれば教えてください。必要に応じて Usage 例や API スニペットを追加します。