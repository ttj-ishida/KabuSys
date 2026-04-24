# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

本リポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリと起動スクリプトを含みます。Trading 実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、および AI を使ったニュース評価などの機能群がモジュール化されています。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています：

- 日次・リアルタイムのシグナルに基づく注文発行（ExecutionEngine）
- システム状態／注文状態／リスクを監視し、Kill Switch（停止フラグ）で発注エンジンを安全に停止
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）
- OpenAI（gpt-4o-mini 等）を使ったニュースのセンチメント評価（AI モジュール）
- ペーパートレードと本番環境の分離（Paper Trading 用 DB）

設計方針の一部：
- DB は DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- 環境変数 / .env による設定管理（config.py）
- 起動スクリプトはプロセス優先度やログ設定を統一的に行う
- フェイルセーフ（API 失敗時のバックオフやフォールバック）を重視

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文発行（本番 / ペーパートレードを切り替え可能）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - リスクマネージャ（ポジション上限、利用率、ドローダウンなど）
  - OrderRepository / OrderManager / Reconciler

- Monitoring
  - SystemMonitor: CPU／メモリ／ディスク／プロセス生存／データ鮮度の監視
  - TradeMonitor: 注文滞留や約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限などの監視
  - MonitoringEngine: 監視コンポーネントの統合ポーリング
  - KillSwitch: 条件により ExecutionEngine を停止するフラグ書き込み
  - 永続層: monitoring_db.py（SQLite スキーマと読み書きユーティリティ）

- Portfolio / Position sizing
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（単元丸め、aggregate cap 調整）

- Research
  - factor_research: momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ

- AI（OpenAI）
  - news_nlp: ニュースを LLM でスコア化し ai_scores に永続化
  - regime_detector: ETF (1321) の MA とマクロセンチメントを合成して市場レジーム判定

- ツール / スクリプト
  - 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式に生成）
  - 設定検証: python -m kabusys.validate_config（--strict 指定可）
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

- ログ設定 / ユーティリティ
  - 統一的ロギングセットアップ（ログの stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. レポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 主要依存例（環境によって必要）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証の YAML パースに必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env を作成する
   - 対話式ウィザード推奨:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定
   - デフォルトのパス:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - data/ と logs/ は自動作成されますが、権限等で失敗することがあるため手動で作成する場合:
     - mkdir -p data logs

---

## 主な環境変数（よく使うもの）

- KABUSYS_ENV: 実行環境（development, paper_trading, live）※ default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: duckdb ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 環境時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（default: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（1 で有効。production では 0 推奨）

補足:
- run_monitoring は Monitoring 用の SQLite（settings.sqlite_path）を常に使用します（環境に依らず本番 DB を参照する設計上の仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作中に停止指示を出すには（外部から）data/stop_requested.flag を作成する、もしくは監視の KillSwitch が data/kill.flag を作成します。
  - run_execution は起動時に process priority を "high" に設定します（可能な環境のみ）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Python API の呼び出し例（スクリプトから AI スコアを生成）
  - from openai import OpenAI
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")

---

## 停止 / Kill / フラグの扱い

- run_monitoring と run_execution はプロジェクトルートの data/stop_requested.flag ファイルの存在を監視し、存在時にループを停止します（外部から安全に停止させる目的）。
- KillSwitch は条件（ドローダウン超過やポジション上限超過）を満たしたときに data/kill.flag を書き、ExecutionEngine 側で検出して停止できます。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると 起動時に kill.flag を自動クリアします（本番では危険なためデフォルト 0 推奨）。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照される)
    - kill_switch.py
    - alert_manager.py (参照される)
  - execution/
    - execution_engine.py (参照される)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    — （実行環境で作成されることが多い）
  - logs/                    — ログファイル出力先（デフォルト）

プロジェクトルートには config/*.yaml（テンプレート）、.env.example などが置かれる想定です。

---

## トラブルシューティング / 注意点

- Python パッケージ
  - duckdb / psutil / openai / pyyaml などが必要です。環境に応じてインストールしてください。
  - PyYAML がない場合、validate_config の YAML 検証はスキップされ警告が出ます。

- ログディレクトリ作成失敗
  - 権限などで logs/ の作成が失敗するとファイル出力は無効化され、コンソール出力のみになります（warning が表示されます）。

- DB パスの親ディレクトリが存在しない場合
  - validate_config は親ディレクトリの存在を警告しますが、起動時に自動作成される場合があります。確実に動作させるには事前に data/ ディレクトリを作成してください。

- Paper Trading と本番データは分離されています
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。誤って本番 DB を上書きしないよう注意してください。

- OpenAI 利用
  - OpenAI API はコスト・レイテンシに注意。API エラー時は内部でリトライやフォールバック（macro_sentiment=0 など）を行う設計ですが、本番投入前に十分な検証を行ってください。

---

必要に応じて README を補足（インストール要件の固定化、CI やテスト手順、デプロイ手順、設定例の追加など）します。追加で載せたい内容があれば教えてください。