# KabuSys

日本株向け自動売買システムの軽量ライブラリ／ランタイム群（プロジェクト断片）。
本 README はリポジトリ内の主要エントリポイント・ユーティリティの使い方と構成をまとめたものです。

> 注意: この README はソースコードを基に手動作成しています。実運用前に `python -m kabusys.validate_config` で設定を検証してください。

---

## 概要

KabuSys は次のような機能を提供するモジュール群を含みます。

- 実行エンジン（ExecutionEngine）と監視ループ（Monitoring）
- 発注／注文管理、リスク管理、リコンシリエーション
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ファクター計算・研究ユーティリティ（DuckDB を使った分析）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 監視ログ永続化（SQLite）および監視周りのユーティリティ
- ユーティリティ群（ログ設定、プロセス優先度設定、設定ウィザード・検証）

設計方針の一部:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による）
- DuckDB を分析用に利用
- OpenAI など外部 API 呼び出しは明示的にキーを渡す／環境変数を利用

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動（KABUSYS_ENV による本番／ペーパー切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- monitoring: システム・注文・リスク監視、kill switch、アラート発行
- portfolio: 候補選定、重み付け、ポジションサイジング、セクター制限、レジーム乗数
- research: DuckDB を使ったファクター計算、将来リターン、IC 計算など
- ai: news_nlp（ニュースセンチメント→ai_scores 書込み）、regime_detector（市場レジーム判定）
- tools: paper_verification_report（ペーパートレード検証レポート生成）
- utils: logging_setup, process_priority など共通ユーティリティ
- 設定関連: .env 作成ウィザード（config_setup.py）と起動前検証 CLI（validate_config.py）

---

## 要件（目安）

- Python 3.10+
- 必要な Python パッケージ（プロジェクトの requirements.txt を参照）
  - duckdb
  - psutil
  - openai（ai 機能を使う場合）
  - PyYAML（config/*.yaml の厳密検証を行う場合にオプション）
- SQLite（組み込み）
- 実運用では適切な権限でプロセス優先度変更やログディレクトリの作成が行えること

---

## セットアップ手順

1. リポジトリを clone して作業ディレクトリに移動

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上述の主要パッケージを個別にインストール）

4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に `.env` を作成してプロジェクトルートに置く
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （実運用時は OPENAI_API_KEY、LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID なども設定）
   - KABUSYS_ENV の値:
     - development / paper_trading / live
     - paper_trading: MockBroker を使い `data/paper_trading.db` を使用
     - live: 本番（実発注）

5. 設定検証（起動前）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトのパスは `data/`、`logs/`。起動時に自動作成されますが事前に権限確認推奨。

---

## 使い方（実行例）

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV による挙動）
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 例（本番）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 備考:
    - paper_trading の場合は `PAPER_TRADING_SQLITE_PATH` を指定して専用 DB に記録
    - 実行中にファイル `data/stop_requested.flag` を作成すると起動中のループが検出して終了します

- Monitoring を起動（60 秒間隔がデフォルト）
  - MONITOR_POLL_INTERVAL で秒数を指定可能（1 以上）。不正値はデフォルトにフォールバック。
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 備考:
    - 監視は常に本番の sqlite_path を使用（環境によらず monitoring DB は共通。本番 DB の path は Settings/sqlite_path で制御）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で SQLite ファイルパスを指定（環境変数 PAPER_TRADING_SQLITE_PATH も使用可能）

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前）
  - python -m kabusys.validate_config [--strict]

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（news_nlp/regime_detector を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での Kill Flag 自動クリアを制御、0/1）

---

## 停止・Kill スイッチの仕組み

- run_monitoring.py と run_execution.py はプロジェクト内の `data/stop_requested.flag` を監視しており、存在すると安全にループ／エンジンを終了します。
- kill_switch モジュールは監視結果（ドローダウンやポジション上限など）に応じて `data/kill.flag` を書き込み、ExecutionEngine 側で検知して停止する仕組みです。
- ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると kill.flag を自動クリアします（本番では 0 推奨）。

---

## ログ

- ログ出力は共通のユーティリティ `kabusys.utils.logging_setup.setup_logging` を利用します。
- デフォルト: logs/<app_name>.log に日次ローテーション（30 日保持）
- コンソール出力は stdout を使用

---

## データベース初期化

- 監視用 SQLite のスキーマ作成やマイグレーションは `kabusys.monitoring.monitoring_db.init_monitoring_db` が担います。起動スクリプトは自動的にこれを呼びますが、手動で保証したい場合はスクリプト内から接続して呼び出してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリは次の通りです（src/kabusys 以下）:

- __init__.py
- config.py — 環境変数 / 設定読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + ETF MA でレジーム判定
- monitoring/
  - monitoring_db.py — SQLite 操作用（テーブル作成・読み書き）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
  - monitoring_engine.py — 全体のオーケストレータ
  - kill_switch.py, alert_manager.py（アラート処理）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py, process_priority.py

（上記は主なファイルのみ抜粋。実際のツリーを確認してください）

---

## 注意事項 / 運用メモ

- デフォルト設定では monitoring が本番用 sqlite_path を参照します。監視ログを別にしたい場合は SQLITE_PATH を調整してください。
- process priority の設定はプラットフォーム依存（psutil を利用）。権限不足で設定に失敗する場合は警告が出ますが続行します。
- OpenAI を使用する機能（ニュース NLP, regime 判定）は API キーが必須です。API 失敗時は安全側のフォールバック（※実装による）を行いますが、運用方針を確認してください。
- 本リポジトリの .env は絶対に Git にコミットしないでください（config_setup でも警告あり）。
- DuckDB・SQLite ファイルはデフォルトで data/ 配下に作られます。バックアップや権限管理に注意してください。

---

## 開発・テスト

- ライブラリ関数群（portfolio、research、ai の一部など）は外部依存を持たない純関数設計になっています。ユニットテストが書きやすい設計です。
- 外部 API 呼び出しを含む箇所はテストでモック可能（ソース内に patch 想定の箇所あり）。

---

必要であれば、この README をベースに:
- requirements.txt の推奨一覧作成
- systemd/サービスユニットのサンプル
- docker-compose 構成例
を追加で作成します。どれを優先しますか？